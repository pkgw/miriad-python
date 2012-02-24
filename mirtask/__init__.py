'''mirtask - basic classes for implementing MIRIAD tasks in Python'''

# Copyright 2009-2012 Peter Williams
#
# This file is part of miriad-python.
#
# Miriad-python is free software: you can redistribute it and/or
# modify it under the terms of the GNU General Public License as
# published by the Free Software Foundation, either version 3 of the
# License, or (at your option) any later version.
#
# Miriad-python is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.

import numpy as N
from mirtask import _miriad_c, _miriad_f, util
from mirtask._miriad_c import MiriadError

__all__ = 'util MiriadError'.split ()


class DataSet (object):
    """:synopsis: an opened MIRIAD dataset

:arg str path: the path of the dataset on disk
:arg str mode: the mode on which to open the dataset;
  one of "rw", "c", or "a"

Instances of this class allow lowlevel manipulation of MIRIAD
datasets. More specific subclasses, such as :class:`UVDataSet`
or :class:`XYDataSet`, allow more structured access to the
data contained in the dataset.
"""

    tno = None
    _path = None

    def __init__ (self, path, mode):
        if mode == 'rw':
            modestr = 'old'
        elif mode == 'c':
            modestr = 'new'
        else:
            raise ValueError ('unknown mode string "%s"', mode)

        self._path = path
        self.tno = _miriad_c.hopen (path, modestr)


    def _close (self):
        _miriad_c.hclose (self.tno)


    def __del__ (self):
        # tno can be None if we got an exception inside hopen,
        # or if we are deleteAll'ed

        if _miriad_c is None or self.tno is None:
            return

        self._close ()


    def __repr__ (self):
        return 'DataSet (%r)' % (self._path, )


    def __str__ (self):
        if self.tno is not None:
            hstr = 'handle %d' % self.tno
        else:
            hstr = 'not currently open'

        return '<DataSet "%s" %s>' % (self._path, hstr)


    def path (self, *args):
        from os.path import join
        return join (self._path, *args)


    def isOpen (self):
        return self.tno is not None

    def _checkOpen (self):
        if self.tno is not None:
            return
        raise RuntimeError ('Illegal operation on a closed dataset')

    def close (self):
        """Close the dataset."""

        self._checkOpen ()

        if self._histOpen: self.closeHistory ()

        self._close ()
        self.tno = None

    def flush (self):
        """Write any changed items in the data set out to disk."""

        self._checkOpen ()
        _miriad_c.hflush (self.tno)

    def deleteAll (self):
        """Completely delete this data set. After calling this function,
        this object cannot be used."""

        self._checkOpen ()
        _miriad_c.hrm (self.tno)
        self.tno = None

    def deleteItem (self, name):
        """Delete an item from this data-set."""

        self._checkOpen ()
        _miriad_c.hdelete (self.tno, name)

    MODE_UNKNOWN, MODE_RD, MODE_RDWR = range (0, 3)

    def getMode (self):
        """Return the access mode of this data-set: readonly or
        read-write. See the MODE_X fields of this class for possible
        return values."""

        self._checkOpen ()
        mode = _miriad_c.hmode (self.tno)

        if mode == '': return self.MODE_UNKNOWN
        elif mode == 'r': return self.MODE_RD
        elif mode == 'rw': return self.MODE_RDWR

        raise MiriadError ('Unknown hio mode type: ' + mode)

    # Data items

    def hasItem (self, name):
        """Return whether this data-set contains an item with the given name."""

        self._checkOpen ()
        return _miriad_c.hexists (self.tno, name)

    def getItem (self, itemname, mode):
        """Return a DataItem object representing the desired item
        within this dataset. See the documentation of the DataItem
        constructor for the meaning of the 'itemname' and 'mode'
        parameters.
        """

        if itemname == '.': raise ValueError ("Use itemNames() instead.")

        return DataItem (self, itemname, mode)

    def itemNames (self):
        """Generate a list of the names of the data items contained in
        this data set."""

        ilist = DataItem (self, '.', 'r')
        s = ilist.getSize ()
        text = ilist.read (0, str, s)
        ilist.close ()
        return text.splitlines ()

    # History

    _histOpen = False

    def openHistory (self, mode='a'):
        """Open the history item of this data set. 'mode' may be
        'r' if the history is being read, 'w' for truncation and writing,
        and 'a' for appending. The default is 'a'.
        """

        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self._checkOpen ()
        _miriad_c.hisopen (self.tno, modestr)
        self._histOpen = True

    def writeHistory (self, text):
        """Write text into this data set's history file."""

        self._checkOpen ()
        _miriad_c.hiswrite (self.tno, text)


    def logInvocation (self, ident, args=None):
        """Log a the date, a task name, and an argument list to this dataset's history.

:arg string ident: an identifier that will prefix the history entries
:arg args: a list of arguments, or :const:`None` (the default); if the latter,
  ``sys.argv[1:]`` is used.
:type args: string iterable or :const:`None`
:returns: *self*

This function emulates the MIRIAD library function HISINPUT. It logs
the date, some arguments, and an identifier to the dataset's history file,
with the identifier traditionally being the name of a MIRIAD task. This
implementation attempts to mimic the behavior of HISINPUT as closely as
possible -- except for its truncation of very long arguments.

Note that *args* should not start with an ``argv[0]`` entry.
"""

        self._checkOpen ()

        if args is None:
            import sys
            args = sys.argv[1:]

        prefix = ident + ': '
        date = util.jdToFull (_miriad_f.todayjul (), 'T')
        _miriad_c.hiswrite (self.tno, prefix + 'Executed on: ' + date)
        _miriad_c.hiswrite (self.tno, prefix + 'Command line inputs follow:')

        prefix += '  '
        dofile = False

        for arg in args:
            if dofile:
                f = open (arg, 'r')
                for line in f:
                    _miriad_c.hiswrite (self.tno, prefix + line)
                f.close ()
                dofile = False
            else:
                if arg == '-f':
                    dofile = True
                else:
                    _miriad_c.hiswrite (self.tno, prefix + arg)

        return self


    def closeHistory (self):
        """Close this data set's history item."""

        self._checkOpen ()
        _miriad_c.hisclose (self.tno)
        self._histOpen = False


    # Dataset items

    def getScalarItem (self, itemname, default=None, missingok=True):
        """Get the value of a scalar dataset item

:arg str itemname: the name of the item to fetch
:arg any default: the value to return if the item is not
  present in this dataset; defaults to :const:`None`.
:arg bool missingok: if *default* should be returned if the
  variable is not defined in this dataset; defaults to :const:`True`.
  If :const:`False` and the variable is not defined, raises
  :exc:`ValueError`.
:returns: the value
:rtype: numpy scalar type

This gets the value of a scalar dataset item, possibly returning a
default value if the variable is not found. The return value is a
numpy scalar type appropriate for the item, or a string for textual
items. Note that these types propagate, so there is a danger of
overflow or underflow if you do some kinds of math with the return
value. Furthermore, if you provide *default*, it will usually be one
of the builting Python numeric types, not a NumPy type, so if code
depends on the type of the return value, there may be variations in
behavior depending on whether the variable was found or not.
"""
        self._checkOpen ()
        res = _miriad_c.rdhd_generic (self.tno, itemname)
        if res is None:
            if not missingok:
                raise ValueError ('no such dataset item "%s"' % itemname)
            return default
        return res

    def setScalarItem (self, itemname, itemtype, value):
        """Set the value of a scalar dataset item.

:arg str itemname: the name of the item to set
:arg type itemtype: the type of the item value
:arg any value: the item value
:returns: *self*

Sets the value of a scalar dataset item. Because many aspects
of MIRIAD rely on the particular storage types of dataset
items, the type must be specified explicitly. The value will
be cast to the specified type before writing if it is not
already an instance of it.

Acceptable types are :class:`str`, :class:`numpy.int32`,
:class:`numpy.int64`, :class:`numpy.float32`, :class:`numpy.float64`,
and :class:`numpy.complex64`. Due to limitations in the
MIRIAD I/O routines, :class:`numpy.int8` and :class:`numpy.int16`,
which are acceptable in other contexts, are not allowed here.
"""
        self._checkOpen ()
        if not isinstance (value, itemtype):
            value = itemtype (value)
        _miriad_c.wrhd_generic (self.tno, itemname, value)
        return self


    def copyItem (self, dest, itemname):
        """Copy an item from this dataset to another.

:arg dest: the opened destination dataset
:type dest: :class:`DataSet` or subclass
:arg str itemname: the name of the item
:returns: *self*
"""

        self._checkOpen ()
        dest._checkOpen ()
        _miriad_c.hdcopy (self.tno, dest.tno, itemname)
        return self


    def getItemInfo (self, itemname):
        """Return the characteristics of the item. Returns:
        (desc, type, n), where 'desc' describes the item or gives its value
        if it can be expressed compactly; 'type' is one of 'nonexistant',
        'integer*2', 'integer*8', 'integer', 'real', 'double', 'complex',
        'character', 'text', 'binary', or 'unknown'; and 'n' is the number
        of elements in the item. If 'n' is 1, then 'desc' encodes the item's
        value.
        """

        self._checkOpen ()
        (desc, type, n) = _miriad_c.hdprobe (self.tno, itemname)

        if n == 0:
            raise MiriadError ('error probing item ' + itemname)

        return (desc, type, n)


    # Elaborations on the basic MIRIAD functions to make it easier
    # to read write simple array items

    def getArrayItem (self, itemname):
        """Read a dataset item as a homogeneous data array.

:arg str itemname: the name of the item to read
:returns: the item data
:rtype: ndarray or :class:`str`

This function reads an entire dataset item into a numpy array.  The
type of the array is determined from header information present in the
item data, and the size of the array is determined from the item
size. No size checking is performed, so attempting to load a very
large item can eat all of your memory.

Items marked as being of "text" or "mixed binary" type are read in
as Python strings.
"""

        desc, type, n = self.getItemInfo (itemname)

        if type == 'nonexistant':
            raise MiriadError ('trying to read nonexistant item ' + itemname)
        elif type == 'unknown':
            raise MiriadError ('cannot determine type of item ' + itemname)
        elif type == 'character':
            # Already gets read into desc for us.
            return desc
        elif type == 'integer*2':
            dtype = N.int16
        elif type == 'integer*8':
            dtype = N.int64
        elif type == 'integer':
            dtype = N.int32
        elif type == 'real':
            dtype = N.float32
        elif type == 'double':
            dtype = N.float64
        elif type == 'complex':
            dtype = N.complex64
        elif type == 'text' or type == 'binary':
            dtype = N.int8
        else:
            raise MiriadError ('unhandled type %s for item %s' % (type, itemname))

        # Mistakes in hdprobe() / no offset
        if type == 'text':
            n -= 4
            offset = 0
        elif type == 'binary':
            n -= 4
            offset = 4
        else:
            offset = max (4, dtype ().itemsize)

        item = self.getItem (itemname, 'r')
        data = item.read (offset, dtype, n)
        item.close ()
        return data


    def setArrayItem (self, itemname, dtype, value):
        """Set the value of a dataset item to a numpy array

:arg str itemname: the name of the item
:arg dtype: the format to use for storing the data
:type dtype: Numpy dtype or :class:`str`
:arg value: the data
:type value: Numpy ndarray
:returns: *self*

Sets the value of the specified item to an array of data. Due to
limitations in the MIRIAD I/O routines, data of type int16 are
not allowed. Data divided into 8-bit chunks should be given a
dtype of :class:`str`. The number of items to write is given
by the size of *value*.
"""
        if issubclass (dtype, str):
            self.setScalarItem (itemname, dtype, value)
            return self

        offset = max (4, dtype ().itemsize)
        self.setScalarItem (itemname, dtype, 0)
        item = self.getItem (itemname, 'a')
        item.write (offset, dtype, value)
        item.close ()
        return self


class DataItem (object):
    """An item contained within a Miriad dataset."""

    itno = None

    def __init__ (self, dataset, itemname, mode):
        # Must maintain reference to dataset to prevent it from being
        # GC'd out from under us:
        self.dataset = dataset
        self.name = itemname

        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        elif mode == 's': modestr = 'scratch'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.itno = _miriad_c.haccess (dataset.tno, itemname, modestr)

    def __del__ (self):
        # itno can be None if we got an exception inside haccess.

        if _miriad_c is None or self.itno is None:
            return
        self.close ()

    def close (self):
        _miriad_c.hdaccess (self.itno)
        self.itno = None

    def _checkOpen (self):
        if self.itno is not None:
            return
        raise RuntimeError ('Illegal operation on a closed dataset')

    def isOpen (self):
        return self.itno is not None


    def getSize (self):
        """Return the size of this data item."""

        self._checkOpen ()
        return _miriad_c.hsize (self.itno)


    def read (self, offset, dtype, count):
        """Read data from this item into a newly-allocated buffer.

:arg int offset: the byte offset into the item at which to read
:arg dtype: the type of data to read
:type dtype: Numpy dtype or :class:`str`
:arg count: the number of items to read
:returns: the data
:rtype: ndarray of data type *dtype*, or :class:`str`

Allocates a new buffer and reads data into it.

See also :meth:`readInto`.
"""
        self._checkOpen ()

        if dtype == N.int16:
            # MIRIAD, in its infinite stupid wisdom, unpacks int16s into ints
            # in its low-level I/O routines
            buf = N.empty (count, dtype=N.intc)
            buf2 = buf.view (dtype=N.int16)
            _miriad_c.hio_generic (False, self.itno, buf2, offset, count * 2)
            buf = buf.astype (N.int16)
        elif issubclass (dtype, str):
            buf = N.empty (count, dtype=N.int8)
            _miriad_c.hio_generic (False, self.itno, buf, offset, count)
            buf = buf.tostring ()
        else:
            buf = N.empty (count, dtype=dtype)
            _miriad_c.hio_generic (False, self.itno, buf, offset, count * dtype ().itemsize)

        return buf


    def readInto (self, offset, buf, count=None):
        """Read data from this item into a preexisting buffer.

:arg int offset: the byte offset into the item at which to read
:arg buf: the buffer into which the data should be read
:type buf: ndarray
:arg count: the number of items to read. :const:`None`, the
  default, signifies *buf.size*.
:returns: *buf*

Reads data into a preexisting buffer. The data are interpreted
as being of whatever format is specified by the data type of *buf*.

Item data that should be interpreted as strings cannot be read
with this function.

See also :meth:`read`.
"""
        self._checkOpen ()

        if count is None:
            count = buf.size

        if buf.dtype == N.int16:
            # See comment in read()
            buf2 = N.empty (count, dtype=N.intc)
            buf3 = buf2.view (dtype=N.int16)
            _miriad_c.hio_generic (False, self.itno, buf3, offset, count * 2)
            buf[:] = buf2
        else:
            _miriad_c.hio_generic (False, self.itno, buf, offset, count * buf.itemsize)

        return buf


    def write (self, offset, dtype, buf, count=None):
        """Write data to this item.

:arg int offset: the byte offset into the item at which to write
:arg dtype: the kind of data to write
:type dtype: Numpy dtype or :class:`str`
:arg buf: the data to write
:type buf: ndarray or other iterable
:arg count: the number of items to write. :const:`None`, the default,
  signifies *buf.size*.
:returns: *self*

Writes data to the item. Before writing, *buf* is converted to a numpy
ndarray if it is not already, then its contents are converted to the
format *dtype* if they are not already in that format. If *dtype*
is :class:`str`, *buf* is stringified, then that binary sequence is
written to the item.
"""
        self._checkOpen ()

        if issubclass (dtype, str):
            asbytes = N.fromstring (str (buf), dtype=N.int8)
            _miriad_c.hio_generic (True, self.itno, asbytes, offset, asbytes.size)
            return self

        buf = N.asarray (buf)
        if buf.dtype != dtype:
            buf = buf.astype (dtype)

        if count is None:
            count = buf.size

        if buf.dtype == N.int16:
            # See comment in read()
            buf2 = buf.astype (N.intc)
            buf3 = buf2.view (dtype=N.int16)
            _miriad_c.hio_generic (True, self.itno, buf3, offset, count * 2)
        else:
            _miriad_c.hio_generic (True, self.itno, buf, offset, count * buf.itemsize)

        return self

__all__ += ['DataSet', 'DataItem']


class UVDataSet (DataSet):
    def __init__ (self, path, mode):
        # Technically, 'old' mode is read-only with regard to the
        # UV data, but you can still write non-UV items.
        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        elif mode == 'a': modestr = 'append'
        else: raise ValueError ('Unsupported mode "%s"; "rw", "c", and "a" are allowed' % mode)

        self._path = path
        self.tno = _miriad_c.uvopen (path, modestr)

    def _close (self):
        _miriad_c.uvclose (self.tno)

    # These override the basic DataSet operations

    def flush (self):
        """Write out any unbuffered changes to the UV data set."""

        self._checkOpen ()
        _miriad_c.uvflush (self.tno)

    # UV-specific operations

    def next (self):
        """Skip to the next UV data record. On write, this causes an
        end-of-record mark to be written."""

        self._checkOpen ()
        _miriad_c.uvnext (self.tno)

    def rewind (self):
        """Rewind to the beginning of the file, allowing the UV data to
        be reread from the start."""

        self._checkOpen ()
        _miriad_c.uvrewind (self.tno)

    def lowlevelRead (self, preamble, data, flags, length=None):
        """Read a visibility record from the file. This function should
        be avoided in favor of the uvdat routines except for certain
        low-level manipulations. Length defaults to the length of the
        flags array.

        Returns: the number of items read."""

        if length is None: length = flags.size

        self._checkOpen ()
        return _miriad_c.uvread (self.tno, preamble, data, flags, length)

    def write (self, preamble, data, flags, length=None):
        """Write a visibility record consisting of the given preamble,
        data, flags, and length. Length defaults to the length of the
        flags array."""

        if length is None: length = flags.size

        self._checkOpen ()
        _miriad_c.uvwrite (self.tno, preamble, data, flags, length)

    def rewriteFlags (self, flags):
        """Rewrite the channel flagging data for the current
        visibility record. 'flags' should be a 1D integer ndarray of the
        same length and dtype returned by a uvread call."""

        self._checkOpen ()
        _miriad_c.uvflgwr (self.tno, flags)


    # UV variables

    def getScalar (self, variable, default=None, missingok=True):
        """Get the value of a scalar UV variable.

:arg str variable: the name of the variable to fetch
:arg any default: the value to return if the variable is not
  defined in this dataset; defaults to :const:`None`.
:arg bool missingok: if *default* should be returned if the
  variable is not defined in this dataset; defaults to :const:`True`.
  If :const:`False` and the variable is not defined, raises
  :exc:`ValueError`.
:returns: the value
:rtype: numpy scalar type

This gets the value of a scalar UV variable, possibly returning
a default value if the variable is not found. The return value
is a numpy scalar type appropriate for the UV variable. Note that
these types propagate, so there is a danger of overflow or underflow
if you do some kinds of math with the return value. Furthermore,
if you provide *default*, it will usually be one of the builting
Python numeric types, not a NumPy type, so if code depends on the
type of the return value, there may be variations in behavior
depending on whether the variable was found or not.

This function actually succeeds for array-valued UV variables as well.
In that case, the first array element is returned. The most common
use of this function, however, is for variables like *nants* that
have only one value (unless the dataset is semantically invalid).
"""
        self._checkOpen ()
        res = _miriad_c.uvrdvr_generic (self.tno, variable)
        if res is None:
            if not missingok:
                raise ValueError ('no such UV variable "%s"' % variable)
            return default
        return res


    # uvinfo exploders

    def getLineInfo (self):
        """Get line information about the current UV record.

:returns: line information, described below.
:rtype: six-element integer ndarray

The six integers are ``[linetype, nchan, chan0, width, step, win0]``.

* **linetype** -- the kind of data being read. 1 indicates spectral
  data; 2 indicates wideband data; 3 indicates velocity-space data.
  (Symbolic constants for these are defined in mirtask.util.)
* **nchan** -- the number of channels in the record.
* **chan0** -- the index of the first channel in the record. (This
  index is 1-based in the MIRIAD API, but is adjusted to be 0-based in
  miriad-python).
* **width** -- the number of input channels that are averaged together.
* **step** -- the increment between selected input channels.
* **win0** -- If reading spectral or wideband data, -1. If resampling
  in velocity space, returns the index of the first spectral window
  contributing to the returned data. (This index is 1-based in the
  MIRIAD API, and the null return value is 0, but is likewise adjusted
  to be 0-based here.)
"""
        self._checkOpen ()
        info = N.zeros (6, dtype=N.double)
        _miriad_c.uvinfo (self.tno, 'line', info)
        # FIXME: in e.g. velocity linetype, step/width/etc will be
        # nonintegral
        info = info.astype (N.int)
        # Convert Fortran 1-based index to 0-based
        info[2] -= 1
        info[5] -= 1
        return info


    def getCurrentVisNum (self):
        """Get the serial number of the current UV record.

:returns: the serial number
:rtype: int

Counting begins at zero.
"""
        self._checkOpen ()
        info = N.zeros (1, dtype=N.double)
        _miriad_c.uvinfo (self.tno, 'visno', info)
        # Convert Fortran 1-based index to 0-based
        return int (info[0]) - 1


    def getLinetype (self, astext=False):
        """Get the linetype of the current UV record.

:arg bool astext: if :const:`True`, return the linetype as its
  textual value rather than its integer code; default is :const:`False`.
:returns: the linetype
:rtype: int or str

The linetype values are enumerated in :func:`mirtask.util.linetypeName`.
"""
        self._checkOpen ()
        info = N.zeros (6, dtype=N.double)
        _miriad_c.uvinfo (self.tno, 'line', info)
        linetype = int (info[0])

        if not astext:
            return linetype

        from mirtask.util import linetypeName
        return linetypeName (linetype)


    def getPol (self):
        """Get the polarization code of the current record.

:returns: the polarization code
:rtype: int

For a regular UV dataset, this is just equivalent to reading
the "pol" UV variable. :class:`mirtask.uvdat.UVDatDataSet` instances
require more complicated processing.

The default polarization is Stokes I. See the constants in
:mod:`mirtask.util`.
"""
        return self.getScalar ('pol', 1)


    def getNPol (self):
        """Get the number of simultaneous polarizations.

:returns: the number
:rtype: int

For a regular UV dataset, this is just equivalent to reading
the "npol" UV variable. :class:`mirtask.uvdat.UVDatDataSet` instances
require more complicated processing.

The "npol" quantity is used for on-the-fly Stokes processing of UV
data.  If a full-Stokes correlator is taking data, the ideal output
format is one in which there are four consecutive UV records for each
baseline / time combination: one for each simultaneous Stokes
parameter. The four records can then easily be combined to perform
Stokes conversions (e.g. XX and YY to I) with minimal overhead. In
order to be able to do this, the Stokes processing code needs to know
whether consecutive records have the desired properties, or not. The
UV variable npol records this information.
"""
        return self.getScalar ('npol', 1)


    def getJyPerK (self):
        """Get the Jy/K calibration of the current record

:returns: the Jy/K value
:rtype: float

For a regular UV dataset, this is just equivalent to reading
the "jyperk" UV variable. :class:`mirtask.uvdat.UVDatDataSet` instances
require more complicated processing.

Returns zero if the value could not be determined.
"""
        return self.getScalar ('jyperk', 0.)


    def getVariance (self):
        """Get the variance of the first channel of the current UV record.

:returns: the variance
:rtype: double

Keep in mind that if the read-in data comprise multiple windows
with different channel bandwidths, the variance needs to be scaled
appropriately: ``variance ~ 1 / sqrt (bandwidth)``.

Returns zero if the variance could not be determined.
"""
        self._checkOpen ()
        info = N.zeros (1, dtype=N.double)
        _miriad_c.uvinfo (self.tno, 'variance', info)
        return info[0]


    def baselineShadowed (self, diameter_meters):
        """Returns whether the most recently-read UV record comes from
        antennas that were shadowed, assuming a given antenna
        diameter.

        In order for this function to operate, you must apply a UV
        selection of the form "auto,or,-auto,or,shadow(1)". This is a
        necessary hack to enable the internal UVW recomputation needed
        for shadow testing. Obviously, the example selection doesn't
        filter out any data. If an appropriate "shadow()" selection is
        not applied, a :exc:`MiriadError` will be raised.

        This function depends on an API in the MIRIAD UV I/O library
        that may not necessarily be exposed. If this is the case, this
        function will raise a :exc:`NotImplementedError`. You can
        check in advance whether this function is available by
        checking the return value of
        :func:`mirtask._miriad_c.probe_uvchkshadow`, :const:`True`
        indicating availability.

        *diameter_meters* - the diameter within which an antenna is
          considered shadowed, measured in meters.

        Returns: boolean."""

        self._checkOpen ()
        return _miriad_c.uvchkshadow (self.tno, diameter_meters)


    # uvset exploders

    def _uvset (self, object, type, n, p1, p2, p3):
        self._checkOpen ()
        _miriad_c.uvset (self.tno, object, type, n, p1, p2, p3)

    def setPreambleType (self, *vars):
        """Specify up to five variables to put in the preamble block.
        Should be given a list of variable names; 'uv' and 'uvw' are
        a special expansion of 'coord' that expand out to their
        respective UV coordinates. Default list is 'uvw', 'time',
        'baseline'."""

        self._uvset ('preamble', '/'.join (vars), 0, 0., 0., 0.)

    def setCorrelationType (self, type):
        """Set the correlation type that will be used in this
        vis file."""

        self._uvset ("corr", type, 0, 0., 0., 0.)

    # oh god there are a bunch more of these: data linetype, refernce
    # linetype, gflag, flags, corr

    # Variable handling

    def copyMarkedVars (self, output):
        """Copy variables in this data set to the output data set. Only
        copies those variables which have changed and are marked as
        'copy'."""

        self._checkOpen ()
        _miriad_c.uvcopyvr (self.tno, output.tno)

    def updated (self):
        """Return true if any user-specified 'important variables' have
        been updated in the last chunk of data read."""

        self._checkOpen ()
        return bool (_miriad_c.uvupdate (self.tno))

    def initVarsAsInput (self, linetype):
        """Initialize the UV reading functions to copy variables from
        this file as an input file. Linetype should be one of 'channel',
        'wide', or 'velocity'. Maps to Miriad's varinit() call."""

        self._checkOpen ()
        _miriad_f.varinit (self.tno, linetype)

    def initVarsAsOutput (self, input, linetype):
        """Initialize this dataset as the output file for the UV
        reading functions. Linetype should be one of 'channel', 'wide',
        or 'velocity'. Maps to Miriad's varonit() call."""

        self._checkOpen ()
        _miriad_f.varonit (input.tno, self.tno, linetype)

    def copyLineVars (self, output):
        """Copy UV variables to the output dataset that describe the
        current line in the input set."""

        self._checkOpen ()
        _miriad_f.varcopy (self.tno, output.tno)

    def makeVarTracker (self):
        """Create a UVVarTracker object, which can be used to track
        the values of UV variables and when they change."""

        return UVVarTracker (self)

    def probeVar (self, varname):
        """Get information about a given variable. Returns (type, length,
        updated) or None if the variable is undefined.

        type - The variable type character: a (text), r ("real"/float),
        i (int), d (double), c (complex)

        length - The number of elements in this variable; zero if unknown.

        updated - True if the variable was updated on the last UV data read.
        """

        self._checkOpen ()
        (type, length, updated) = _miriad_c.uvprobvr (self.tno, varname)

        if type == '' or type == ' ': return None
        return (type, length, updated)

    def getVarString (self, varname):
        """Retrieve the current value of a string-valued UV
        variable. Maximum length of 512 characters."""

        self._checkOpen ()
        return _miriad_c.uvgetvra (self.tno, varname)

    def getVarInt (self, varname, n=1):
        """Retrieve the current value or values of an int32-valued UV
        variable."""

        self._checkOpen ()
        ret = _miriad_c.uvgetvri (self.tno, varname, n)

        if n == 1:
            return ret[0]
        return ret

    def getVarShort (self, varname, n=1):
        """Retrieve the current value or values of an int16-valued UV
        variable."""

        self._checkOpen ()
        ret = _miriad_c.uvgetvrj (self.tno, varname, n)

        if n == 1:
            return ret[0]
        return ret

    def getVarFloat (self, varname, n=1):
        """Retrieve the current value or values of a float-valued UV
        variable."""

        self._checkOpen ()
        ret = _miriad_c.uvgetvrr (self.tno, varname, n)

        if n == 1:
            return ret[0]
        return ret

    def getVarDouble (self, varname, n=1):
        """Retrieve the current value or values of a double-valued UV
        variable."""

        self._checkOpen ()
        ret = _miriad_c.uvgetvrd (self.tno, varname, n)

        if n == 1:
            return ret[0]
        return ret

    def getVarComplex (self, varname, n=1):
        """Retrieve the current value or values of a complex-valued UV
        variable."""

        self._checkOpen ()
        ret = _miriad_c.uvgetvrc (self.tno, varname, n)

        if n == 1:
            return ret[0]
        return ret

    def trackVar (self, varname, watch, copy):
        """Set how the given variable is tracked. If 'watch' is true, updated()
        will return true when this variable changes after a chunk of UV data
        is read. If 'copy' is true, this variable will be copied when
        copyMarkedVars() is called.
        """

        switches = ''
        if watch: switches += 'u'
        if copy: switches += 'c'

        self._checkOpen ()
        _miriad_c.uvtrack (self.tno, varname, switches)

    def scanUntilChange (self, varname):
        """Scan through the UV data until the given variable changes. Reads
        to the end of the record in which the variable changes. Returns False
        if end-of-file was reached, True otherwise."""

        self._checkOpen ()
        return _miriad_c.uvscan (self.tno, varname) == 0

    def writeVarInt (self, name, val):
        """Write an integer UV variable. val can either be a single value or
        an ndarray for array variables."""

        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.int32)
            v2[0] = int (val)
            val = v2

        _miriad_c.uvputvri (self.tno, name, val)

    def writeVarFloat (self, name, val):
        """Write an float UV variable. val can either be a single value or
        an ndarray for array variables."""

        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.float32)
            v2[0] = float (val)
            val = v2

        _miriad_c.uvputvrr (self.tno, name, val)

    def writeVarDouble (self, name, val):
        """Write a double UV variable. val can either be a single value or
        an ndarray for array variables."""

        self._checkOpen ()

        if not isinstance (val, N.ndarray):
            v2 = N.ndarray (1, dtype=N.float64)
            v2[0] = float (val)
            val = v2

        _miriad_c.uvputvrd (self.tno, name, val)

    def writeVarString (self, name, val):
        """Write a string UV variable. val will be stringified."""

        self._checkOpen ()
        _miriad_c.uvputvra (self.tno, name, str (val))


class UVVarTracker (object):
    def __init__ (self, owner):
        # Must maintain a reference to the dataset to prevent it from
        # being GC'd under us:
        self.dataset = owner
        self.vhnd = _miriad_c.uvvarini (owner.tno)

    def track (self, *vars):
        """Indicate that the specified variable(s) should be tracked by this
        tracker. Returns *self* for convenience."""

        for var in vars:
            _miriad_c.uvvarset (self.vhnd, var)
        return self

    def copyTo (self, output):
        """Copy the variables tracked by this tracker into the output
        data set."""

        _miriad_c.uvvarcpy (self.vhnd, output.tno)

    def updated (self):
        """Return true if one of the variables tracked by this tracker
        was updated in the last UV data read."""

        return bool (_miriad_c.uvvarupd (self.vhnd))

__all__ += ['UVDataSet', 'UVVarTracker']

MASK_MODE_FLAGS = 1
MASK_MODE_RUNS = 2
_maskModes = set ((MASK_MODE_FLAGS, MASK_MODE_RUNS))

class MaskItem (object):
    """A 'mask' item contained within a Miriad dataset."""

    def __init__ (self, dataset, itemname, mode):
        # must maintain ref to dataset to prevent it from being GC'd
        # out from under us:
        self.dataset = dataset
        self.name = itemname
        self.handle = None

        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.handle = _miriad_c.mkopen (dataset.tno, itemname, modestr)


    def read (self, mode, flags, offset, n):
        if mode not in _maskModes:
            raise ValueError ('Unexpected mask mode %d' % mode)
        self._checkOpen ()
        return _miriad_c.mkread (self.handle, mode, flags, offset, n)


    def write (self, mode, flags, offset, n=None):
        if mode not in _maskModes:
            raise ValueError ('Unexpected mask mode %d' % mode)
        if n is None:
            n = flags.size
        self._checkOpen ()
        _miriad_c.mkwrite (self.handle, mode, flags, offset, n)


    def flush (self):
        self._checkOpen ()
        _miriad_c.mkflush (self.handle)


    def close (self):
        self._checkOpen ()
        _miriad_c.mkclose (self.handle)
        self.handle = None


    def isOpen (self):
        return self.handle is not None


    def _checkOpen (self):
        if self.handle is not None:
            return
        raise RuntimeError ('Illegal operation on a closed mask item')


    def __del__ (self):
        if _miriad_c is None or self.handle is None:
            return

        self.close ()


__all__ += ['MaskItem', 'MASK_MODE_FLAGS', 'MASK_MODE_RUNS']


_AXTYPE_LAT, _AXTYPE_LONG, _AXTYPE_SPEC, _AXTYPE_LIN = range (4)

_axinfo_map = {
    'DEC': (_AXTYPE_LAT, 'rad', None),
    'ELAT': (_AXTYPE_LAT, 'rad', None),
    'ELON': (_AXTYPE_LONG, 'rad', None),
    'FELO': (_AXTYPE_SPEC, 'km/s', 'VOPT'),
    'FREQ': (_AXTYPE_SPEC, 'GHz', None),
    'GLAT': (_AXTYPE_LAT, 'rad', None),
    'GLON': (_AXTYPE_LONG, 'rad', None),
    'RA': (_AXTYPE_LONG, 'rad', None),
    'VELO': (_AXTYPE_SPEC, 'km/s', None),
    'VOPT': (_AXTYPE_SPEC, 'km/s', None),
}

_longlat_map = {
    'RA': 'DEC',
    'ELON': 'ELAT',
    'GLON': 'GLAT',
}


class CoordinateError (StandardError):
    def __init__ (self, fmt, *args):
        if not len (args):
            self.themessage = str (fmt)
        else:
            self.themessage = fmt % args

    def __str__ (self):
        return self.themessage


class XYDataSet (DataSet):
    """:synopsis: an opened image dataset

This class provides access to MIRIAD image data. It allows whole image
planes to be read in easily using the :meth:`XYDataSet.readPlane`
function.

You shouldn't create :class:`XYDataSet` instances directly. Instead,
use :meth:`miriad.ImData.open`.
"""

    axes = None
    """An integer ndarray of axis sizes. Stored in "inside-out"
    format: ``axes[0]`` is the most quickly-varying axis, almost
    always the image column number. ``axes[1]`` is the second-most
    quickly-varying axis, almost always the image row number. *axes*
    is set upon creation of the instance and modifications to it after
    that point have no effect (besides probably causing the methods
    to crash).
    """

    _wcs = None

    def __init__ (self, path, mode, axes=None):
        if mode == 'rw':
            modestr = 'append'
        elif mode == 'c':
            modestr = 'new'
        else:
            raise ValueError ('unsupported mode "%s"; expect "rw" or "c"' % mode)

        if axes is not None:
            axes = N.atleast_1d (axes).copy ()
        else:
            if mode == 'c':
                raise ValueError ('axes must be specified when creating a new XY dataset')
            axes = N.zeros (16, dtype=N.intc)

        self.axes = axes
        self._path = path
        self.tno = _miriad_c.xyopen (path, modestr, axes.size, axes)

        if mode == 'rw':
            self.axes = axes = axes[:self.getScalarItem ('naxis', 0)]

        self._databuf = N.empty (axes[0], dtype=N.float32)
        self._flagbuf = N.empty (axes[0], dtype=N.intc)
        self._npmaskbuf = N.empty (axes[0], dtype=N.bool)
        self._masked = N.ma.masked_array (self._databuf, self._npmaskbuf,
                                          copy=False)


    def _close (self):
        _miriad_c.xyclose (self.tno)


    def wcs (self):
        """Retrieve a :class:`pywcs.WCS` object representing the coordinate system
of this image.

:rtype: :class:`pywcs.WCS`, :class:`list` of :class:`str`
:returns: tuple of (*wcs*, *warnings*)
:raises: :exc:`ImportError` if :mod:`pywcs` is not available
:raises: :exc:`MemoryError` if memory for the instance couldn't be allocated

Note that ``wcslib``, and hence :mod:`pywcs`, use degrees internally, unlike
MIRIAD.

This function returns a tuple of a WCS coordinate system object and a list
of warnings encountered when setting up the coordinate system. It's up to
the caller to decide what to do about the warnings, including whether and
how to present them to the user.

At the moment, we do not encourage newly-written Python code to attempt to
use the classical MIRIAD APIs for coordinate manipulation.
"""
        if self._wcs is not None:
            return self._wcs

        import pywcs

        w = pywcs.WCS (naxis=self.axes.size)
        # Need to set properties array-at-a-time
        work = N.empty ((3, self.axes.size))
        ctypes = [None] * self.axes.size
        cunits = [None] * self.axes.size
        warnings = []

        # Combination of setup and fixups. Most of the latter are
        # copied from co.for:coReinit() in MIRIAD. WCSLIB uses degrees
        # internally (??) so we need to deal with that by setting the
        # coordinate units. The WCSLIB documentation suggests that
        # wcsset() actually performs the projection fixups, so much of
        # this work may be pointless ...  but it's all in coReinit() and
        # I believe the code is all written by the same person, Mark
        # Calabretta.
        #
        # TODO: if coReinit runs into a "fatal" error, it assumes linear
        # axes everywhere. We could do the same.
        #
        # Of course, the fixup code is completely untested, because
        # I don't have a bunch of wacky-projection images lying around.
        # Yay!

        latax = longax = specax = None
        lattype = longtype = None
        latproj = longproj = None

        for i in xrange (self.axes.size):
            ctype = ctypes[i] = self.getScalarItem ('ctype%d' % (i + 1), '')
            cunits[i] = ''
            axtype = _AXTYPE_LIN

            for pfx, info in _axinfo_map.iteritems ():
                if ctype.startswith (pfx):
                    if info[0] is not None:
                        axtype = info[0]
                    if info[1] is not None:
                        cunits[i] = info[1]
                    if info[2] is not None:
                        ctype = ctypes[i] = info[2] + ctype[len (info[2]):]
                    break

            if axtype == _AXTYPE_LAT:
                if latax is None:
                    latax = i
                    lattype = pfx
                    latproj = ctypes[i].split ('-')[-1].upper ()
                else:
                    # We can still go ahead and try to be helpful here.
                    warnings.append ('multiple latitude axes')
            elif axtype == _AXTYPE_LONG:
                if longax is None:
                    longax = i
                    longtype = pfx
                    longproj = ctypes[i].split ('-')[-1].upper ()
                else:
                    warnings.append ('multiple longitude axes')
            elif axtype == _AXTYPE_SPEC:
                if specax is None:
                    specax = i
                else:
                    warnings.append ('multiple spectral axes')

            work[0,i] = self.getScalarItem ('cdelt%d' % (i + 1), 1)
            work[1,i] = self.getScalarItem ('crval%d' % (i + 1), 1)
            work[2,i] = self.getScalarItem ('crpix%d' % (i + 1), 1)

        w.wcs.ctype = ctypes
        w.wcs.cunit = cunits
        w.wcs.cdelt = work[0]
        w.wcs.crval = work[1]
        w.wcs.crpix = work[2]
        # I believe this is correct; see uvvars.inc:
        w.wcs.equinox = self.getScalarItem ('epoch', 2000.0)
        w.wcs.restfrq = self.getScalarItem ('restfreq', 0.) * 1e9

        if (longax is None) ^ (latax is None):
            raise CoordinateError ('unpaired celestial axis')

        if longax is not None:
            if latproj != longproj:
                raise CoordinateError ('celestial axes have different projections')

            if _longlat_map[longtype] != lattype:
                raise CoordinateError ('incompatible celestial axes')

            long0 = work[1,longax]
            lat0 = work[1,latax]

            # "crval was stored as [float32] in older Miriad images,
            # whence rounding errors may carry the reference latitude
            # at the pole beyond 90 deg by more than the tolerance
            # allowed by WCSLIB."

            if abs (lat0) > 90:
                if abs (lat0) < 90.00005:
                    # "Assume it's a rounding error"
                    lat0 = 90. * (lat0 / abs (lat0))
                else:
                    # "Do something tricky"
                    lat0 = (180. - abs (lat0)) * (lat0 / abs (lat0))
                    long0 += 180

                    if long0 >= 360:
                        long0 -= 360

            _miriad_c.mirwcs_set_celref (w.wcs, long0, lat0)

            if latproj == 'NCP':
                # "Convert NCP to SIN"
                if lat0 == 0:
                    raise CoordinateError ('NCP proj may not have lat0 = 0')

                _miriad_c.mirwcs_set_prjcode (w.wcs, 'SIN')
                # possibly redundant with w.wcs.set_pv ?
                _miriad_c.mirwcs_set_prjpv (w.wcs, 1, 0.)
                _miriad_c.mirwcs_set_prjpv (w.wcs, 2, 1./N.tan (lat0 * N.pi/180))
            elif latproj == 'GLS':
                # "Convert GLS to SFL"
                _miriad_c.mirwcs_set_celoffset (w.wcs, 1)
                _miriad_c.mirwcs_set_celphitheta (w.wcs, 0, lat0)
                _miriad_c.mirwcs_set_prjcode (w.wcs, 'SFL')
            else:
                _miriad_c.mirwcs_set_prjcode (w.wcs, latproj)

            result = _miriad_c.mirwcs_celset (w.wcs)
            if result is not None:
                raise CoordinateError (result)

        try:
            w.wcs.set ()
        except Exception, e:
            raise CoordinateError (e)

        self._wcs = w
        return w, warnings


    def flush (self):
        """Write any pending changes to disk.

:returns: *self*
"""

        self._checkOpen ()
        _miriad_c.xyflush (self.tno)
        return self


    def setPlane (self, axes=[]):
        """Set the active plane for reading or writing.

:type axes: int ndarray
:arg axes: the pixel coordinates of the non-plane axes (default zeros)
:returns: *self*

A MIRIAD image can have any (reasonable) number of dimensions, but is
typically read one "plane" at a time. A plane comprises a subcube of
the first two axes of data with the coordinates of the other axes held
constant. This routine sets the pixel coordinate values of the other axes.

If an image has *n* axes, *axes* should have at most ``n - 2`` elements,
because two axes refer to the plane being read. However, *axes* may
have fewer elements, with the pixel values of the outer axes being set
to zero. It is valid for *axes* to be an empty list, specifying that
all non-axis coordinates should be set to zero, and this is in fact the
default argument.

Note that in MIRIAD, array indices are Fortran style and begin at one;
in this function, as in Python in general, array indices begin at zero.
"""

        self._checkOpen ()
        # C/Python to Fortran index convention:
        axes = N.asarray (axes).astype (N.intc) + 1
        _miriad_c.xysetpl (self.tno, axes.size, axes)
        return self


    def readRow (self, rownum):
        """Read a row of data from the current plane

:arg int rownum: the zero-based for number to read
:returns: a masked ndarray of data

The method :meth:`setPlane` must be called before the first attempt to
read or write image data.

Reads one row of data and flags from the current plane into a
buffer. The returned array has a shape of ``(self.axes[0], )``.
The buffer is stored in the object instance and is shared
between all I/O calls, so be careful with concurrent access.

See also :meth:`readRows` and :meth:`readPlane`.
"""
        if rownum < 0 or rownum >= self.axes[1]:
            raise ValueError ('rownum must be >= 0 and < %d' % self.axes[1])

        self._checkOpen ()
        _miriad_c.xyread (self.tno, rownum + 1, self._databuf)
        _miriad_c.xyflgrd (self.tno, rownum + 1, self._flagbuf)
        N.logical_not (self._flagbuf, self._npmaskbuf)
        return self._masked


    def readRows (self, topIsZero=False):
        """Read all rows of data from the current plane

:arg bool topIsZero: whether to invert the image ordering from
  MIRIAD's bottom-to-top ordering to top-to-bottom
:returns: generator yielding masked ndarray of data

Reads all rows of data and flags from the current plane into a
buffer. The returned arrays have a shape of ``(self.axes[0], )``.  The
buffer is stored in the object instance and is shared between all I/O
calls, so be careful with concurrent access.

The method :meth:`setPlane` must be called before the first attempt to
read or write image data.

MIRIAD's image coordinate system is "bottom-to-top", where pixel ``(0,
0)`` in a plane is its bottom-left pixel. This can be counterintuitive,
but all of MIRIAD's coordinate routines rely on this system, so you
should attempt to get used to it. However, in certain cases it can be
useful to read in a plane such that pixel ``(0, 0)`` is its top-right
pixel. Setting *topIsZero* to :const:`True` does this.

See also :meth:`readPlane` and :meth:`readRow`.
"""
        self._checkOpen ()
        nrow = self.axes[1]

        if not topIsZero:
            for i in xrange (1, nrow + 1):
                _miriad_c.xyread (self.tno, i, self._databuf)
                _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
                N.logical_not (self._flagbuf, self._npmaskbuf)
                yield self._masked
        else:
            for i in xrange (nrow, 0, -1):
                _miriad_c.xyread (self.tno, i, self._databuf)
                _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
                N.logical_not (self._flagbuf, self._npmaskbuf)
                yield self._masked


    def readPlane (self, axes=None, buf=None, topIsZero=False):
        """Read the current plane.

:arg axes: the pixel coordinates of the non-plane axes, or :const:`None`
  (the default) to use the current axes
:type axes: int ndarray
:arg buf: the buffer into which the data are stored, or :const:`None`
  (the default) to allocate a new buffer
:type buf: masked ndarray of shape (nrow, ncol)
:arg bool topIsZero: whether to invert the image ordering from
  MIRIAD's bottom-to-top ordering to top-to-bottom
:returns: the buffer
:raises: :exc:`MiriadError` about end-of-file if MIRIAD doesn't know
  which plane to read

Reads the current plane into a buffer. If *buf* is not :const:`None`,
it must be of shape ``(nrow, ncol)`` (equivalently, ``(self.axes[1],
self.axes[0])``) and be a masked ndarray. Otherwise, a new buffer is
allocated.

You must tell MIRIAD which image plane you wish to read before calling
this function -- otherwise, a :exc:`MiriadError` about end-of-file is
raised. You can do this either by giving a non-:const:`None` value to
the *axes* argument, or by calling :meth:`setPlane` explicitly. (The
former approach is a shorthand for the latter.) Note that the default
value of *axes* (:const:`None`) doesn't change which plane should be
read, but also doesn't choose a plane if none has been chosen
already. If you want to read the first plane in an image without any
setup, the correct call is::

   data = ImData ('path').open ('rw').readPlane (axes=[])

MIRIAD's image coordinate system is "bottom-to-top", where pixel ``(0,
0)`` in a plane is its bottom-left pixel. This can be counterintuitive,
but all of MIRIAD's coordinate routines rely on this system, so you
should attempt to get used to it. However, in certain cases it can be
useful to read in a plane such that pixel ``(0, 0)`` is its top-right
pixel. Setting *topIsZero* to :const:`True` does this.

See also :meth:`readRows` and :meth:`readRow`.
"""
        ncol, nrow = self.axes[:2]

        if buf is None:
            data = N.empty ((nrow, ncol), dtype=N.float32)
            mask = N.empty ((nrow, ncol), dtype=N.bool)
            buf = N.ma.masked_array (data, mask, copy=False)
        else:
            buf = N.ma.atleast_2d (buf)

            if buf.ndim != 2:
                raise ValueError ('buf must be 2d')
            if buf.shape != (nrow, ncol):
                raise ValueError ('buf must have shape (%d, %d)' % (nrow, ncol))

            data, mask = buf.data, buf.mask

        self._checkOpen ()

        if axes is not None:
            self.setPlane (axes)

        if not topIsZero:
            for i in xrange (1, nrow + 1):
                _miriad_c.xyread (self.tno, i, data[i-1])
                _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
                N.logical_not (self._flagbuf, mask[i-1])
        else:
            for i in xrange (1, nrow + 1):
                _miriad_c.xyread (self.tno, i, data[nrow - i])
                _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
                N.logical_not (self._flagbuf, mask[nrow - i])

        return buf


    def writeRow (self, rownum, maskeddata):
        """Write a row of data to the current plane

:arg int rownum: the zero-based for number to read
:arg maskeddata: the data to write
:type maskeddata: numpy maskedarray
:returns: *self*

Writes one row of data and flags to the current plane. The argument
*maskeddata* must have a shape of ``(self.axes[0], )``.  *rownum*
should be between zero and ``self.axes[1] - 1``.

The method :meth:`setPlane` must be called before the first attempt to
read or write image data.

See also :meth:`writePlane`.
"""
        maskeddata = N.ma.atleast_1d (maskeddata)

        if rownum < 0 or rownum >= self.axes[1]:
            raise ValueError ('rownum must be >= 0 and < %d' % self.axes[1])
        if maskeddata.ndim != 1:
            raise ValueError ('maskeddata must be 1d')
        if maskeddata.size != self.axes[0]:
            raise ValueError ('maskeddata must be of size %d' % self.axes[0])

        self._checkOpen ()
        if maskeddata.data.dtype == N.float32:
            data = maskeddata.data
        else:
            data = maskeddata.data.astype (N.float32)
        N.logical_not (maskeddata.mask, self._flagbuf)
        _miriad_c.xywrite (self.tno, rownum + 1, data)
        _miriad_c.xyflgwr (self.tno, rownum + 1, self._flagbuf)
        return self


    def writePlane (self, maskeddata, axes=None, topIsZero=False):
        """Write a plane of data.

:arg maskeddata: the data buffer
:type maskeddata: masked ndarray of shape (nrow, ncol)
:arg axes: the pixel coordinates of the non-plane axes, or :const:`None`
  (the default) to use the current axes
:type axes: int ndarray
:arg bool topIsZero: whether to invert the image ordering from
  MIRIAD's bottom-to-top ordering to top-to-bottom
:returns: *self*

Writes data to the current plane. *buf* must be of shape ``(nrow,
ncol)`` (equivalently, ``(self.axes[1], self.axes[0])``) and be a
masked ndarray.

The method :meth:`setPlane` must be called before the first attempt to
read or write image data. If *axes* is not :const:`None`,
:meth:`setPlane` will be called with axes as an argument before
performing the read.

MIRIAD's image coordinate system is "bottom-to-top", where pixel ``(0,
0)`` in a plane is its bottom-left pixel. This can be
counterintuitive, but all of MIRIAD's coordinate routines rely on this
system, so data will likely come in this format. Howeve, if
*maskeddata* is stored in a top-to-bottom system, where pixel ``(0,
0)`` is its top-right pixel, setting *topIsZero* to :const:`True` will
write out the data in the correct order.

See also :meth:`writeRow`.
"""
        maskeddata = N.atleast_2d (N.ma.asarray (maskeddata))
        ncol, nrow = self.axes[:2]

        if maskeddata.ndim != 2:
            raise ValueError ('maskeddata must be 2d')
        if maskeddata.shape != (nrow, ncol):
            raise ValueError ('maskeddata must be of shape (%d, %d)' %
                              (nrow, ncol))

        self._checkOpen ()

        if axes is not None:
            self.setPlane (axes)

        if maskeddata.mask is N.ma.nomask:
            self._flagbuf.fill (True)
            fillbuf = lambda i: i # can't have a pass lambda
        else:
            fillbuf = lambda i: N.logical_not (maskeddata.mask[i],
                                               self._flagbuf)

        if not topIsZero:
            for i in xrange (1, nrow + 1):
                fillbuf (i - 1)
                _miriad_c.xywrite (self.tno, i, maskeddata[i-1])
                _miriad_c.xyflgwr (self.tno, i, self._flagbuf)
        else:
            for i in xrange (1, nrow + 1):
                fillbuf (nrow - i)
                _miriad_c.xywrite (self.tno, i, maskeddata[nrow - i])
                _miriad_c.xyflgwr (self.tno, i, self._flagbuf)

        return self


__all__ += ['XYDataSet']
