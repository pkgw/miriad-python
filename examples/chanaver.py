#! /usr/bin/env python

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

"""= chanaver - Average spectral channels after applying bandpass
& pkgw
: uv Analysis
+
 CHANAVER averages spectral channels. It is less powerful than
 UVCAT/UVAVER, but it averages after applying gain and bandpass
 corrections to the input dataset. If you want to average a dataset in
 channel space after solving for the bandpass, CHANAVER saves you the
 UVCAT of the dataset normally needed to apply the bandpass before
 averaging. (If you don't do this UVCAT, the bandpass is applied after
 the channel averaging, resulting in the message "Performing linetype
 averaging before applying bandpass!!  ... this may be very unwise".)

 In some circumstances CHANAVER can also provide a more precise
 bandpass application than what is obtained via UVCAT. If the
 correlation data are stored in scaled 16-bit integer format and
 there's a birdie (a very large amplitude spike in one channel) in a
 given spectrum, there will have been a loss of precision in the input
 dataset due to the dynamic range compression needed to encode the
 birdie. When UVCAT applies the bandpass, it will maintain the birdie
 (flagged though it may be), so there will be a secondary loss of
 precision as the bulk of the data are written with a compressed
 dynamic range. CHANAVER, on the other hand, will apply the flagging
 when averaging, eliminating the birdie (assuming it has been flagged)
 and thus avoiding the second round of dynamic-range compression. This
 can be a nontrivial effect in some datasets.

 A related distinction is that averaging with the line= keyword is
 performed in the 16-bit scaled-integer space, whereas CHANAVER does
 its averaging after multiplication by the scaling factor. This should
 result in CHANAVER being subject to slightly more roundoff errors
 compared to line= averaging, but the differences should be trivial
 compared to the loss-of-precision inherent in the use of the scaled-
 integer format to begin with.

 A minor difference between CHANAVER and UVAVER is that CHANAVER does
 not share the default UVAVER behavior of discarding
 completely-flagged records.

 LIMITATIONS: CHANAVER only works with datasets containing a single
 spectral window.

@ vis
 The input dataset or datasets. For more information, see
 "mirhelp vis".

@ out
 The name of the averaged output dataset to create.

@ naver
 The number of channels to average together. This number must divide
 evenly into the number of spectral channels. A value of one is
 acceptable, meaning that calibrations will be applied and flagged
 data will be zeroed out in the output dataset.

@ slop
 The fraction of channels in each averaging bin that must be present
 in order for the averaged bin to be considered valid. Default is
 0.5, i.e., half of the channels must be unflagged. If slop is zero,
 one channel must still be good in each bin in order for the data
 to remain unflagged.

@ select
 The standard MIRIAD UV-data selection keyword. For more information,
 see "mirhelp select".

@ line
 The standard MIRIAD line processing keyword. For more information,
 see "mirhelp line".

@ stokes
 The standard MIRIAD Stokes processing keyword. For more information,
 see "mirhelp stokes".

@ ref
 The standard MIRIAD reference-line processing keyword. For more
 information, see "mirhelp ref".

@ options.
 Multiple options can be specified, separated by commas. Minimum-match
 is used.

 'nocal'  Do not apply gain/phase calibration tables.
 'nopass' Do not apply the bandpass correction. Included for
          completeness, but if you are specifying this, you should use
          UVAVER instead.
 'nopol'  Do not apply polarization leakage correction.

--
"""

import numpy as N
from miriad import VisData, ensureiterable
from mirtask import keys, util, uvdat


__all__ = ('DEFAULT_SLOP DEFAULT_BANNER InputStructureError '
           'channelAverage task').split ()

__version_info__ = (1, 0)
DEFAULT_SLOP = 0.5
DEFAULT_BANNER = 'PYTHON chanaver: channel average after applying bandpass'
UVDAT_OPTIONS = '3'


class InputStructureError (Exception):
    def __init__ (self, vis, why):
        self.vis = vis
        self.why = why
    def __str__ (self):
        return 'Cannot handle input dataset %s: %s' % (self.vis, self.why)


class _CreateFailedError (Exception):
    def __init__ (self, subexc):
        self.subexc = subexc


def channelAverage (out, naver, slop=DEFAULT_SLOP, banner=DEFAULT_BANNER,
                    args=['undefined']):
    """Read data from the uvdat subsystem and channel average into an output dataset.

    out: dataset handle; the output dataset to be created
  naver: int; the number of channels to average together (see task docs)
   slop: float; tolerance for partially flagged bins (see task docs)
 banner: string; a message to write into the output's history
   args: list of strings; command-line arguments to write into the output's history,
         not including the program name (i.e. no traditional argv[0])
returns: None

Contrast with channelAverageWithSetup, which sets up the uvdat subsytem itself
rather than assuming that it's been initialized.
"""

    if naver < 1:
        raise ValueError ('must average at least one channel (got naver=%d)' % naver)
    if slop < 0 or slop > 1:
        raise ValueError ('slop must be between 0 and 1 (got slop=%f)' % slop)

    try:
        _channelAverage (uvdat.read (), out, naver, slop, banner, args)
    except _CreateFailedError, e:
        # Don't delete the existing dataset!
        raise e.subexc
    except Exception:
        out.delete ()
        raise


def channelAverageWithSetup (toread, out, naver, slop=DEFAULT_SLOP,
                             banner=DEFAULT_BANNER, **uvdargs):
    """Read UV data and channel average into an output dataset.

   toread: dataset handle or iterable thereof; input dataset(s)
      out: dataset handle; the output dataset to be created
    naver: int; the number of channels to average together (see task docs)
     slop: float; tolerance for partially flagged bins (see task docs)
   banner: string; a message to write into the output's history
**uvdargs: keyword arguments passed through to the uvdat subsystem
           initialization (mirtask.uvdat.setupAndRead)
  returns: None

Contrast with channelAverage, which performs no extra initialization
of the uvdat subsystem.
"""

    if naver < 1:
        raise ValueError ('must average at least one channel (got naver=%d)' % naver)
    if slop < 0 or slop > 1:
        raise ValueError ('slop must be between 0 and 1 (got slop=%f)' % slop)

    try:
        gen = uvdat.setupAndRead (toread, UVDAT_OPTIONS, False, **uvdargs)
        args = ['vis=' + ','.join (str (x) for x in ensureiterable (toread))]
        args += ['%s=%s' % (k, uvdargs[k]) for k in sorted (uvdargs.iterkeys ())]
        _channelAverage (gen, out, naver, slop, banner, args)
    except _CreateFailedError, e:
        # Don't delete the existing dataset!
        raise e.subexc
    except Exception:
        out.delete ()
        raise


def _channelAverage (gen, out, naver, slop, banner, args):
    """Implementation of the channel averaging.

    gen: iterable of (hnd, pream, data, flags); source of UV records
    out: dataset handle; the output dataset to be created
  naver: int; the number of channels to average together (see task docs)
   slop: float; tolerance for partially flagged bins (see task docs)
 banner: string; a message to write into the output's history
   args: list of strings; command-line args to write into the output history
returns: None
"""
    from numpy import sum, greater_equal, maximum

    nmin = max (int (round (slop * naver)), 1) # min num. chans to avoid flagging

    firstiteration = True
    prevhnd = None
    prevnpol = 0 # for writing correct polarization metadata
    npolvaried = False # ditto

    try:
        outhnd = out.open ('c')
    except Exception, e:
        raise _CreateFailedError (e)
    outhnd.setPreambleType ('uvw', 'time', 'baseline')

    for vishnd, preamble, data, flags in gen:
        if firstiteration:
            firstiteration = False

            corrtype, _, _ = vishnd.probeVar ('corr')
            if corrtype != 'r' and corrtype != 'j' and corrtype != 'c':
                raise InputStructureError (vis, 'type of "corr" variable (%c) not '
                                           'expected (one of rjc)' % corrtype)
            outhnd.setCorrelationType (corrtype)

            vishnd.copyItem (outhnd, 'history')
            outhnd.openHistory ()
            outhnd.writeHistory (banner)
            outhnd.logInvocation ('PYTHON chanaver', args)
            outhnd.writeHistory ('PYTHON chanaver: naver=%d slop=%f' % (naver, slop))
            outhnd.closeHistory ()

        if vishnd is not prevhnd:
            # Started reading new input dataset.
            prevhnd = vishnd
            npol = 0

            tracker = vishnd.makeVarTracker ()
            tracker.track ('nchan', 'nspect', 'nwide', 'sdf', 'nschan',
                           'ischan', 'sfreq')

            # We don't care about these, but they would normally be copied
            # by the VarCopy(line=channel) logic.
            for var in 'restfreq systemp xtsys ytsys xyphase'.split ():
                vishnd.trackVar (var, False, True)

            vishnd.initVarsAsInput (' ') # set up to copy basic variables
            outhnd.initVarsAsOutput (vishnd, ' ')

        if tracker.updated ():
            # Potentially new spectral configuration. Verify.
            nspect = vishnd.getScalar ('nspect', 0)
            nwide = vishnd.getScalar ('nwide', 0)
            nchan = vishnd.getScalar ('nchan', 0)

            if nspect != 1:
                raise InputStructureError (vis, 'require exactly one spectral window')
            if nwide != 0:
                raise InputStructureError (vis, 'require no wideband windows')

            sdf = vishnd.getVarDouble ('sdf', nspect)
            nschan = vishnd.getVarInt ('nschan', nspect)
            ischan = vishnd.getVarInt ('ischan', nspect)
            sfreq = vishnd.getVarDouble ('sfreq', nspect)

            if nschan != nchan:
                raise InputStructureError (vis, 'require nchan (%d) = nschan (%d)' %
                                           (nchan, nschan))
            if ischan != 1:
                raise InputStructureError (vis, 'require ischan (%d) = 1' % ischan)

            if nchan % naver != 0:
                raise InputStructureError (vis, 'require nchan (%d) to be a multiple '
                                           'of naver (%d)' % (nchan, naver))

            # OK, everything is hunky-dory. Compute new setup.

            nout = nchan // naver
            sdfout = sdf * naver
            sfreqout = sfreq + 0.5 * sdf * (naver - 1)

            outdata = N.empty (nout, dtype=N.complex64)
            outflags = N.empty (nout, dtype=N.int32)
            counts = N.empty (nout, dtype=N.int32)

            outhnd.writeVarInt ('nspect', 1)
            outhnd.writeVarInt ('nschan', nout)
            outhnd.writeVarInt ('ischan', 1)
            outhnd.writeVarDouble ('sdf', sdfout)
            outhnd.writeVarDouble ('sfreq', sfreqout)

        # Do the averaging. This is as fast as I know how to make it
        # within numpy. Have no idea if there's a way to take advantage
        # of multicore processors that is robustly faster and not a
        # ton of effort.

        data *= flags # zero out flagged data
        sum (data.reshape ((nout, naver)), axis=1, out=outdata)
        sum (flags.reshape ((nout, naver)), axis=1, out=counts)
        greater_equal (counts, nmin, outflags)
        maximum (counts, 1, counts) # avoid div-by-zero
        outdata /= counts

        # Write, with the usual npol tomfoolery.

        vishnd.copyLineVars (outhnd)
        vishnd.copyMarkedVars (outhnd)

        if npol == 0:
            npol = vishnd.getNPol ()
            if npol != prevnpol:
                outhnd.writeVarInt ('npol', npol)
                npolvaried = npolvaried or prevnpol != 0
                prevnpol = npol

        outhnd.writeVarInt ('pol', vishnd.getPol ())
        outhnd.write (preamble, outdata, outflags)
        npol -= 1

    # All done.

    if not npolvaried:
        outhnd.setScalarItem ('npol', N.int32, prevnpol)

    outhnd.close ()


def task (args):
    """Run as a command-line task.

   args: list of strings; command-line arguments, not including the
         program name (no traditional argv[0]).
returns: None

Will call mirtask.util.die on some errors.
"""
    util.checkusage (__doc__, ['dummy'] + args)

    ks = keys.KeySpec ()
    ks.keyword ('out', 'f', ' ')
    ks.keyword ('naver', 'i', -1)
    ks.keyword ('slop', 'd', DEFAULT_SLOP)
    ks.uvdat (UVDAT_OPTIONS + 'dslr')
    opts = ks.process (args)

    if opts.out == ' ':
        util.die ('must specify an output filename (out=...)')
    out = VisData (opts.out)

    if opts.naver == -1:
        util.die ('must specify the number of channels to average (naver=...)')

    try:
        channelAverage (out, opts.naver, opts.slop, banner=DEFAULT_BANNER, args=args)
    except (InputStructureError, ValueError), e:
        util.die (str (e))


if __name__ == '__main__':
    import sys
    from mirtask import cliutil # install user-friendly-ish exception handling
    task (sys.argv[1:])
