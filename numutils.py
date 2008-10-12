"""Some useful classes for numerical work."""

import numpy as N

__all__ = []

class GrowingArray (object):
    __slots__ = ['dtype', 'ncols', 'chunkSize', 'nextIdx', 'arr']
    
    def __init__ (self, dtype, ncols, chunkSize=128):
        self.dtype = dtype
        self.ncols = ncols
        self.chunkSize = chunkSize
        
        self.nextIdx = 0
        self.arr = None

    def addLine (self, line):
        assert (line.size == self.ncols)
        
        if self.arr is None:
            self.arr = N.ndarray ((self.chunkSize, self.ncols), dtype=self.dtype)
        elif self.arr.shape[0] <= self.nextIdx:
            newchk = N.ndarray ((self.chunkSize, self.ncols), dtype=self.dtype)
            self.arr = N.concatenate ((self.arr, newchk))

        self.arr[self.nextIdx] = line
        self.nextIdx += 1

    def add (self, *args):
        line = N.asarray (args, dtype=self.dtype)
        self.addLine (line)

    def doneAdding (self):
        self.arr = self.arr[0:self.nextIdx]
        del self.nextIdx

    def get (self, idx):
        return self.arr[idx]

    def col (self, colnum):
        return self.arr[:,colnum]

    def shuffle (self, idxs):
        self.arr = self.arr[idxs]
    
    def __len__ (self):
        return self.arr.shape[0]
    
    def save (self, fh):
        self.arr.dump (fh)

    def load (self, fh):
        self.arr = N.load (fh)

__all__.append ('GrowingArray')

class GrowingVector (object):
    __slots__ = ['dtype', 'chunkSize', 'nextIdx', 'arr']
    
    def __init__ (self, dtype=N.float, chunkSize=128):
        self.dtype = dtype
        self.chunkSize = chunkSize
        
        self.nextIdx = 0
        self.arr = None

    def add (self, val):
        if self.arr is None:
            self.arr = N.ndarray ((self.chunkSize, ), dtype=self.dtype)
        elif self.arr.size <= self.nextIdx:
            self.arr.resize ((self.arr.size + self.chunkSize, ))

        self.arr[self.nextIdx] = val
        self.nextIdx += 1

    def doneAdding (self):
        self.arr = self.arr[0:self.nextIdx]
        del self.nextIdx

    def __getslice__ (self, *args): return self.arr.__getslice__ (*args)
    def __setslice__ (self, *args): return self.arr.__setslice__ (*args)
    def __getitem__ (self, *args): return self.arr.__getitem__ (*args)
    def __setitem__ (self, *args): return self.arr.__setitem__ (*args)

    def shuffle (self, idxs):
        self.arr = self.arr[idxs]
    
    def __len__ (self):
        return self.arr.size
    
    def save (self, fh):
        self.arr.dump (fh)

    def load (self, fh):
        self.arr = N.load (fh)

__all__.append ('GrowingVector')

class StatsAccumulator (object):
    # FIXME: I worry about loss of precision when n gets very
    # large: we'll be adding a tiny number to a large number.
    # We could periodically rebalance or something. I'll think
    # about it more if it's ever actually a problem.

    __slots__ = ['xtot', 'xsqtot', 'n']
    
    def __init__ (self):
        self.xtot = 0.
        self.xsqtot = 0.
        self.n = 0

    def add (self, x):
        self.xtot += x
        self.xsqtot += x**2
        self.n += 1

    def num (self): return self.n
    
    def mean (self): return self.xtot / self.n

    def rms (self): return N.sqrt (self.xsqtot / self.n)
    
    def std (self):
        return N.sqrt (self.var ())

    def var (self):
        return self.xsqtot/self.n - (self.xtot/self.n)**2

__all__.append ('StatsAccumulator')

class AccDict (dict):
    """An accumulating dictionary."""

    __slots__ = ['_create', '_accum']
    
    def __init__ (self, create, accum):
        self._create = create
        self._accum = accum
        
    def accum (self, key, val):
        entry = self.get (key)

        if entry is None:
            entry = self._create ()
            self[key] = entry
            
        self._accum (entry, val)

__all__.append ('AccDict')

class RedDict (dict):
    """A reducing dictionary."""

    __slots__ = ['_nothingEquiv', '_reduce']
                 
    def __init__ (self, nothingEquiv, reducefn):
        self._nothingEquiv = nothingEquiv
        self._reduce = reducefn
        
    def reduce (self, key, val):
        prev = self.get (key)

        if prev is None: prev = self._nothingEquiv

        self[key] = self._reduce (prev, val)

__all__.append ('RedDict')

