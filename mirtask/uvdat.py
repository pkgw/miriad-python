'''mirtask.uvdat - wrappers for the MIRIAD UV-data streaming API'''

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
from mirtask import _miriad_c, _miriad_f, MiriadError, UVDataSet
from miriad import VisData, commasplice

__all__ = []

# Python 2.4 compatibility: no try/finally in generators. Trying
# this raises a SyntaxError, which can't be caught within a module,
# but can be on import

try:
    from _uvdat_compat_default import _inputSets, _read_gen
except SyntaxError:
    import sys
    v = sys.version_info[0] * 1000 + sys.version_info[1]
    if v >= 2005:
        # Genuine syntax error!
        raise
    del v, sys
    from _uvdat_compat_24 import _inputSets, _read_gen


class UVDatDataSet (UVDataSet):
    """:synopsis: a handle to a UV dataset being read with the UVDAT
    subsystem

This class is a subclass of :class:`mirtask.UVDataSet` with extra code
to invoke the correct lifecycle functions associated with MIRIAD's
UVDAT subsystem. It should transparently behave like a
:class:`mirtask.UVDataSet` from the Python programmer's perspective.

You should not construct a :class:`UVDatDataSet` yourself.
"""
    def __init__ (self, tno):
        self.tno = tno
        self._path = _getString ('name')

    def _close (self):
        _miriad_f.uvdatcls ()

    # Prohibit UVDataSet functions that affect our progress through the
    # stream, which would mess up the UVDAT routines.

    def next (self):
        raise RuntimeError ('next() not allowed when reading with UVDAT system')

    def scanUntilChange (self, varname):
        raise RuntimeError ('scanUntilChange() not allowed when reading with UVDAT system')

    # Override UVDataSet functions that have uvdat-based implementations

    def rewind (self):
        _miriad_f.uvdatrew ()

    def lowlevelRead (self, preamble, data, flags, length=None):
        if length is None:
            length = flags.size

        self._checkOpen ()
        return _miriad_f.uvdatrd (preamble, data, flags, length)

    def getCurrentVisNum (self):
        return _getOneInt ('visno') - 1

    def getPol (self):
        return _getOneInt ('pol')

    def getNPol (self):
        return _getOneInt ('npol')

    def getJyPerK (self):
        return _miriad_f.uvdatgtr ('jyperk')

    def getVariance (self):
        return _miriad_f.uvdatgtr ('variance')


def inputSets ():
    """Retrieve handles to the datasets to be read by the UVDAT
    subsystem.

:rtype: generator of :class:`UVDatDataSet`
:returns: handles to the datasets to by read by the UVDAT system

Generates a sequence of :class:`UVDatDataSet` objects allowing access
to the datasets that would be read by the UVDAT subsystem.

If you plan on reading the UV data associated with these handles, you
should instead use :func:`read`.

See also :func:`singleInputSet` in the case that you know there is
exactly one input dataset.
"""
    # Implemented in one of _uvdat_compat_default or _uvdat_compat_24
    # thanks to compatibility issues with Python 2.4
    return _inputSets (UVDatDataSet)


def singleInputSet ():
    """Get a :class:`UVDatDataSet` object representing the input UV dataset.

:rtype: :class:`UVDatDataSet`
:returns: a UV data dataset

Retrieves a :class:`UVDatDataSet` object corresponding to the dataset
to be read by the UVDAT subsystem.

If you want to read the UV data associated with this handle, use
:func:`read` or :func:`setupAndRead`.

The subsystem can accept more than one input dataset generically, but
you should only call this function if UVDAT has been initialized to
read only one dataset. You can ensure this condition by passing the
*b* option to :func:`setupAndRead` or
:meth:`mirtask.keys.KeySpec.uvdat`. If you don't want to or can't
enforce this condition, use :func:`inputSets`.
"""

    # In certain cases (e.g. an empty dataset, which yields an
    # "Invalid preamble time/baseline" MiriadError if there's no coord
    # UV variable), UVDATOPN can fail with a bug('f') call but still
    # leave the dataset opened. This means that too many successive
    # such failures will fill up MIRIAD's static buffer of UV dataset
    # information and make it impossible to open more datasets. This
    # could be solved by catching the exception and calling
    # UVDATCLS().
    #
    # On the other hand, if, say, the desired dataset doesn't exist,
    # then we get a MiriadError without having the dataset opened, and
    # if we call UVDATCLS, we segfault.
    #
    # I haven't yet figured out a way to handle both of these cases
    # cleanly. With some hacking of UVDATOPN or the uvdat module
    # in general, something could be worked out. In the meantime, we
    # prefer to avoid the segfault.
    #
    # Similar code is relevant in _uvdat_compat_*:inputSets.

    status, tin = _miriad_f.uvdatopn ()

    if not status:
        raise RuntimeError ('No input datasets?!')

    # Count on the user or the __del__ to close this.
    return UVDatDataSet (tin)


def read (saveFlags=False, maxchan=4096):
    """Read in data via the UVDAT subsystem.

:arg saveFlags: whether to rewrite the flags of the dataset(s) as it/they are
                being read
:type saveFlags: :class:`bool`
:arg maxchan: the maximum number of spectral channels that can be read in at once
:type maxchan: :class:`int`
:rtype: generator of ``(handle, preamble, data, flags)``
:returns: generator yielding UV data records

Read in data with the UVDAT subsystem. The system must have previously
been initialized, typically in a call to
:meth:`mirtask.keys.KeySpec.process` after configuration with
:meth:`mirtask.keys.KeySpec.uvdat`.

The return value is a generator that yields tuples of ``(handle,
preamble, data, flags)``, where *handle* is a :class:`UVDatDataSet`
corresponding to the dataset being read, and *preamble*, *data*, and
*flags* are the usual UV data arrays. For speed, the identities of the
arrays do not change from iteration to iteration, but their contents do.
"""
    return _read_gen (saveFlags, UVDatDataSet, maxchan)


def setupAndRead (toread, uvdOptions, saveFlags, nopass=False, nocal=False,
                  nopol=False, select=None, line=None, stokes=None, ref=None,
                  maxchan=4096):
    """Set up the UVDAT subsystem manually and read in the data.

:arg toread: the name(s) of the dataset or datasets to read
:type toread: stringable or iterable of stringable
:arg uvdOptions: extra options controlling the behavior of the UVDAT subsytem
:type uvdOptions: :class:`str`
:arg saveFlags: whether to rewrite the flags of the dataset(s) as it/they are
                being read
:type saveFlags: :class:`bool`
:arg nopass: whether to avoid applying bandpass calibration even if possible
:type nopass: :class:`bool`
:arg nocal: whether to avoid applying gain calibration even if possible
:type nocal: :class:`bool`
:arg nopol: whether to avoid applying polarization calibration even if possible
:type nopol: :class:`bool`
:arg select: standard UV data selection string
:type select: :class:`str` or :const:`None`
:arg line: standard channel processing string
:type line: :class:`str` or :const:`None`
:arg stokes: standard Stokes parameter processing string
:type stokes: :class:`str` or :const:`None`
:arg ref: standard reference line specification string
:type ref: :class:`str` or :const:`None`
:arg maxchan: the maximum number of spectral channels that can be read in at once
:type maxchan: :class:`int`
:rtype: generator of ``(handle, preamble, data, flags)``
:returns: generator yielding UV data records

Set up the UVDAT subsytem with explicitly-specified parameters and
read in the data.

The argument *toread* specifies which dataset or datasets to read. If
it is a non-string iterable, the stringification of each of its values
is treated as a dataset to read. Otherwise, its stringification is
treated as the dataset to read. Escaping is not supported by MIRIAD,
so if ``toread = 'a,b'``, MIRIAD will interpret this as a direction to
read two datasets named "a" and "b".

The return value is a generator that yields tuples of ``(handle,
preamble, data, flags)``, where *handle* is a :class:`UVDatDataSet`
corresponding to the dataset being read, and *preamble*, *data*, and
*flags* are the usual UV data arrays. For speed, the identities of the
arrays do not change from iteration to iteration, but their contents do.

Optional features of the UVDAT subsystem may be enabled by including
their control characters in the contents of *uvdOptions*:

==========      ==================
Character       Feature behavior
==========      ==================
*p*             Planet rotation and scaling corrections should be applied.
*w*             UVW coordinates should be returned in wavelength units, not
                nanoseconds. (Beware when writing these data to new UV
                datasets, as the output routines expect the values to
                be in nanoseconds.)
*1*             (The character is the number one.) Average the data
                down to one channel.
*x*             The input data must be cross-correlations.
*a*             The input data must be autocorrelations.
*b*             The input must be exactly one UV dataset (not multiple).
*3*             The "preamble" returned while reading data will always have 5
                elements and include the *w* coordinate.
==========      ==================
"""
    args = ['vis=' + commasplice (toread)]
    flags = uvdOptions + 'dslr'
    options = set ()

    if select is not None:
        args.append ('select=' + select)
    if line is not None:
        args.append ('line=' + line)
    if stokes is not None:
        args.append ('stokes=' + stokes)
    if ref is not None:
        args.append ('ref=' + ref)

    if nopass:
        options.add ('nopass')
    if nocal:
        options.add ('nocal')
    if nopol:
        options.add ('nopol')
    if len (options) > 0:
        args.append ('options=' + ','.join (options))

    from keys import KeySpec
    KeySpec ().uvdat (flags).process (args)
    return _read_gen (saveFlags, UVDatDataSet, maxchan)


# Variable probes

def _getOneInt (kw):
    a = N.zeros (1, dtype=N.int32)
    _miriad_f.uvdatgti (kw, a)
    return a[0]


def _getString (kw):
    buf = N.chararray (120)
    _miriad_f.uvdatgta (kw, buf)

    # Better way?
    for i in xrange (buf.size):
        if buf[i] == '':
            return buf[:i].tostring ()

    raise MiriadError ('output from uvdatgta exceeded buffer size')


def getNPol ():
    """Return the number of simultaneous polarizations being returned by readData.
Zero indicates that this number could not be determined.
"""    
    return _getOneInt ('npol')

def getPols ():
    """Return the polarizations being returned by readData, an array of the size
returned by getNPol (). Zeros indicate an error. Polarization values are as in FITS
and are defined in mirtask.util.POL\_??. """

    a = N.zeros (getNPol (), dtype=N.int32)
    _miriad_f.uvdatgti ('pols', a)
    return a

def getPol ():
    """Return the last Stokes parameter returned by readData. May vary from one
visibility to another."""

    return _getOneInt ('pol')

def getNChan ():
    """Return the number of channels being processed."""
    return _getOneInt ('nchan')

def getNFiles ():
    """Return the number of files being processed."""
    return _getOneInt ('nfiles')

def getVisNum ():
    """Get the serial number of the current UV record.

:returns: the serial number
:rtype: int

Counting begins at zero. The return value may vary from what
:meth:`mirtask.UVDataSet.getCurrentVisNum` returns if polarization
processing is active, because the underlying data records may
be merged.
"""
    return _getOneInt ('visno') - 1

def getVariance ():
    """Return the variance of the current visibility."""
    return _miriad_f.uvdatgtr ('variance')

def getJyPerK ():
    """Return the Jansky-per-Kelvin value of the current visibility."""
    return _miriad_f.uvdatgtr ('jyperk')


def getCurrentName ():
    """Get the path of the file currently being processed.

:returns: the path of the file currently being processed
:rtype: string

Maps to a call of MIRIAD's UVDATGTA function with an "object" of "name".
"""
    return _getString ('name')


def getLinetype ():
    """Get the linetype of the current record.

:returns: the linetype
:rtype: string

The linetype is one of "channel", "velocity", "felocity", "wide", or
"" (if not explicitly specified on the commandline). Maps to a call of
MIRIAD's UVDATGTA function with an "object" of "ltype".
"""
    return _getString ('ltype')
