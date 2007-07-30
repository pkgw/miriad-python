"""A module that provides an object that reads a UV data set's
gains table conveniently.
"""

import lowlevel as ll
import numpy as N
from mirtask import MiriadError

__all__ = []

# Some utility functions

def initKeys ():
    """Initialize the MIRIAD keys system based on sys.argv. Can be
    called multiple times, to iterate through the keys repeatedly."""

    from sys import argv
    ll.keyini (argv)

__all__ += ['initKeys']

# Very simple wrapper classes. Shouldn't necessarily be used,
# given that there are standard APIs like uvdat*

class DataSet (object):
    """A generic Miriad data-set."""
    
    def __init__ (self, fname, create=False):
        if create: mode = 'new'
        else: mode = 'old'

        self.name = fname
        self.tno = ll.hopen (fname, mode)

    def __del__ (self):
        # tno can be None if we got an exception inside hopen,
        # or if we are deleteAll'ed

        if ll is None or not hasattr (self, 'tno'): return

        if self._histOpen: self.closeHistory ()
        
        ll.hclose (self.tno)

    def __repr__ (self):
        return 'DataSet (%s)' % (repr (self.name))

    def __str__ (self):
        return '<DataSet \"%s\" handle %d>' % (self.name, self.tno)

    def flush (self):
        """Write any changed items in the data set out to disk."""
        
        ll.hflush (self.tno)

    def deleteAll (self):
        """Completely delete this data set. After calling this function,
        this object cannot be used."""
        
        ll.hrm (self.tno)
        delattr (self, 'tno') # make any further use of this item fail
        
    def deleteItem (self, name):
        """Delete an item from this data-set."""

        ll.hdelete (self.tno, name)
    
    MODE_UNKNOWN, MODE_RD, MODE_RDWR = range (0, 3)

    def getMode (self):
        """Return the access mode of this data-set: readonly or
        read-write. See the MODE_X fields of this class for possible
        return values."""
        
        mode = ll.hmode (self.tno)

        if mode == '': return self.MODE_UNKNOWN
        elif mode == 'r': return self.MODE_RD
        elif mode == 'rw': return self.MODE_RDWR
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)
        
        raise MiriadError ('Unknown hio mode type: ' + mode)
    
    # Data items

    def hasItem (self, name):
        """Return whether this data-set contains an item with the given name."""
        
        return ll.hexists (self.tno, name)

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

        del ilist

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

        ll.hisopen (self.tno, modestr)
        self._histOpen = True

    def writeHistory (self, text):
        """Write text into this data set's history file."""
        
        ll.hiswrite (self.tno, text)

    def closeHistory (self):
        """Close this data set's history item."""

        ll.hisclose (self.tno)
        self._histOpen = False

    # Header variables

    def getHeaderFloat (self, keyword, default):
        """Retrieve the value of a float-valued header variable."""

        return ll.rdhdr (self.tno, keyword, float (default))

    def getHeaderInt (self, keyword, default):
        """Retrieve the value of an int-valued header variable."""

        return ll.rdhdi (self.tno, keyword, int (default))

    def getHeaderBool (self, keyword, default):
        """Retrieve the value of a bool-valued header variable."""

        return bool (ll.rdhdl (self.tno, keyword, int (default)))

    def getHeaderDouble (self, keyword, default):
        """Retrieve the value of a double-valued header variable."""

        return ll.rdhdd (self.tno, keyword, float (default))

    def getHeaderComplex (self, keyword, default):
        """Retrieve the value of a complex-valued header variable."""

        dc = complex (default)
        out = ll.rdhdc (self.tno, keyword, (dc.real, dc.imag))
        return complex (out[0], out[1])
    
    def getHeaderString (self, keyword, default):
        """Retrieve the value of a string-valued header variable.
        Maximum value length is 512."""

        return ll.rdhda (self.tno, keyword, str (default))

    def copyHeader (self, dest, keyword):
        """Copy a header variable from this data-set to another."""

        ll.hdcopy (self.tno, dest.tno, keyword)

    # skip hdprsnt: same thing as hexists
    
    def getHeaderInfo (self, keyword):
        """Return the characteristics of the header variable. Returns:
        (desc, type, n), where 'desc' describes the item or gives its value
        if it can be expressed compactly; 'type' is one of 'nonexistant',
        'integer*2', 'integer*8', 'integer', 'real', 'double', 'complex',
        'character', 'text', or 'binary'; and 'n' is the number of elements
        in the item. If 'n' is 1, then 'desc' encodes the item's value.
        """

        (desc, type, n) = ll.hdprobe (self.tno, keyword)

        if n == 0: raise MiriadError ('Error probing header ' + keyword)

        return (desc, type, n)

class DataItem (object):
    """An item contained within a Miriad dataset."""
    
    def __init__ (self, dataset, keyword, mode):
        self.dataset = dataset
        self.name = keyword

        if mode == 'r': modestr = 'read'
        elif mode == 'w': modestr = 'write'
        elif mode == 'a': modestr = 'append'
        elif mode == 's': modestr = 'scratch'
        else: raise ValueError ('Unexpected value for "mode" argument: ' + mode)

        self.itno = ll.haccess (dataset.tno, keyword, modestr)

    def __del__ (self):
        # itno can be None if we got an exception inside hopen.

        if ll is None or not hasattr (self, 'itno'): return

        ll.hdaccess (self.itno)

    def getSize (self):
        """Return the size of this data item."""

        return ll.hsize (self.itno)

    def seek (self, offset):
        """Seek to the specified position within this data item."""

        ll.hseek (self.itno, int (offset))

    def getPosition (self):
        """Retrieve the current position within this data item."""

        return ll.htell (self.itno)

    def seqReadString (self):
        """Read until newline from the current position within this
        data item. Maximum string length of 512."""

        return ll.hreada (self.itno)

    def seqWriteString (self, line, length=None):
        """Write a textual string into the data item, terminating
        the string with a newline. If desired, only a subset of the
        string can be written out; the default is to write the
        entire string."""

        if length is None: length = len (line)
        ll.hwritea (self.itno, str (line), length)

    # Reading buffers
    
    def readBytes (self, buf, offset, length=None):
        """Read an array of bytes from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadb (self.itno, buf, offset, length)

    def readInts (self, buf, offset, length=None):
        """Read an array of integers from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadi (self.itno, buf, offset, length)

    def readShorts (self, buf, offset, length=None):
        """Read an array of 16-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadj (self.itno, buf, offset, length)

    def readLongs (self, buf, offset, length=None):
        """Read an array of 64-bit integers from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadl (self.itno, buf, offset, length)

    def readFloats (self, buf, offset, length=None):
        """Read an array of floats from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadr (self.itno, buf, offset, length)

    def readDoubles (self, buf, offset, length=None):
        """Read an array of doubles from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadd (self.itno, buf, offset, length)

    def readComplex (self, buf, offset, length=None):
        """Read an array of complexes from the given location in the data
        item. The default read length is the size of the array."""

        if length is None: length = darray.size
        ll.hreadc (self.itno, buf, offset, length)

    # Writing
    
    def writeBytes (self, buf, offset, length=None):
        """Write an array of bytes to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwriteb (self.itno, buf, offset, length)

    def writeInts (self, buf, offset, length=None):
        """Write an array of integers to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwritei (self.itno, buf, offset, length)

    def writeShorts (self, buf, offset, length=None):
        """Write an array of 16-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwritej (self.itno, buf, offset, length)

    def writeLongs (self, buf, offset, length=None):
        """Write an array of 64-bit integers to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwritel (self.itno, buf, offset, length)

    def writeFloats (self, buf, offset, length=None):
        """Write an array of floats to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwriter (self.itno, buf, offset, length)

    def writeDoubles (self, buf, offset, length=None):
        """Write an array of doubles to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwrited (self.itno, buf, offset, length)

    def writeComplex (self, buf, offset, length=None):
        """Write an array of complexes to the given location in the data
        item. The default write length is the size of the array."""

        if length is None: length = darray.size
        ll.hwritec (self.itno, buf, offset, length)

__all__ += ['DataSet', 'DataItem']
