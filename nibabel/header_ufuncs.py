'''  Ufunc-like functions operating on Analyze headers '''
import numpy as np

from volumeutils import array_from_file, array_to_file, \
    HeaderDataError, HeaderTypeError, \
    calculate_scale, can_cast


def read_unscaled_data(hdr, fileobj):
    ''' Read raw (unscaled) data from ``fileobj``

    Parameters
    ----------
    hdr : header
       analyze-like header implementing ``get_data_dtype``,
       ``get_data_shape`` and ``get_data_offset``.
    fileobj : file-like
       Must be open, and implement ``read`` and ``seek`` methods

    Returns
    -------
    arr : array-like
       an array like object (that might be an ndarray),
       implementing at least slicing.
    '''
    dtype = hdr.get_data_dtype()
    shape = hdr.get_data_shape()
    offset = hdr.get_data_offset()
    return array_from_file(shape, dtype, fileobj, offset)


def read_data(hdr, fileobj):
    ''' Read data from ``fileobj`` given ``hdr``

    Parameters
    ----------
    hdr : header
       analyze-like header implementing ``get_slope_inter`` and
       requirements for ``read_unscaled_data``
    fileobj : file-like
       Must be open, and implement ``read`` and ``seek`` methods

    Returns
    -------
    arr : array-like
       an array like object (that might be an ndarray),
       implementing at least slicing.

    '''
    slope, inter = hdr.get_slope_inter()
    data = read_unscaled_data(hdr, fileobj)
    if slope is None:
        return data
    # The data may be from a memmap, and not writeable
    if slope:
        if slope !=1.0:
            try:
                data *= slope
            except ValueError:
                data = data * slope
        if inter:
            try:
                data += inter
            except ValueError:
                data = data + inter
    return data


def write_data(hdr, data, fileobj,
               intercept=0.0,
               divslope=1.0,
               mn=None,
               mx=None):
    ''' Write ``data`` to ``fileobj`` coercing to header dtype

    Parameters
    ----------
    hdr : header
       header object implementing ``get_data_dtype``, ``get_data_shape``
       and ``get_data_offset``.
    data : array-like
       data to write; should match header defined shape.  Data is
       coerced to dtype matching header by simple ``astype``.
    fileobj : file-like object
       Object with file interface, implementing ``write`` and ``seek``
    intercept : scalar, optional
       scalar to subtract from data, before dividing by ``divslope``.
       Default is 0.0
    divslope : None or scalar, optional
       scalefactor to *divide* data by before writing.  Default
       is 1.0.  If None, image has no valid data, zeros are written
    mn : scalar, optional
       minimum threshold in (unscaled) data, such that all data below
       this value are set to this value. Default is None (no threshold)
    mx : scalar, optional
       maximum threshold in (unscaled) data, such that all data above
       this value are set to this value. Default is None (no threshold)

    Examples
    --------
    >>> from nibabel.analyze import AnalyzeHeader
    >>> hdr = AnalyzeHeader()
    >>> hdr.set_data_shape((1, 2, 3))
    >>> hdr.set_data_dtype(np.float64)
    >>> from StringIO import StringIO
    >>> str_io = StringIO()
    >>> data = np.arange(6).reshape(1,2,3)
    >>> write_data(hdr, data, str_io)
    >>> data.astype(np.float64).tostring('F') == str_io.getvalue()
    True

    We check the data shape

    >>> write_data(hdr, data.reshape(3,2,1), str_io)
    Traceback (most recent call last):
       ...
    HeaderDataError: Data should be shape (1, 2, 3)
    '''
    data = np.asarray(data)
    shape = hdr.get_data_shape()
    if data.shape != shape:
        raise HeaderDataError('Data should be shape (%s)' %
                              ', '.join(str(s) for s in shape))
    out_dtype = hdr.get_data_dtype()
    offset = hdr.get_data_offset()
    try:
        fileobj.seek(offset)
    except IOError, msg:
        if fileobj.tell() != offset:
            raise IOError(msg)
    if divslope is None: # No valid data
        fileobj.write('\x00' * (data.size*out_dtype.itemsize))
        return
    array_to_file(data, out_dtype, fileobj, intercept, divslope,
                  mn, mx)


def write_scaled_data(hdr, data, fileobj):
    ''' Write data to ``fileobj`` with best data match to ``hdr`` dtype

    This is a convenience function that modifies the header as well as
    writing the data to file.  Because it modifies the header, it is not
    very useful for general image writing, where you often need to first
    write the header, then the image.

    Parameters
    ----------
    data : array-like
       data to write; should match header defined shape
    fileobj : file-like object
       Object with file interface, implementing ``write`` and ``seek``

    Returns
    -------
    None

    Examples
    --------
    >>> from nibabel.analyze import AnalyzeHeader
    >>> hdr = AnalyzeHeader()
    >>> hdr.set_data_shape((1, 2, 3))
    >>> hdr.set_data_dtype(np.float64)
    >>> from StringIO import StringIO
    >>> str_io = StringIO()
    >>> data = np.arange(6).reshape(1,2,3)
    >>> write_scaled_data(hdr, data, str_io)
    >>> data.astype(np.float64).tostring('F') == str_io.getvalue()
    True
    '''
    slope, inter, mn, mx = hdr.scaling_from_data(data)
    write_data(hdr, data, fileobj, inter, slope, mn, mx)
