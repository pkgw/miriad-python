'''mirtask.readgains - convenient reading of the gains tables in UV datasets'''

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
from mirtask import MiriadError

__all__ = ['GainsReader', 'readBandpass' ]

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

        if not self.dset.hasItem ('gains'):
            raise ValueError ('Input "%s" doesn\'t have a gains table!' % self.dset.name)

        self.ngains = ngains = self.dset.getScalarHeader ('ngains', 0)
        self.nfeeds = nfeeds = self.dset.getScalarHeader ('nfeeds', 1)
        self.ntau = ntau = self.dset.getScalarHeader ('ntau', 0)

        if nfeeds < 1 or nfeeds > 2 or \
           ngains % (nfeeds + ntau) != 0 or \
           ntau > 1 or ntau < 0:
            raise RuntimeError ('Bad number of gains (%d), feeds (%d), or taus (%d) in UV dataset' % \
                                (ngains, nfeeds, ntau))

        self.nants = ngains / (nfeeds + ntau)
        self.gitem = self.dset.getItem ('gains', 'r')
        self.nsols = (self.gitem.getSize () - 8) / (8 * ngains + 8)
        
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
            self.gitem.readDoubles (time[i:], offset, 1)
            offset += 8
            self.gitem.readComplex (gains[pnt,:], offset, ngains)
            offset += 8 * ngains
            pnt += 1

        self.gitem.close ()
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
            self.gitem.readDoubles (time, offset, 1)
            offset += 8
            self.gitem.readComplex (gains, offset, ngains)
            offset += 8 * ngains

            yield (time[0], gains)

        self.gitem.close ()

def readBandpass (dset):
    """Read in the bandpass table from the given dataset.

    Parameter: dset, an open Miriad dataset

    Returns: (nschans, freqs, gains), where

    nschans - A vector of 'nspect' integers, where nspect is the number
              of spectral windows in this dataset. Each integer gives
              the number of channels occupied by the window.
    freqs   - A vector of 'nchan' doubles, giving the sky frequency
              associated with each channel. nchan is the total number
              of channels, equal to the sum of the elements of nschans.
    gains   - A 3-D array of shape (nants, nfeeds, nchan) giving the
              bandpass solution for each antenna and feed. nants is the
              number of antennas allowed in the dataset -- though not
              all antennas may be used (some may be flagged, etc.) nfeeds
              is the number of feeds on each antenna: expected to be 1
              or 2. nchan is as in freqs.
    """
    
    if not dset.hasItem ('bandpass'):
        raise ValueError ('Input "%s" doesn\'t have a gains table!' % dset.name)

    # Prep counts and check sanity
    
    ngains = dset.getScalarHeader ('ngains', 0)
    nfeeds = dset.getScalarHeader ('nfeeds', 1)
    ntau = dset.getScalarHeader ('ntau', 0)
    nchan0 = dset.getScalarHeader ('nchan0', 0)
    nspect0 = dset.getScalarHeader ('nspect0', 0)

    nants = ngains // (nfeeds + ntau)

    if nfeeds < 1:
        raise RuntimeError ('Bad number of feeds (%d) in UV dataset' % nfeeds)
    if ngains < 1 or ngains != nants * (nfeeds + ntau):
        raise RuntimeError ('Bad number of gains (%d; %d ants %d feeds %d taus) '
                            'in UV dataset' % (ngains, nants, nfeeds, ntaus))
    if nchan0 < 1:
        raise RuntimeError ('Bad number of spectral channels (%d) in UV dataset' % nchan0)
    if nspect0 < 1 or nspect0 > nchan0:
        raise RuntimeError ('Bad number of spectral windows (%d) in UV dataset' % nspect0)

    # Frequency table.

    hdfreq = dset.getItem ('freqs', 'r')
    freqs = N.ndarray (nchan0, dtype=N.double)
    
    n = 0
    ofs = 8
    nschans = N.ndarray (nspect0, dtype=N.int32)
    freqbuf = N.ndarray (2, dtype=N.double)

    for i in xrange (0, nspect0):
        hdfreq.readInts (nschans[i:], ofs, 1)
        ofs += 8
        hdfreq.readDoubles (freqbuf, ofs)
        ofs += 8 * 2

        # This could be more efficient, but it's not a huge deal.
        for j in xrange (0, nschans[i]):
            freqs[n] = freqbuf[0] + j * freqbuf[1]
            n += 1

    if nschans.sum () != nchan0:
        raise RuntimeError ('Disagreeing number of channels and spectral window widths '
                            'in UV dataset: sum(nschan) = %d, nchan0 = %d' % (nschans.sum (),
                                                                              nchan0))
    
    hdfreq.close ()

    # Bandpass table

    hdbpass = dset.getItem ('bandpass', 'r')
    gains = N.ndarray ((nants, nfeeds, nchan0), dtype=N.complex64)
    hdbpass.readComplex (gains, 8)
    hdbpass.close ()
    
    return nschans, freqs, gains
