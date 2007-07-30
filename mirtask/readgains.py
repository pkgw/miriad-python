"""A module that provides an object that reads a UV data set's
gains table conveniently.
"""

import lowlevel as ll
import numpy as N
from mirtask import MiriadError

__all__ = [ 'GainsReader' ]

class GainsReader (object):
    """Read in gains from a Miriad data set. Code based on gplist.for."""
    
    def __init__ (self, dset):
        self.dset = dset

    nants = None
    ngains = None
    nfeeds = None
    ntau = None
    nsols = None
    
    def prep (self):
        """Read in header information, preparing to read the gains
        information itself. Sets the following attributes on the object:
        ngains, nfeeds, ntau, nants, nsols."""

        if not dset.hasItem ('gains'):
            raise ValueError ('Input "%s" doesn\'t have a gains table!' % dset.name)

        self.ngains = ngains = self.dset.getHeaderInt ('ngains', 0)
        self.nfeeds = nfeeds = self.dset.getHeaderInt ('nfeeds', 1)
        self.ntau = ntau = self.dset.getHeaderInt ('ntau', 0)

        if nfeeds < 1 or nfeeds > 2 or \
           ngains % (nfeeds + ntau) != 0 or \
           ntau > 1 or ntau < 0:
            raise RuntimeError ('Bad number of gains (%d), feeds (%d), or taus (%d) in UV dataset' % \
                                (ngains, nfeeds, ntau))

        self.nants = nants = ngains / (nfeeds + ntau)

        self.gitem = self.dset.getItem ('gains', 'r')
        self.nsols = nsols = (self.gitem.getSize () - 8) / (8 * ngains + 8)
        
    def readAll (self):
        """Read in all of the gain and time information in at
        once. Returns (time, gains), where time is an ndarray of nsols
        doubles, and gains is an ndarray of (nsols, ngains) complexes."""

        if self.nsols is None: raise RuntimeError ('Need to call prep() first!')
        
        nsols, ngains = self.nsols, self.ngains
        
        offset = 8
        pnt = 0
        time = N.ndarray (nsols, dtype=N.double)
        gains = N.ndarray ((nsols, ngains), dtype=N.complex64)
        
        for i in xrange (0, nsols):
            self.gitem.readDoubles (time[i:], offset, 8)
            offset += 8
            self.gitem.readComplex (gains[pnt,:], offset, 8 * ngains)
            offset += 8 * ngains
            pnt += 1

        del self.gitem
        return (time, gains)

    def readSeq (self):
        """Generate a sequence of (time, gains), where time is a double and
        gains is an ndarray of ngains complexes."""
        
        if self.nsols is None: raise RuntimeError ('Need to call prep() first!')
        
        nsols, ngains = self.nsols, self.ngains
        
        offset = 8
        time = N.ndarray (1, dtype=N.double)
        gains = N.ndarray (ngains, dtype=N.complex64)
        
        for i in xrange (0, nsols):
            self.gitem.readDoubles (time, offset, 8)
            offset += 8
            self.gitem.readComplex (gains, offset, 8 * ngains)
            offset += 8 * ngains

            yield (time[0], gains)

        del self.gitem
