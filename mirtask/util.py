'''mirtask.util - miscellaneous utility subroutines for MIRIAD tasks'''

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

import numpy as N
from mirtask import _miriad_f

# Banner printing (and Id string decoding)

def printBannerSvn (name, desc, idstr):
    """Print a banner string containing the name of a task, its
    description, and versioning information extracted from a
    Subversion ID string. The banner string is returned as well."""

    try:
        file, rev, date, time, user = idstr[5:-2].split ()
    except:
        rev = '???'
        date = '?'
        time = '?'

    b = '%s: %s (Python, SVN r%s, modified %s %s)' % (name, desc,
                                                      rev, date, time)
    print b
    return b


def printBannerGit (name, desc, idstr):
    """Print a banner string containing the name of a task, its
    description, and SHA1 information extracted from a Git ID
    string. The banner string is returned as well."""

    sha1 = idstr[5:-2]
    b = '%s: %s (Python, SHA1 %s)' % (name, desc, sha1)
    print b
    return b


def die (format, *args):
    """Raise a :exc:`SystemExit` exception with a formatted error message.

:arg str format: a format string
:arg args: arguments to the format string

A :exc:`SystemExit` exception is raised with the argument ``'error: '
+ (format % args)``. If uncaught, the interpreter exits with an error
code and prints the exception argument.

Example::

   if ndim != 3:
      die ('require exactly 3 dimensions, not %d', ndim)
"""

    raise SystemExit ('error: ' + (format % args))


def showusage (docstring):
    """Print program usage information and exit.

:arg str docstring: the program help text

This function just prints *docstring*, with one wrinkle described
below, and exits. In most cases, the function :func:`checkusage`
should be used: it automatically checks :data:`sys.argv` for a sole
"-h" or "--help" argument and invokes this function.

The wrinkle is that if ``docstring[0]`` is '=', which is the signpost
that the docstring is written in MIRIAD "doc" markup, the
miriad-python help program :command:`mirpyhelp.py` is executed with a
guess of the name of the current program as an argument. The program
name is guessed from the second token of the docstring, which should
be the program name by MIRIAD conventions. If this launch fails, the
raw docstring is printed.

This function is provided in case there are instances where the user
should get a friendly usage message that :func:`checkusage` doesn't
catch. It can be contrasted with :func:`wrongusage`, which prints a
terser usage message and exits with an error code.
"""

    if docstring[0] != '=':
        # Unformatted help text
        print docstring.strip ()
        raise SystemExit (0)

    # The docstring appears to be MIRIAD help text. Invoke
    # mirpyhelp.py to display documentation. There's no convenient way
    # to feed the Python-to-doc converter the docstring we've been
    # given, so we parse out the program name from the '=' line and
    # hope that works.

    try:
        progname = docstring.splitlines ()[0].split ()[1]
        import subprocess
        if subprocess.call (['mirpyhelp.py', progname], shell=False):
            raise Exception () # help program didn't work
    except:
        print docstring.strip ()

    raise SystemExit (0)


def checkusage (docstring, argv=None, usageifnoargs=False):
    """Check if the program has been run with a --help argument; if so,
print usage information and exit.

:arg str docstring: the program help text
:arg argv: the program arguments; taken as :data:`sys.argv` if
  given as :const:`None` (the default)
:arg bool usageifnoargs: if :const:`True`, usage information will be
  printed and the program will exit if no command-line arguments are
  passed. Default is :const:`False`.

This function is intended for small programs launched from the command
line. The intention is for the program help information to be written
in its docstring, and then for the preamble to contain something
like::

  \"\"\"myprogram - this is all the usage help you get\"\"\"
  from mirtask.util import checkusage
  ... # other setup
  checkusage (__doc__)
  ... # go on with business

If it is determined that usage information should be shown,
:func:`showusage` is called and the program exits.

As described more fully in the :func:`showusage` documentation,
*docstring* is treated specially if it begins with an equals sign,
which indicates that it is written in MIRIAD "doc" markup. In that
case, the :command:`mirpyhelp.py` MIRIAD documentation program is run.

See also :func:`wrongusage`.
"""

    if argv is None:
        from sys import argv

    if len (argv) == 1 and usageifnoargs:
        showusage (docstring)

    if len (argv) == 2 and argv[1] in ('-h', '--h', '--he', '--hel', '--help'):
        showusage (docstring)


def wrongusage (docstring, *rest):
    """Print a message indicating invalid command-line arguments and
exit with an error code.

:arg str docstring: the program help text
:arg rest: an optional specific error message

This function is intended for small programs launched from the command
line. The intention is for the program help information to be written
in its docstring, and then for argument checking to look something
like this::

  \"\"\"mytask <input> <output>

  Do something to the input to create the output.
  \"\"\"
  ...
  import sys
  from mirtask.util import checkusage, wrongusage
  ... # other setup
  checkusage (__doc__)
  ... # more setup
  if len (sys.argv) != 3:
     wrongusage (__doc__, "expect exactly 3 arguments, not %d",
                 len (sys.argv))

When called, an error message is printed along with the *first stanza*
of *docstring*. The program then exits with an error code and a
suggestion to run the program with a --help argument to see more
detailed usage information. The "first stanza" of *docstring* is
defined as everything up until the first blank line, ignoring any
leading blank lines.

The optional message in *rest* is treated as follows. If *rest* is
empty, the error message "invalid command-line arguments" is
printed. If it is a single item, that item is printed. If it is more
than one item, the first item is treated as a format string, and it is
percent-formatted with the remaining values. See the above example.

If *docstring* starts with an equals sign, it is taken to be
MIRIAD-format doc markup, and the first stanza is *not* printed.

See also :func:`checkusage` and :func:`showusage`.
"""

    import sys
    intext = False

    if len (rest) == 0:
        detail = 'invalid command-line arguments'
    elif len (rest) == 1:
        detail = rest[0]
    else:
        detail = rest[0] % tuple (rest[1:])

    print >>sys.stderr, 'error:', detail
    print >>sys.stderr

    # If the docstring doesn't appear to be in MIRIAD doc format,
    # print the first stanza

    if docstring[0] != '=':
        for l in docstring.splitlines ():
            if intext:
                if not len (l):
                    break
                print >>sys.stderr, l
            elif len (l):
                intext = True
                print >>sys.stderr, 'Usage:', l
        print >>sys.stderr

    print >>sys.stderr, \
        'Run with a sole argument --help for more detailed usage information.'
    raise SystemExit (1)


# Baseline-related stuff

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return _miriad_f.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return _miriad_f.antbas (ant1, ant2)

# Linetype constants. From subs/uvio.c

LINETYPE_NONE = 0
LINETYPE_CHANNEL = 1
LINETYPE_WIDE = 2
LINETYPE_VELOCITY = 3
LINETYPE_FELOCITY = 4

_ltNames = { LINETYPE_NONE: 'undefined',
             LINETYPE_CHANNEL: 'channel',
             LINETYPE_WIDE: 'wide',
             LINETYPE_VELOCITY: 'velocity',
             LINETYPE_FELOCITY: 'felocity',
}

def linetypeName (linetype):
    """Given a linetype number, return its textual description

:arg int linetype: the linetype code
:returns: the description
:rtype: str

The linetypes are:

================== ============== ============
Symbolic Constant  Numeric Value  Description
================== ============== ============
LINETYPE_NONE      0              "undefined"
LINETYPE_CHANNEL   1              "channel"
LINETYPE_WIDE      2              "wide"
LINETYPE_VELOCITY  3              "velocity"
LINETYPE_FELOCITY  4              "felocity"
================== ============== ============

The "felocity" type is used for spectral data resampled at
even velocity increments, using the "optical definition" of velocity,
``v / c = (lambda - lambda0) / lambda0``. The "radio definition"
is slightly different: ``v / c = (nu0 - nu) / nu0``.
"""
    return _ltNames[linetype]


def linetypeFromName (text):
    """Given a linetype name, return the corresponding numeric code.

:arg str text: the name of a linetype
:returns: the code
:rtype: int
:throws: :exc:`ValueError` if *text* doesn't correspond to one
  of the linetype names.

See :func:`linetypeName` for a description of the linetype symbolic
constants, their numerical values, and standard textual descriptions.

Matching in this function is done case-insensitively and accepts
partial matches. Because the linetype names all begin with different
letters, this means that a code can be retrieved using just a single
letter. Strings of all whitespace, or the empty string, are mapped to
:const:`LINETYPE_NONE`.
"""
    if not len (text.strip ()):
        return LINETYPE_NONE

    ltext = text.lower ()

    for lt, name in _ltNames.iteritems ():
        if name.startswith (ltext):
            return lt

    raise ValueError ('text "%s" does not express a linetype name', text)


# Polarizations. From subs/uvdat.h

POL_II = 0
POL_I = 1
POL_Q = 2
POL_U = 3
POL_V = 4
POL_RR = -1
POL_LL = -2
POL_RL = -3
POL_LR = -4
POL_XX = -5
POL_YY = -6
POL_XY = -7
POL_YX = -8
POL_QQ = 5
POL_UU = 6

_polNames = { POL_II: 'II', POL_I: 'I', POL_Q: 'Q',
              POL_U: 'U', POL_V: 'V', POL_RR: 'RR',
              POL_LL: 'LL', POL_RL: 'RL', POL_LR: 'LR',
              POL_XX: 'XX', POL_YY: 'YY', POL_XY: 'XY',
              POL_YX: 'YX', POL_QQ: 'QQ', POL_UU: 'UU' }

def polarizationName (polnum):
    """Return the textual description of a MIRIAD polarization type
    from its number."""

    return _polNames[polnum]

def polarizationNumber (polname):
    for (num, name) in _polNames.iteritems ():
        if name.lower () == polname.lower (): return num

    raise Exception ('Unknown polarization name \'%s\'' % polname)

def polarizationIsInten (polnum):
    """Return True if the given polarization is intensity-type, e.g.,
    is I, XX, YY, RR, or LL."""

    return _miriad_f.polspara (polnum)

# And, merging them together: antpol and basepol handling.
#
# In the following, "M" stands for the MIRIAD antenna number
# of an antenna. These numbers are 1-based. "P" stands for
# a MIRIAD polarization number, values given above.
#
# First, a "feed polarization" (f-pol) is a polarization that an
# individual feed can respond to. We include Stokes parameters here,
# even though such feeds can't operate physically, to allow sensible
# roundtripping with MIRIAD/FITS polarization values in the code
# below.

FPOL_X = 0
FPOL_Y = 1
FPOL_R = 2
FPOL_L = 3
FPOL_I = 4
FPOL_Q = 5
FPOL_U = 6
FPOL_V = 7

fPolNames = 'XYRLIQUV'

# This table helps split a MIRIAD/FITS pol code into a pair of f-pol
# values.  The pair is packed into 8 bits, the upper 3 being for the
# left pol and the lower 4 being for the right. An offset of 8 is
# required because the pol codes range from -8 to +6

_polToFPol = [0x10, 0x01, 0x11, 0x00, # YX XY YY XX
              0x32, 0x23, 0x33, 0x22, # LR RL LL RR
              0x44, # II
              0x44, 0x55, 0x66, 0x77, # I Q U V
              0x55, 0x66] # QQ UU

# This table performs the reverse mapping, with index being the two
# f-pol values packed into four bits each. A value of 0xFF indicates
# an illegal pairing. Correlations written in Stokes space are
# indicated with the single-letter FITS codes; the "II", "QQ", and
# "UU" codes are only used during pol conversion inside UVDAT.

_fpolToPol = N.ndarray (128, dtype=N.int8)
_fpolToPol.fill (0xFF)
_fpolToPol[0x00] = POL_XX
_fpolToPol[0x01] = POL_XY
_fpolToPol[0x10] = POL_YX
_fpolToPol[0x11] = POL_YY
_fpolToPol[0x22] = POL_RR
_fpolToPol[0x23] = POL_RL
_fpolToPol[0x32] = POL_LR
_fpolToPol[0x33] = POL_LL
_fpolToPol[0x44] = POL_I
_fpolToPol[0x55] = POL_Q
_fpolToPol[0x66] = POL_U
_fpolToPol[0x77] = POL_V

# A "antpol" (AP) is an integer identifying an antenna/f-pol pair. It
# can be decoded without any external information.  The translation
# between AP and M,FP is:
#
#   AP = (M - 1) << 3 + FP
#
# or
#
#   M = AP >> 3 + 1
#   P = AP & 0x7
#
# Note that arbitrarily-large antenna numbers can be encoded
# if sufficiently many bits are used to store the AP. Also note that
# if you think of the antpol "antenna number" as AP >> 3, antpol
# antenna numbers start at zero, while MIRIAD antenna numbers start at
# one.

def fmtAP (ap):
    m = (ap >> 3) + 1
    fp = ap & 0x7
    return '%d%c' % (m, fPolNames[fp])

def apAnt (ap):
    return (ap >> 3) + 1

def apFPol (ap):
    return ap & 0x7

def antpol2ap (m, fpol):
    return ((m - 1) << 3) + fpol

def parseAP (text):
    try:
        polcode = text[-1].upper ()
        fpol = fPolNames.find (polcode)
        assert fpol >= 0

        m = int (text[:-1])
        assert m > 0
    except:
        raise ValueError ('text does not specify an antpol: ' + text)

    return antpol2ap (m, fpol)


# A "basepol" is a baseline between two antpols. It is expressed as a
# 2-tuple of antpols.

def fmtBP (bp):
    ap1, ap2 = bp

    if ap1 < 0:
        raise ValueError ('first antpol %d is negative' % ap1)
    if ap2 < 0:
        raise ValueError ('second antpol %d is negative' % ap2)

    m1 = (ap1 >> 3) + 1
    fp1 = ap1 & 0x7
    m2 = (ap2 >> 3) + 1
    fp2 = ap2 & 0x7

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])


def bp2aap (bp):
    """Converts a basepol into a tuple of (ant1, ant2, pol)."""

    ap1, ap2 = bp

    if ap1 < 0:
        raise ValueError ('first antpol %d is negative' % ap1)
    if ap2 < 0:
        raise ValueError ('second antpol %d is negative' % ap2)

    m1 = (ap1 >> 3) + 1
    m2 = (ap2 >> 3) + 1
    pol = _fpolToPol[((ap1 & 0x7) << 4) + (ap2 & 0x7)]

    if pol == 0xFF:
        raise ValueError ('no FITS polarization code for pairing '
                          '%c-%c' % (fPolNames[ap1 & 0x7],
                                     fPolNames[ap2 & 0x7]))

    return m1, m2, pol


def aap2bp (m1, m2, pol):
    """\
Create a basepol from antenna numbers and a FITS/MIRIAD polarization
code.

:arg int m1: the first antenna number; *one*-based as used
  internally by MIRIAD, not zero based
:arg int m2: the second antenna number; also one-based
:type pol: FITS/MIRIAD polarization code
:arg pol: the polarization
:returns: the corresponding basepol
:raises: :exc:`ValueError` if *m1* or *m2* is below one, or
  *pol* is not a known polarization code.

Note that the input antenna numbers should be one-based, not
zero-based as more conventional for C and Python. (This
is consistent with :func:`bp2aap`.) *m1* need not be
smaller than *m2*, although this is the typical convention.
"""

    if m1 < 1:
        raise ValueError ('first antenna is below 1: %s' % m1)
    if m2 < 0:
        raise ValueError ('second antenna is below 1: %s' % m2)
    if pol < POL_YX or pol > POL_UU:
        raise ValueError ('illegal polarization code %s' % pol)

    fps = _polToFPol[pol + 8]
    ap1 = ((m1 - 1) << 3) + ((fps >> 4) & 0x07)
    ap2 = ((m2 - 1) << 3) + (fps & 0x07)
    return ap1, ap2


def bp2blpol (bp):
    """Converts a basepol into a tuple of (bl, pol) where
'bl' is the MIRIAD-encoded baseline number."""

    m1, m2, pol = bp2aap (bp)
    return encodeBaseline (m1, m2), pol


def mir2bp (inp, preamble):
    """Uses a UV dataset and a preamble array to return a basepol."""

    pol = inp.getPol ()
    fps = _polToFPol[pol + 8]
    m1, m2 = decodeBaseline (preamble[4])

    ap1 = ((m1 - 1) << 3) + ((fps >> 4) & 0x07)
    ap2 = ((m2 - 1) << 3) + (fps & 0x07)

    return ap1, ap2


def bpIsInten (bp):
    ap1, ap2 = bp

    if ap1 < 0:
        raise ValueError ('first antpol %d is negative' % ap1)
    if ap2 < 0:
        raise ValueError ('second antpol %d is negative' % ap2)

    fp1, fp2 = ap1 & 0x7, ap2 & 0x7
    return (fp1 >= 0 and fp1 < 5 and fp2 == fp1)


def parseBP (text):
    t1, t2 = text.split ('-', 1)

    try:
        fp1 = fPolNames.find (t1[-1].upper ())
        assert fp1 >= 0

        m1 = int (t1[:-1])
        assert m1 > 0

        fp2 = fPolNames.find (t2[-1].upper ())
        assert fp2 >= 0

        m2 = int (t2[:-1])
        assert m2 > 0
    except Exception:
        raise ValueError ('text does not specify a basepol: ' + text)

    return ((m1 - 1) << 3) + fp1, ((m2 - 1) << 3) + fp2


# A "packed 32-bit basepol" (PBP32) encodes a basepol in a single
# 32-bit integer. It can be decoded without any external
# information. The translation between PBP32 and M1,M2,FP1,FP2 is:
#
#  PBP32 = ((M1 - 1) << 19) + (FP1 << 16) + ((M2 - 1) << 3) + FP2
#
# or
#
#  M1 = (PBP32 >> 19) + 1
#  FP1 = (PBP32 >> 16) & 0x7
#  M2 = (PBP32 >> 3 & 0x1FFF) + 1
#  FP2 = PBP32 & 0x7
#
# This encoding allocates 13 bits for antenna number, which gets us up
# to 8192 antennas. This should be sufficient for most applications.

def fmtPBP32 (pbp32):
    if pbp32 < 0 or pbp32 > 0xFFFFFFFF:
        raise ValueError ('illegal PBP32 0x%x' % pbp32)

    m1 = ((pbp32 >> 19) & 0x1FFF) + 1
    fp1 = (pbp32 >> 16) & 0x7
    m2 = ((pbp32 >> 3) & 0x1FFF) + 1
    fp2 = pbp32 & 0x7

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])


def mir2pbp32 (handle, preamble):
    fps = _polToFPol[handle.getPol () + 8]
    m1, m2 = _miriad_f.basants (preamble[4], True)

    if m1 > 0x2000:
        raise ValueError ('cannot encode baseline %d-%d in PBP32: '
                          'm1 > 0x2000' % (m1, m2))
    if m2 > 0x2000:
        raise ValueError ('cannot encode baseline %d-%d in PBP32: '
                          'm2 > 0x2000' % (m1, m2))

    return ((m1 - 1) << 19) + ((fps & 0x70) << 12) + ((m2 - 1) << 3) \
        + (fps & 0x7)


def pbp32ToBP (pbp32):
    if pbp32 < 0 or pbp32 > 0xFFFFFFFF:
        raise ValueError ('illegal PBP32 %x' % pbp32)
    return ((pbp32 >> 16) & 0xFFFF, pbp32 & 0xFFFF)


def bpToPBP32 (bp):
    ap1, ap2 = bp

    if ap1 < 0:
        raise ValueError ('first antpol %d is negative' % ap1)
    if ap2 < 0:
        raise ValueError ('second antpol %d is negative' % ap2)
    if ap1 > 0xFFFF:
        raise ValueError ('cannot store first antpol 0x%x in PBP32: '
                          'a1 > 0xFFFF' % ap1)
    if ap2 > 0xFFFF:
        raise ValueError ('cannot store second antpol 0x%x in PBP32: '
                          'a2 > 0xFFFF' % ap2)

    return (ap1 << 16) + (ap2 & 0xFFFF)


def pbp32IsInten (pbp32):
    if pbp32 < 0 or pbp32 > 0xFFFFFFFF:
        raise ValueError ('illegal PBP32 %x' % pbp32)

    return (pbp32 & 0x70007) in (0, 0x10001, 0x20002, 0x30003, 0x40004)


def parsePBP32 (text):
    t1, t2 = text.split ('-', 1)

    try:
        fp1 = fPolNames.find (t1[-1].upper ())
        assert fp1 >= 0

        m1 = int (t1[:-1])
        assert m1 > 0

        fp2 = fPolNames.find (t2[-1].upper ())
        assert fp2 >= 0

        m2 = int (t2[:-1])
        assert m2 > 0
    except Exception:
        raise ValueError ('text does not encode a basepol: ' + text)

    if m1 > 0x2000 or m2 > 0x2000:
        raise ValueError ('basepol cannot be encoded in a PBP32: ' + text)

    return ((m1 - 1) << 19) + (fp1 << 16) + ((m2 - 1) << 3) + fp2


# Date stuff

def jdToFull (jd, form='H'):
    """Return a textual representation of a Julian date.

:arg double jd: a Julian date
:arg character form: the output format, described below.
  Defaults to "H".
:returns: the textualization of the Julian date
:raises: :exc:`MiriadError` in case of buffer overflow
  (should never happen)

The possible output formats are:

==========  ====================================
Character   Result
==========  ====================================
*H*         "yyMONdd:mm:mm:ss.s" ("MON" is the three-letter abbreviation
            of the month name.)
*T*         "yyyy-mm-ddThh:mm:ss.s" (The "T" is literal.)
*D*         "yyMONdd.dd"
*V*         "dd-MON-yyyy" (loses fractional day)
*F*         "dd/mm/yy" (loses fractional day)
==========  ====================================
"""

    calday = N.chararray (120)
    _miriad_f.julday (jd, form, calday)

    for i in xrange (calday.size):
        if calday[i] == '':
            return calday[:i].tostring ()

    raise MiriadError ('Output from julday exceeded buffer size')


def jdToPartial (jd):
    """Return a string representing the time-of-day portion of the
    given Julian date in the form 'HH:MM:SS'. Obviously, this loses
    precision from the JD representation."""

    # smauvplt does the hr/min/sec breakdown manually so I shall
    # do the same except maybe a bit better because I use jul2ut.

    from math import floor, pi
    fullhrs = _miriad_f.jul2ut (jd) * 12 / pi

    hr = int (floor (fullhrs))
    mn = int (floor (60 * (fullhrs - hr)))
    sc = int (3600 * (fullhrs - hr - mn / 60.))

    return '%02d:%02d:%02d' % (hr, mn, sc)

def dateOrTimeToJD (calendar):
    """Return a full or offset Julian date parsed from the argument.
(An offset Julian date is between 0 and 1 and measures a time of day.
The anchor point to which the offset Julian date is relative to is
irrelevant to this function.) Acceptable input formats are:

  yymmmdd.dd (D)
  dd/mm/yy (F)
  [yymmmdd:][hh[:mm[:ss.s]]] (H)
  ccyy-mm-dd[Thh[:mm[:ss.ss]]] (T)
  dd-mm-ccyy

See the documentation to Miriad function DAYJUL for a more detailed
description of the parser behavior. The returned Julian date is of
moderate accuracy only, e.g. good to a few seconds (I think?)."""

    return _miriad_f.dayjul (calendar)

# Wrapper around NLLSQU, the non-linear least squares solver

def nlLeastSquares (guess, neqn, func, derivative=None,
                    maxIter=None, absCrit=None, relCrit=None,
                    stepSizes=None, allowFail=False):
    """\
Optimize parameters by performing a nonlinear least-squares fit.

:type guess: 1D ndarray
:arg guess: the initial guess of the parameters. The size of the
  array is used to determine the number of parameters, to which we
  refer as *nunk* below.
:arg int neqn: the number of equations -- usually, the number of data
  points you have. Should be at least *nunk*.
:arg callable func: a function evaluating the fit residuals. Prototype
  below.
:arg callable derivative: an optional function giving the derivative
  of func with regards to changes in the parameters. Prototype
  below. If unspecified, the derivative will be approximated by
  exploring values of *func*, and *stepSizes* below must be given.
:arg int/None maxIter: the maximum number of iterations to perform
  before giving up. An integer, or :const:`None`. If :const:`None`,
  maxIter is set to 200 times *nunk*. Defaults to :const:`None`.
:arg float/None absCrit: absolute termination criterion: iteration
  stops if sum(normResids**2) < criterion. If :const:`None`, set to
  ``neqn - nunk`` (i.e., reduced chi squared = 1). Default is
  :const:`None`.
:arg float/none relCrit: relative termination criterion: iteration
  stops if relCrit * sum(abs(params)) < sum (abs(dparams)). If
  :const:`None`, set to ``nunk * 1e-4``, i.e. explore until the
  parameters are constrained to about one in 10000 . Default is
  :const:`None`.
:type stepSizes: 1D ndarray
:arg stepSizes: if *derivative* isn't given, this should be a
  1D array of *nunk* parameters, giving the parameter step sizes
  to use when evaluating the derivative of *func* numerically. If
  *derivative* is given, the value is ignored.
:arg bool allowFail: if :const:`True`, return results even for fits
  that did not succeed. If :const:`False`, raise an exception in these
  cases.  It is better to choose better values for absCrit and relCrit
  than it is to set allowFail to :const:`True`.
:rtype: (int, 1D ndarray, 1D ndarray, float)
:returns: tuple of (*success*, *best*, *normResids*, *rchisq*),
  described below.

The argument *func* is a function taking two arguments, *params* and
*normResids*, and returning :const:`None`.

:type params: 1D ndarray
:arg params: the current guess of the parameters
:type normResids: 1D ndarray
:arg normResids: an output argument of size *neqn*.
  sum(normResids**2) is minimized by the solver. So-called because in
  the classic case, this variable is set to the normalized residuals::

    normResids[i] = (model (x[i], params) - data[i]) / sigma[i]

:returns: ignored

The optional argument *derivative* is a function taking two arguments,
*params* and *dfdx*, and returning :const:`None`.

:type params: 1D ndarray
:arg params: the current guess of the parameters.
:type dfdx: 2D ndarray
:arg dfdx: an output argument of shape (*nunk*, *neqn*). Should be
  filled with the derivative of *func* with regard to the parameters::

    dfdx[i,j] = d(normResids[j]) / d(params[i]) .

:returns: ignored

The return value is a tuple (*success*, *best*, *normResids*, *rchisq*),
with the following meanings:

* **success** -- an integer describing the outcome of the fit:

  * *0* -- fit succeeded; one of the convergence criteria was achieved.
  * *1* -- a singular matrix was encountered; unable to complete fit.
  * *2* -- maximum number of iterations completed before able to find
    a solution meeting either convergence criterion.
  * *3* -- failed to achieve a better chi-squared than on the previous
    iteration, and the convergence criteria were not met on the
    previous iteration. The convergence criteria may be too stringent,
    or the initial guess may be leading the solver into a local
    minimum too far from the correct solution.
* **best** -- a 1D array giving the best-fit parameter values found by the
  algorithm.
* **normResids** -- a 1D array giving the last-evaluated normalized residuals as
  described in the prototype of *func*.
* **rchisq** -- the reduced chi squared of the fit::

    rChiSq = sum (normResids**2) / (neqn - nunk)

Implemented using the Miriad function NLLSQU.
"""

    from _miriad_f import nllsqu
    arr = lambda shape: N.zeros (shape, dtype=N.float32, order='F')

    # Verify arguments

    guess = N.asarray (guess, dtype=N.float32, order='F')
    if guess.ndim != 1:
        raise ValueError ('Least squares guess must be 1-dimensional')
    nunk = guess.size

    neqn = int (neqn)
    if neqn < nunk:
        raise RuntimeError ('Not enough equations to solve problem')

    if not callable (func):
        raise TypeError ('"func" is not callable?!')

    haveDer = derivative is not None

    if haveDer:
        if not callable (derivative):
            raise TypeError ('"derivative" is not callable?!')
        stepSizes = arr ((nunk, ))
    else:
        def derivative (params, dfdx):
            raise NotImplementedError ()
        stepSizes = N.asarray (stepSizes)
        if stepSizes.shape != (nunk, ):
            raise ValueError ('"stepSizes" array is wrong shape!')

    if maxIter is None:
        maxIter = 200 * nunk
    else:
        maxIter = int (maxIter)
        if maxIter <= 0: raise ValueError ('"maxIter" must be positive')

    if absCrit is None:
        absCrit = neqn - nunk
    else:
        absCrit = float (absCrit)
        if absCrit <= 0: raise ValueError ('"criterion" must be positive')

    if relCrit is None:
        #relCrit = 5 * nunk * N.finfo (N.float32).eps
        relCrit = nunk * 1e-4
    else:
        relCrit = float (relCrit)
        if relCrit <= 0: raise ValueError ('"relCrit" must be positive')

    allowFail = bool (allowFail)

    # Construct scratch arrays

    normResids = arr ((neqn, ))
    normResidsPrime = arr ((neqn, ))
    dx = arr ((nunk, ))
    dfdx = arr ((nunk, neqn))
    aa = arr ((nunk, nunk))

    # Do it!

    success = nllsqu (guess, stepSizes, maxIter, absCrit, relCrit,
                      haveDer, func, derivative, normResids,
                      normResidsPrime, dx, dfdx, aa)

    if success != 0 and not allowFail:
        msg = ('Nonlinear least-squares fit failed: success = %d '
               '(see docstring for explanations)' % success)
        raise RuntimeError (msg)

    # Return useful results

    rChiSq = (normResids**2).sum () / (neqn - nunk)
    return success, guess, normResids, rChiSq

# Wrapper around LLSQU, the linear least-squares solver

def linLeastSquares (coeffs, vals):
    """\
Solve for parameters in a linear least-squares problem.  The problem
has *neqn* equations used to solve for *nunk* unknown parameters.

:type coeffs: 2D ndarray
:arg coeffs: an array of shape (*nunk*, *neqn*). With *vals*, defines the
  linear equations specifying the problem.
:type vals: 1D ndarray
:arg vals: data array of size *neqn*.
:rtype: 1D ndarray
:returns: an array of size *nunk* giving the parameters that yield the
  least-squares fit to the given equation.

The linear least squares problem is that of finding best solution (in
a least-squares sense), *retval*, such that ``coeffs.T * retval =
vals``, using matrix notation. This is the same as solving *neqn*
linear equations simultaneously, where the i'th equation is::

  vals[i] = coeffs[0,i] * retval[0] + ... + coeffs[nunk-1,i] * retval[nunk-1]
"""

    from _miriad_f import llsqu

    coeffs = N.asarray (coeffs, dtype=N.float32, order='F')
    if coeffs.ndim != 2:
        raise ValueError ('"coeffs" must be a 2D array.')

    nunk, neqn = coeffs.shape

    if neqn < nunk:
        raise RuntimeError ('Not enough equations to solve problem')

    vals = N.asarray (vals, dtype=N.float32, order='F')
    if vals.ndim != 1:
        raise ValueError ('"vals" must be a 1D array.')
    if vals.size != neqn:
        raise ValueError ('"vals" must be of size neqn')

    b = N.ndarray ((nunk, nunk), dtype=N.float32, order='F')
    pivot = N.ndarray ((nunk, ), dtype=N.intc, order='F')

    # Do it!

    c, success = llsqu (vals, coeffs, b, pivot)

    if success != 0:
        raise RuntimeError ('Linear least-squares fit failed: singular matrix')

    return c


# Coordinate foo

def precess (jd1, ra1, dec1, jd2):
    """Precess a coordinate from one Julian Date to another.

:arg double jd1: the JD of the input coordinates
:arg double ra1: the input RA in radians
:arg double dec1: the input dec in radians
:arg double jd2: the JD to precess to
:rtype: (double, double)
:returns: (ra2, dec2), the precessed equatorial coordinates, both in radians

Claimed accuracy is 0.3 arcsec over 50 years. Based on the algorithm
described in the Explanatory Supplement to the Astronomical Almanac,
1993, pp 105-106. Does not account for atmospheric refraction,
nutation, aberration, or gravitational deflection.
"""
    return _miriad_f.precess (jd1, ra1, dec1, jd2)

def equToHorizon (ra, dec, lst, lat):
    """Convert equatorial coordinates to horizon coordinates.

:arg double ra: the apparent RA in radians
:arg double dec: the apparent dec in radians
:arg double lst: the local sidereal time in radians
:arg double lat: the geodetic latitude of the observatory in radians
:rtype: (double, double)
:returns: (az, el), both in radians
"""
    return _miriad_f.azel (ra, dec, lst, lat)


def horizonToEqu (az, el, lst, lat):
    """Convert horizon coordinates to equatorial coordinates.

:arg double az: the elevation coordinate in radians
:arg double el: the azimuth coordinate in radians
:arg double lst: the local sidereal time in radians
:arg double lat: the geodetic latitude of the observatory in radians
:rtype: (double, double)
:returns: (ra, dec), apparent equatorial coordinates, both in radians
"""
    # Miriad does not provide a mirror to azel() but it's easy to
    # implement manually
    from numpy import arcsin, arctan2, cos, sin, pi
    dec = arcsin (sin (lat) * sin (el) + cos (lat) * cos (el) * cos (az))
    ha = arctan2 (-sin (az) * cos (el),
                   cos (lat) * sin (el) - sin (lat) * cos (el) * cos (az))
    ra = (lst - ha) % (2 * pi)
    return ra, dec


# Spheroidal convolution functions

def sphGridFunc (nsamp, width, alpha):
    """Compute a spheroidal convolutional gridding function.

:arg int nsamp: the number of points at which to sample the function.
  In MIRIAD, *nsamp* is always 2047.
:arg int width: the width of the correction function, in pixels;
  must be 4, 5, or 6. In MIRIAD, *width* is always 6.
:arg float alpha: spheroidal parameter; must be between 0 and 2.25,
  and will be rounded to the nearest half-integral value (i.e., 0,
  0.5, 1, 1.5, or 2). In MIRIAD, *alpha* is always 1.0.
:rtype: *nsamp*-element real ndarray
:returns: the tabulated function

The spheroidal convolutional gridding function is used to put
visibility measurements on a regular grid so that a dirty map can be
made using a fast Fourier transform (FFT) algorithm. A thorough
discussion of the topic is beyond the scope of this docstring. See
Chapter 10 of Thompson, Moran & Swenson or `Lecture 7 of Synthesis
Imaging in Radio Astronomy II
<http://adsabs.harvard.edu/abs/1999ASPC..180..127B>`_.

In MIRIAD's standard usage of this function, all of the arguments are
fixed. You should probably use the MIRIAD values (*nsamp* = 2047,
*width* = 6, *alpha* = 1.0) unless you really know what you're
doing. I don't know how *alpha* affects the spheroidal function used
but it's probably not hard to look up.

Indices into the tabulated array are related to pixel offsets by the
expression ``index = (nsamp // width) * pixeloffset + nsamp //
2``. Using the standard MIRIAD parameters, this is ``index = 341 *
pixeloffset + 1023``.
"""
    return _miriad_f.gcffun ('spheroidal', nsamp, width, alpha)


def sphCorrFunc (axislen, width, alpha):
    """Compute a spheroidal gridding correction function.

:arg int axislen: length of image axis to be corrected, in pixels
:arg int width: width of gridding function; must be 4, 5, or 6
:arg float alpha: spheroidal parameter; must be 0, 0.5, 1, 1.5, or 2.
:rtype: *axislen*-element real ndarray
:returns: the tabulated function

I don't quite understand the details of this function, but it's used
to correct the dirty map for the effects of the spheroidal function
used to put visibilities onto a grid before FFTing int the mapping
process. See the usage of *xcorr* and *ycorr* in
``mapper.for:MapFFT2``.  The correction function is separable in
*u*/*v* or *l*/*m* so that there's one for each image axis, which is
why *axislen* is a single integer in this function. The output image
is divided by the correction functions, scaled by their central
pixels. The overall profile of the correction function is similar to
that of the spheroidal convolution function itself.

In MIRIAD, *width* is always 6 and *alpha* is always 1.0. I don't know
how *alpha* affects the spheroidal function used but it's probably not
hard to look up.
"""
    return _miriad_f.corrfun ('spheroidal', axislen, width, alpha)
