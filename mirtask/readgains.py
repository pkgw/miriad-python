"""A module that provides an object that reads a UV data set's
gains table conveniently.
"""

import lowlevel as ll
import numpy as N
from mirtask import MiriadError

__all__ = [ 'GainsReader' ]

class GainsReader (object):
    def __init__ (self, dfile):
        self.dfile = dfile

    def readAll (self):
        """Return arrays of time values and gains values. Code based on
        gplist.for."""

        tno = self.dfile.tno
        
        ngains = ll.rdhdi (tno, 'ngains', 0)
        nfeeds = ll.rdhdi (tno, 'nfeeds', 1)
        ntau = ll.rdhdi (tno, 'ntau', 0)

        if nfeeds < 1 or nfeeds > 2 or \
           ngains % (nfeeds + ntau) != 0 or \
           ntau > 1 or ntau < 0:
            raise MiriadError ('Bad number of gains (%d), feeds (%d), or taus (%d) in UV dataset' % \
                               (ngains, nfeeds, ntau))

        nants = ngains / (nfeeds + ntau)

        tgains = ll.haccess (tno, 'gains', 'read')
        nsols = (ll.hsize (tgains) - 8) / (8 * ngains + 8)

        offset = 8
        pnt = 0
        
        time = N.ndarray (nsols, dtype=N.double)
        gains = N.nadarray (nsols * ngains, dtype=N.complex64)
        
        for i in xrange (0, nsols):
            ll.hreadd (tgains, time[i:], offset, 8)
            offset += 8
            ll.hreadc (tgains, gains[pnt:], offset, 8 * ngains)
            offset += 8 * ngains
            pnt += ngains

        hdaccess (tgains)

        return (time, gains)

    def readSeq (self):
        """Yield a sequence of (time, gains) arrays. Code based on
        gplist.for."""
        
        ngains = ll.rdhdi (tno, 'ngains', 0)
        nfeeds = ll.rdhdi (tno, 'nfeeds', 1)
        ntau = ll.rdhdi (tno, 'ntau', 0)

        if nfeeds < 1 or nfeeds > 2 or \
           ngains % (nfeeds + ntau) != 0 or \
           ntau > 1 or ntau < 0:
            raise MiriadError ('Bad number of gains (%d), feeds (%d), or taus (%d) in UV dataset' % \
                               (ngains, nfeeds, ntau))

        nants = ngains / (nfeeds + ntau)

        tgains = ll.haccess (tno, 'gains', 'read')
        nsols = (ll.hsize (tgains) - 8) / (8 * ngains + 8)

        offset = 8
        pnt = 0
        
        time = N.ndarray (1, dtype=N.double)
        gains = N.nadarray (ngains, dtype=N.complex64)
        
        for i in xrange (0, nsols):
            ll.hreadd (tgains, time, offset, 8)
            offset += 8
            ll.hreadc (tgains, gains, offset, 8 * ngains)
            offset += 8 * ngains
            pnt += ngains

            yield (time[0], gains)

        hdaccess (tgains)
