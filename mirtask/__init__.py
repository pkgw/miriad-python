'''mirtask - basic classes for implementing MIRIAD tasks in Python'''

# Copyright 2009, 2010, 2011 Peter Williams
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


# Very simple wrapper classes. Shouldn't necessarily be used,
# given that there are standard APIs like uvdat*

class DataSet (object):
    """A generic Miriad data-set. Subclasses must implement a _close()
    method."""

    tno = None

    def __del__ (self):
        # tno can be None if we got an exception inside hopen,
        # or if we are deleteAll'ed

        if _miriad_c is None or self.tno is None:
            return

        self._close ()

    def __repr__ (self):
        if hasattr (self, 'name'):
            return 'DataSet (%s)' % (repr (self.name))
        return 'DataSet (<unknown filename>)'

    def __str__ (self):
        if hasattr (self, 'name'):
            nstr = '\"%s\"' % (self.name, )
        else:
            nstr = '[unknown filename]'

        if self.tno is not None:
            hstr = 'handle %d' % self.tno
        else:
            hstr = 'not currently open'

        return '<DataSet %s %s>' % (nstr, hstr)

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

    def getItem (self, keyword, mode):
        """Return a DataItem object representing the desired item
        within this dataset. See the documentation of the DataItem
        constructor for the meaning of the 'keyword' and 'mode'
        parameters.
        """

        if keyword == '.': raise ValueError ("Use itemNames() instead.")

        return DataItem (self, keyword, mode)

    def itemNames (self):
        """Generate a list of the names of the data items contained in
        this data set."""

        ilist = DataItem (self, '.', 'r')
        s = ilist.getSize ()

        while ilist.getPosition () < s:
            yield ilist.seqReadString ()

        ilist.close ()

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
        _miriad_c.hiswrite (tno, prefix + 'Executed on: ' + date)
        _miriad_c.hiswrite (tno, prefix + 'Command line inputs follow:')

        prefix += '  '
        dofile = False

        for arg in args:
            if dofile:
                f = open (arg, 'r')
                for line in f:
                    _miriad_c.hiswrite (tno, prefix + line)
                f.close ()
                dofile = False
            else:
                if arg == '-f':
                    dofile = True
                else:
                    _miriad_c.hiswrite (tno, prefix + arg)

        return self


    def closeHistory (self):
        """Close this data set's history item."""

        self._checkOpen ()
        _miriad_c.hisclose (self.tno)
        self._histOpen = False

    # Header variables

    def getHeaderFloat (self, keyword, default):
        """Retrieve the value of a float-valued header variable."""

        self._checkOpen ()
        return _miriad_c.rdhdr (self.tno, keyword, float (default))

    def getHeaderInt (self, keyword, default):
        """Retrieve the value of an int32-valued header variable."""

        self._checkOpen ()
        return _miriad_c.rdhdi (self.tno, keyword, int (default))

    def getHeaderLong (self, keyword, default):
        """Retrieve the value of an int64-valued header variable."""

        self._checkOpen ()
        return _miriad_c.rdhdl (self.tno, keyword, N.int64 (default))

    def getHeaderDouble (self, keyword, default):
        """Retrieve the value of a double-valued header variable."""

        self._checkOpen ()
        return _miriad_c.rdhdd (self.tno, keyword, float (default))

    def getHeaderComplex (self, keyword, default):
        """Retrieve the value of a complex-valued header variable."""

        self._checkOpen ()
        return _miriad_c.rdhdc (self.tno, keyword, complex (default))

    def getHeaderString (self, keyword, default):
        """Retrieve the value of a string-valued header variable.
        Maximum value length is 512."""

        self._checkOpen ()
        return _miriad_c.rdhda (self.tno, keyword, str (default))

    def writeHeaderFloat (self, keyword, value):
        """Write a float-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhdr (self.tno, keyword, float (value))

    def writeHeaderInt (self, keyword, value):
        """Write an int-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhdi (self.tno, keyword, int (value))

    def writeHeaderLong (self, keyword, value):
        """Write a long-int-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhdl (self.tno, keyword, int (value))

    def writeHeaderDouble (self, keyword, value):
        """Write a double-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhdd (self.tno, keyword, float (value))

    def writeHeaderComplex (self, keyword, value):
        """Write a complex-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhdc (self.tno, keyword, complex (value))

    def writeHeaderString (self, keyword, value):
        """Write a string-valued header variable."""
        self._checkOpen ()
        _miriad_c.wrhda (self.tno, keyword, str (value))

    def copyHeader (self, dest, keyword):
        """Copy a header variable from this data-set to another."""

        self._checkOpen ()
        _miriad_c.hdcopy (self.tno, dest.tno, keyword)

    # skip hdprsnt: same thing as hexists

    def getHeaderInfo (self, keyword):
        """Return the characteristics of the header variable. Returns:
        (desc, type, n), where 'desc' describes the item or gives its value
        if it can be expressed compactly; 'type' is one of 'nonexistant',
        'integer*2', 'integer*8', 'integer', 'real', 'double', 'complex',
        'character', 'text', 'binary', or 'unknown'; and 'n' is the number
        of elements in the item. If 'n' is 1, then 'desc' encodes the item's
        value.
        """

        self._checkOpen ()
        (desc, type, n) = _miriad_c.hdprobe (self.tno, keyword)

        if n == 0: raise MiriadError ('Error probing header ' + keyword)

        return (desc, type, n)

    # Elaborations on the basic MIRIAD functions to make it easier
    # to read write simple header arrays

    def getArrayHeader (self, keyword):
        desc, type, n = self.getHeaderInfo (keyword)

        if type == 'nonexistant':
            raise MiriadError ('Trying to read nonexistant header ' + keyword)
        elif type == 'unknown':
            raise MiriadError ('Cannot determine type of header ' + keyword)
        elif type == 'character':
            # Already gets read into desc for us.
            return desc
        elif type == 'integer*2':
            func = 'readShorts'
            dtype = N.int16
        elif type == 'integer*8':
            func = 'readLongs'
            dtype = N.int8
        elif type == 'integer':
            func = 'readInts'
            dtype = N.int32
        elif type == 'real':
            func = 'readFloats'
            dtype = N.float32
        elif type == 'double':
            func = 'readDoubles'
            dtype = N.float64
        elif type == 'complex':
            func = 'readComplex'
            dtype = N.complex64
        elif type == 'text' or type == 'binary':
            func = 'readBytes'
            dtype = N.uint8
        else:
            raise MiriadError ('Unhandled type %s for header %s' % (type, keyword))

        # Mistakes in hdprobe() / no offset
        if type == 'text':
            n -= 4
            offset = 0
        elif type == 'binary':
            n -= 4
            offset = 4
        else:
            offset = max (4, dtype ().itemsize)

        data = N.empty (n, dtype=dtype)
        item = self.getItem (keyword, 'r')

        getattr (item, func) (data, offset)
        item.close ()

        if type == 'text':
            # There has to be a better way to do this ...
            data = ''.join (chr (x) for x in data)

        return data


    def _writeArrayHeader (self, keyword, value, wsingle, wmultiname, dtype):
        value = N.asarray (value, dtype=dtype)
        offset = max (4, dtype ().itemsize)

        wsingle (keyword, 0)
        item = self.getItem (keyword, 'a')
        getattr (item, wmultiname) (value, offset)
        item.close ()


    def writeArrayHeaderInt (self, keyword, value):
        self._writeArrayHeader (keyword, value, self.writeHeaderInt,
                                 'writeInts', N.int32)


    def writeArrayHeaderLong (self, keyword, value):
        self._writeArrayHeader (keyword, value, self.writeHeaderLong,
                                 'writeLongs', N.int64)


    def writeArrayHeaderFloat (self, keyword, value):
        self._writeArrayHeader (keyword, value, self.writeHeaderFloat,
                                 'writeFloats', N.float32)


    def writeArrayHeaderDouble (self, keyword, value):
        self._writeArrayHeader (keyword, value, self.writeHeaderDouble,
                                 'writeDoubles', N.float64)


    def writeArrayHeaderComplex (self, keyword, value):
        self._writeArrayHeader (keyword, value, self.writeHeaderComplex,
                                 'writeComplex', N.complex64)


class DataItem (object):
    """An item contained within a Miriad dataset."""

    itno = None

    def __init__ (self, dataset, keyword, mode):
        self.dataset = dataset
        self.refobj = dataset.refobj
        self.name = keyword

        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        elif mode == 's': modestr = 'scratch'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.itno = _miriad_c.haccess (dataset.tno, keyword, modestr)

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

    def seek (self, offset):
        """Seek to the specified position within this data item."""

        self._checkOpen ()
        _miriad_c.hseek (self.itno, int (offset))

    def getPosition (self):
        """Retrieve the current position within this data item."""

        self._checkOpen ()
        return _miriad_c.htell (self.itno)

    def seqReadString (self):
        """Read until newline from the current position within this
        data item. Maximum string length of 512."""

        self._checkOpen ()
        return _miriad_c.hreada (self.itno)

    def seqWriteString (self, line, length=None):
        """Write a textual string into the data item, terminating
        the string with a newline. If desired, only a subset of the
        string can be written out; the default is to write the
        entire string."""

        if length is None: length = len (line)
        self._checkOpen ()
        _miriad_c.hwritea (self.itno, str (line), length)

    # Reading buffers

    def readBytes (self, buf, offset, length=None):
        """Read an array of bytes from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.byte)
        if length is None: length = buf.size
        _miriad_c.hreadb (self.itno, buf, offset, length)

    def readInts (self, buf, offset, length=None):
        """Read an array of 32-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int32)
        if length is None: length = buf.size
        _miriad_c.hreadi (self.itno, buf, offset, length)

    def readShorts (self, buf, offset, length=None):
        """Read an array of 16-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int16)
        if length is None: length = buf.size
        _miriad_c.hreadj (self.itno, buf, offset, length)

    def readLongs (self, buf, offset, length=None):
        """Read an array of 64-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int64)
        if length is None: length = buf.size
        _miriad_c.hreadl (self.itno, buf, offset, length)

    def readFloats (self, buf, offset, length=None):
        """Read an array of floats from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.float32)
        if length is None: length = buf.size
        _miriad_c.hreadr (self.itno, buf, offset, length)

    def readDoubles (self, buf, offset, length=None):
        """Read an array of doubles from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.double)
        if length is None: length = buf.size
        _miriad_c.hreadd (self.itno, buf, offset, length)

    def readComplex (self, buf, offset, length=None):
        """Read an array of complexes from the given location in the data
        item. The default read length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.complex64)
        if length is None: length = buf.size
        _miriad_c.hreadc (self.itno, buf, offset, length)

    # Writing

    def writeBytes (self, buf, offset, length=None):
        """Write an array of bytes to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.byte)
        if length is None: length = buf.size
        _miriad_c.hwriteb (self.itno, buf, offset, length)

    def writeInts (self, buf, offset, length=None):
        """Write an array of integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int32)
        if length is None: length = buf.size
        _miriad_c.hwritei (self.itno, buf, offset, length)

    def writeShorts (self, buf, offset, length=None):
        """Write an array of 16-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int16)
        if length is None: length = buf.size
        _miriad_c.hwritej (self.itno, buf, offset, length)

    def writeLongs (self, buf, offset, length=None):
        """Write an array of 64-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.int64)
        if length is None: length = buf.size
        _miriad_c.hwritel (self.itno, buf, offset, length)

    def writeFloats (self, buf, offset, length=None):
        """Write an array of floats to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.float32)
        if length is None: length = buf.size
        _miriad_c.hwriter (self.itno, buf, offset, length)

    def writeDoubles (self, buf, offset, length=None):
        """Write an array of doubles to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.double)
        if length is None: length = buf.size
        _miriad_c.hwrited (self.itno, buf, offset, length)

    def writeComplex (self, buf, offset, length=None):
        """Write an array of complexes to the given location in the data
        item. The default write length is the size of the array."""

        self._checkOpen ()
        buf = N.asarray (buf, dtype=N.complex64)
        if length is None: length = buf.size
        _miriad_c.hwritec (self.itno, buf, offset, length)

__all__ += ['DataSet', 'DataItem']

class UserDataSet (DataSet):
    def __init__ (self, refobj, create=False):
        if create: mode = 'new'
        else: mode = 'old'

        self.tno = _miriad_c.hopen (refobj.base, mode)
        self.refobj = refobj
        self.name = refobj.base

    def _close (self):
        _miriad_c.hclose (self.tno)

__all__ += ['UserDataSet']

class UVDataSet (DataSet):
    def __init__ (self, refobj, mode):
        # Technically, 'old' mode is read-only with regard to the
        # UV data, but you can still write non-UV header variables.
        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        elif mode == 'a': modestr = 'append'
        else: raise ValueError ('Unsupported mode "%s"; "rw", "c", and "a" are allowed' % mode)

        self.tno = _miriad_c.uvopen (refobj.base, modestr)
        self.refobj = refobj
        self.name = refobj.base

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

    def setSelectAmplitude (self, selamp):
        """Specify whether selection based on amplitude should be
        performed."""

        if selamp: val = 1
        else: val = 0

        self._uvset ("selection", "amplitude", val, 0., 0., 0.,)

    def setSelectWindow (self, selwin):
        """Specify whether selection based on window should be
        performed."""

        if selwin: val = 1
        else: val = 0

        self._uvset ("selection", "window", val, 0., 0., 0.,)

    def setPlanetParams (self, major, minor, angle):
        """Set the reference parameters for planet scaling and
        rotation."""

        self._uvset ("planet", "", 0, major, minor, angle)

    def setWavelengthMode (self, wlmode):
        """Specify that UV coordinates should be returned in units
        of wavelength. Otherwise, they are returned in nanoseconds."""

        if wlmode:
            self._uvset ("coord", "wavelength", 0, 0., 0., 0.)
        else:
            self._uvset ("coord", "nanosec", 0, 0., 0., 0.)

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

    def getVarFirstString (self, varname, dflt):
        """Retrieve the first value of a string-valued UV
        variable with a default if the variable is not present.
        Maximum length of 512 characters."""

        self._checkOpen ()
        return _miriad_c.uvrdvra (self.tno, varname, dflt)

    def getVarFirstInt (self, varname, dflt):
        """Retrieve the first value of an int-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return _miriad_c.uvrdvri (self.tno, varname, dflt)

    def getVarFirstFloat (self, varname, dflt):
        """Retrieve the first value of a float-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return _miriad_c.uvrdvrr (self.tno, varname, dflt)

    def getVarFirstDouble (self, varname, dflt):
        """Retrieve the first value of a double-valued UV
        variable with a default if the variable is not present."""

        self._checkOpen ()
        return _miriad_c.uvrdvrd (self.tno, varname, dflt)

    def getVarFirstComplex (self, varname, dflt):
        """Retrieve the first value of a complex-valued UV
        variable with a default if the variable is not present."""

        dflt = complex (dflt)
        self._checkOpen ()
        retval = _miriad_c.uvrdvrd (self.tno, varname, (dflt.real, dflt.imag))
        return complex (retval[0], retval[1])

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
        self.dataset = owner
        self.refobj = owner.refobj
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

    def __init__ (self, dataset, keyword, mode):
        self.dataset = dataset
        self.refobj = dataset.refobj
        self.name = keyword
        self.handle = None

        if mode == 'rw': modestr = 'old'
        elif mode == 'c': modestr = 'new'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.handle = _miriad_c.mkopen (dataset.tno, keyword, modestr)


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


class XYDataSet (DataSet):
    def __init__ (self, refobj, mode, naxis, axes=None):
        if mode == 'rw':
            modestr = 'old'
        elif mode == 'c':
            modestr = 'new'
        else:
            raise ValueError ('unsupported mode "%s"; expect "rw" or "c"' % mode)

        if axes is None:
            if mode == 'c':
                raise ValueError ('axes must be specified when creating a new XY dataset')
            axes = N.zeros (naxis, dtype=N.int)

        self.axes = axes
        self.name = str (refobj)
        self.tno = _miriad_c.xyopen (str (refobj), modestr, naxis, axes)
        self._databuf = N.empty (axes[0], dtype=N.float32)
        self._flagbuf = N.empty (axes[0], dtype=N.int)
        self._npmaskbuf = N.empty (axes[0], dtype=N.bool)
        self._masked = N.ma.masked_array (self._databuf, self._npmaskbuf,
                                          copy=False)


    def _close (self):
        _miriad_c.xyclose (self.tno)


    def flush (self):
        self._checkOpen ()
        _miriad_c.xyflush (self.tno)
        return self


    def setPlane (self, axes=[]):
        self._checkOpen ()
        axes = N.asarray (axes).astype (N.int)
        _miriad_c.xysetpl (self.tno, axes.size, axes)
        return self


    def readRow (self, rownum):
        self._checkOpen ()
        _miriad_c.xyread (self.tno, rownum + 1, self._databuf)
        _miriad_c.xyflgrd (self.tno, rownum + 1, self._flagbuf)
        N.logical_not (self._flagbuf, self._npmaskbuf)
        return self._masked


    def readRows (self):
        self._checkOpen ()

        for i in xrange (1, self.axes[1] + 1):
            _miriad_c.xyread (self.tno, i, self._databuf)
            _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
            N.logical_not (self._flagbuf, self._npmaskbuf)
            yield self._masked


    def readPlane (self, axes=[]):
        """note pixel 0, 0 is bottom left corner, not top left"""
        self._checkOpen ()
        self.setPlane (axes)

        data = N.empty ((self.axes[1], self.axes[0]), dtype=N.float32)
        mask = N.empty ((self.axes[1], self.axes[0]), dtype=N.bool)
        masked = N.ma.masked_array (data, mask, copy=False)

        for i in xrange (1, self.axes[1] + 1):
            _miriad_c.xyread (self.tno, i, data[i-1])
            _miriad_c.xyflgrd (self.tno, i, self._flagbuf)
            N.logical_not (self._flagbuf, mask[i-1])

        return masked


    def writeRow (self, rownum, maskeddata):
        maskeddata = N.ma.atleast_1d (maskeddata)

        if maskeddata.ndim != 1:
            raise ValueError ('maskeddata must be 1d')
        if maskeddata.size != self.axes[0]:
            raise ValueError ('maskeddata must be of size %d' % self.axes[0])

        self._checkOpen ()
        N.logical_not (maskeddata.mask, self._flagbuf)
        _miriad_c.xywrite (self.tno, rownum + 1, self._databuf)
        _miriad_c.xyflgwr (self.tno, rownum + 1, self._flagbuf)
        return self


    def writePlane (self, maskeddata, axes=[]):
        maskeddata = N.ma.atleast_2d (maskeddata)

        if maskeddata.ndim != 2:
            raise ValueError ('maskeddata must be 2d')
        if maskeddata.shape != (self.axes[1], self.axes[0]):
            raise ValueError ('maskeddata must be of shape (%d, %d)' %
                              (self.axes[1], self.axes[0]))

        self._checkOpen ()
        self.setPlane (axes)

        for i in xrange (1, self.axes[1] + 1):
            N.logical_not (maskeddata.mask[i-1], self._flagbuf)
            _miriad_c.xywrite (self.tno, i, maskeddata[i-1])
            _miriad_c.xyflgwr (self.tno, i, self._flagbuf)

        return self


__all__ += ['XYDataSet']
