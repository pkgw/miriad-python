'''numutils - utility classes for working with Numpy arrays'''

# Copyright 2009, 2010 Peter Williams
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

__all__ = []

class ArrayGrower (object):
    __slots__ = ['dtype', 'ncols', 'chunkSize', '_nextIdx', '_arr']
    
    def __init__ (self, ncols, dtype=N.float, chunkSize=128):
        self.dtype = dtype
        self.ncols = ncols
        self.chunkSize = chunkSize
        self.clear ()

    
    def clear (self):
        self._nextIdx = 0
        self._arr = None


    def addLine (self, line):
        line = N.asarray (line, dtype=self.dtype)
        assert (line.size == self.ncols)
        
        if self._arr is None:
            self._arr = N.ndarray ((self.chunkSize, self.ncols), dtype=self.dtype)
        elif self._arr.shape[0] <= self._nextIdx:
            self._arr.resize ((self._arr.shape[0] + self.chunkSize, self.ncols))

        self._arr[self._nextIdx] = line
        self._nextIdx += 1


    def add (self, *args):
        self.addLine (args)


    def __len__ (self): return self._nextIdx


    def finish (self, trans=False):
        if self._arr is None:
            ret = N.ndarray ((0, self.ncols), dtype=self.dtype)
        else:
            self._arr.resize ((self._nextIdx, self.ncols))
            ret = self._arr

        self.clear ()

        if trans: ret = ret.T

        return ret


__all__.append ('ArrayGrower')

class VectorGrower (object):
    __slots__ = ['dtype', 'chunkSize', '_nextIdx', '_vec']
    
    def __init__ (self, dtype=N.float, chunkSize=128):
        self.dtype = dtype
        self.chunkSize = chunkSize
        self.clear ()


    def clear (self):
        self._nextIdx = 0
        self._vec = None


    def add (self, val):
        if self._vec is None:
            self._vec = N.ndarray ((self.chunkSize, ), dtype=self.dtype)
        elif self._vec.size <= self._nextIdx:
            self._vec.resize ((self._vec.size + self.chunkSize, ))

        self._vec[self._nextIdx] = val
        self._nextIdx += 1


    def __len__ (self): return self._nextIdx


    def finish (self):
        if self._vec is None:
            ret = N.ndarray ((0, ), dtype=self.dtype)
        else:
            self._vec.resize ((self._nextIdx, ))
            ret = self._vec

        self.clear ()

        return ret


__all__.append ('VectorGrower')


def growarr (itre, dtype=N.float, chunkSize=128):
    g = None

    for item in itre:
        item = N.asarray (item)

        if g is None:
            isVec = item.shape == ()
            g = ArrayGrower (item.size, dtype=dtype, chunkSize=chunkSize)

        g.addLine (item)

    if g is None:
        return N.empty ((0,0), dtype=dtype)

    v = g.finish ()

    if isVec: v = v.squeeze ()

    return v


__all__.append ('growarr')


class StatsAccumulator (object):
    # FIXME: I worry about loss of precision when n gets very
    # large: we'll be adding a tiny number to a large number.
    # We could periodically rebalance or something. I'll think
    # about it more if it's ever actually a problem.

    __slots__ = ['xtot', 'xsqtot', 'n']
    
    def __init__ (self):
        self.clear ()

    def clear (self):
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

class WeightAccumulator (object):
    """Standard stastical weighting is wt_i = sigma_i**-2
We don't need the 'n' variable to do any stats, but it can
be nice to have that information.
"""

    __slots__ = ['xwtot', 'wtot', 'n']

    def __init__ (self):
        self.clear ()

    def clear (self):
        self.xwtot = 0.
        self.wtot = 0.
        self.n = 0

    def add (self, x, wt):
        self.xwtot += x * wt
        self.wtot += wt
        self.n += 1

    def num (self): return self.n

    def wtavg (self): return self.xwtot / self.wtot

    def var (self):
        """Assumes wt_i = sigma_i**-2"""
        return 1. / self.wtot

    def std (self):
        return N.sqrt (self.var ())

__all__.append ('WeightAccumulator')

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
