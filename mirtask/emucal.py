"""mirtask.emucal - Emulate MIRIAD's calibration routines"""

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
from miriad import *
import readgains, util

__all__ = []

def applyGain (g, tau, data, flags, freqs=None, freq0=None):
    """Apply gain and delay factors to spectral data.

:arg g: the complex gain parameter
:type g: :class:`complex`
:arg tau: the complex delay parameter
:type tau: :class:`complex`
:arg data: an array of visibilities; modified in-place
:type data: 1D :class:`~numpy.ndarray` of complex
:arg flags: an array of flag values; modified in-place
:type flags: 1D :class:`~numpy.ndarray` of bool
:arg freqs: the center frequency for each visibility in GHZ
:type freqs: 1D :class:`~numpy.ndarray` of double
:arg freq0: the reference frequency for which the delays have been calculated
:type freq0: :class:`float`
:returns: *data*

Applies complex gain and delay factors to a spectrum. This
function is for demonstration purposes only, and the routines used
by MIRIAD should be preferred whenever possible.

The parameters *freqs* and *freq0* are only necessary if
*tau* is nonzero. If *tau* is nonzero and they are not provided
an :exception:`ValueError` will be raised.
"""
    if g is None:
        flags.fill (0)
        return

    data *= g

    # Copied from uvgnpsdl

    if tau is not None:
        if freqs is None:
            raise ValueError ('freqs')
        if freq0 is None:
            raise ValueError ('freq0')
        atten, theta = tau.real, tau.imag

        if theta != 0.:
            if atten != 0.:
                data *= (freqs / freq0).real ** atten
                data *= N.exp ((0+1j) * theta * (freq - freq0))
            else:
                data *= N.exp ((0+1j) * theta * (freq - freq0))
        elif atten != 0.:
            data *= (freqs / freq0).real ** atten

    return data


class GainsCalculator (object):
    nants = None
    nfeeds = None
    ntau = None

    _times = None
    _gains = None
    _tidx = None
    _solno = None
    _timetab = None
    _gflags = None
    
    def read (self, vis):
        vhnd = vis.open ('rw')
        self.interval = vhnd.getHeaderDouble ('interval', 0.)
        assert self.interval > 0. 
        gr = readgains.GainsReader (vhnd)
        gr.prep ()
        self.nants = gr.nants
        self.nfeeds = gr.nfeeds
        self.ntau = gr.ntau
        self.times, self.gains = gr.readAll ()
        vhnd.close ()

        self._tidx = N.asarray ([0, 1])
        self._solno = N.asarray ([-1, 0])
        self._timetab = N.empty (2, dtype=N.double)
        self._timetab[1] = self.times[0]
        self._timetab[0] = self._timetab[1] - 1e6 * self.interval
        self._gflags = (N.abs (self.gains) > 0)


    def antfactor (self, time, ant, feed=0):
        assert feed < self.nfeeds

        gains = self.gains
        times = self.times
        gflag = self._gflags
        dtime = self.interval
        timetab = self._timetab
        solno = self._solno
        nsols = times.size
        nfeeds = self.nfeeds
        t1, t2 = self._tidx

        tau = 0

        # "Check if (t1,t2) bounds the solution. If not, find (t1,t2)
        # which do. Use a binary step through the gains file."

        if (time - timetab[t1]) * (time - timetab[t2]) > 0:
            t1valid = t2valid = True
            n = 1

            while timetab[t2] < time and solno[t2] < nsols - 1:
                t1, t2 = t2, t1
                t1valid, t2valid = t2valid, False
                solno[t2] = min (solno[t1] + n, nsols)
                n *= 2
                timetab[t2] = times[solno[t2]]

            while timetab[t1] > time and solno[t1] > 0:
                t1, t2 = t2, t1
                t1valid, t2valid = False, t1valid
                solno[t1] = max (solno[t2] - n, 0)
                n *= 2
                timetab[t1] = times[solno[t1]]

            # "Check if we have fallen off the end of the gains table"

            if time > timetab[t2]:
                t1, t2 = t2, t1
                t1valid, t2valid = t2valid, False
                solno[t2] = nsols
                timetab[t2] = time + 1e6 * dtime
            elif time < timetab[t1]:
                t1, t2 = t2, t1
                t1valid, t2valid = False, t1valid
                solno[t1] = -1
                timetab[t1] = time - 1e6 * dtime

            # "We have solution intervals which bound "time", but they
            # may not be adjacent solutions. Home in on an adjacent
            # solution pair.

            while solno[t1] + 1 != solno[t2]:
                s = (solno[t1] + solno[t2]) / 2

                if times[s] > time:
                    solno[t2] = s
                    timetab[t2] = times[s]
                    t2valid = False
                else:
                    solno[t1] = s
                    timetab[t1] = times[s]
                    t1valid = False

            # Skip: "Read in the gains if necessary"
            self._tidx[:] = t1, t2
        # End if (need to find new interval)

        # "Determine the indices of the gains"
        i1 = (nfeeds + self.ntau) * (ant - 1) + feed

        # Python fix: we don't use uvgnget so don't
        # have gflag[invalid-solution] -> false, so
        # precompute these values

        if solno[t1] < 0 or solno[t1] >= nsols:
            gflag1 = False
        else:
            gflag1 = gflag[solno[t1],i1]

        if solno[t2] < 0 or solno[t2] >= nsols:
            gflag2 = False
        else:
            gflag2 = gflag[solno[t2],i1]

        # "Determine the gains" (for each antenna)
        flag = True
        t1good = abs (time - timetab[t1]) < dtime
        t2good = abs (time - timetab[t2]) < dtime

        if t1good and gflag1:
            ga1 = gains[solno[t1],i1]
        elif t2good and gflag2:
            ga1 = gains[solno[t2],i1]
        else:
            flag = False

        if t2good and gflag2:
            ga2 = gains[solno[t2],i1]
        elif t1good and gflag1:
            ga2 = gains[solno[t1],i1]
        else:
            flag = False

        if self.ntau > 0 and flag:
            if t1good and gflag1:
                taua1 = gains[solno[t1],i1+nfeeds]
            elif t2good and gflag2:
                taua1 = gains[solno[t2],i1+nfeeds]

            if t2good and gflag2:
                taua2 = gains[solno[t2],i1+nfeeds]
            elif t1good and gflag1:
                taua2 = gains[solno[t1],i1+nfeeds]

        # "If all is good, interpolate the gains to the current time
        # interval"

        if flag:
            epsi = (timetab[t2] - time) / (timetab[t2] - timetab[t1])
            g = ga1 / ga2
            mag = abs (g)
            # This interpolates linearly considering phase and amplitude
            # separately.
            gain = ga2 * (1 + (mag - 1) * epsi) * (g/mag) ** epsi

            if self.ntau == 0:
                tau = None
            else:
                tau = taua2 - epsi * (taua2 - taua1)

            return gain, tau

        return None, None


    def bpfactor (self, time, blcode, pol):
        assert pol < 0
        
        # Copied from uvgnfac
        if self.nfeeds == 1:
            f1 = f2 = 0
        else:
            if pol <= -5:
                pol = -4 - pol
            else:
                pol = -p

            assert pol < 5

            f1 = [0, 1, 0, 1][pol]
            f2 = [0, 1, 1, 0][pol]

        ant1, ant2 = util.decodeBaseline (blcode)
        g1, tau1 = self.antfactor (time, ant1, f1)
        g2, tau2 = self.antfactor (time, ant2, f2)

        if g1 is None or g2 is None:
            g = None
        else:
            g = g1 * g2.conjugate ()

        if tau1 is None or tau2 is None:
            tau = None
        else:
            tau = tau1 + tau2.conjugate ()

        return g, tau


__all__ += ['applyGain', 'GainsCalculator']
