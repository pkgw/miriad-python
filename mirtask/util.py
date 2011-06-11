'''mirtask.util - miscellaneous utility subroutines for MIRIAD tasks'''

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

import lowlevel as ll
import numpy as N

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

    b = '%s: %s (Python, SVN r%s, modified %s %s)' % (name.upper (), desc,
                                                      rev, date, time)
    print b
    return b


def die (format, *args):
    raise SystemExit ('Error: ' + (format % args))


# Baseline-related stuff

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return ll.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return ll.antbas (ant1, ant2)

# Linetype constants. From subs/uvio.c

LINETYPE_NONE = 0
LINETYPE_CHANNEL = 1
LINETYPE_WIDE = 2
LINETYPE_VELOCITY = 3
LINETYPE_FELOCITY = 4

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
    
    return ll.polspara (polnum)

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
        raise Exception ('Text does not encode a valid AP: ' + text)

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

    pol = inp.getVarFirstInt ('pol', POL_I)
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
        raise ValueError ('text does not encode a basepol: ' + text)

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
    fps = _polToFPol[handle.getVarFirstInt ('pol', POL_I) + 8]
    m1, m2 = ll.basants (preamble[4], True)

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

def jdToFull (jd):
    """Return a string representing the given Julian date as date
    and time of the form 'YYMMDD:HH:MM:SS.S'."""
    return ll.julday (jd, 'H')

def jdToPartial (jd):
    """Return a string representing the time-of-day portion of the
    given Julian date in the form 'HH:MM:SS'. Obviously, this loses
    precision from the JD representation."""

    # smauvplt does the hr/min/sec breakdown manually so I shall
    # do the same except maybe a bit better because I use jul2ut.

    from math import floor, pi
    fullhrs = ll.jul2ut (jd) * 12 / pi

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

    return ll.dayjul (calendar)

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

    from _mirgood import nllsqu
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

    from _mirgood import llsqu
    
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
    pivot = N.ndarray ((nunk, ), dtype=N.int32, order='F')

    # Do it!
    
    c, success = llsqu (vals, coeffs, b, pivot)

    if success != 0:
        raise RuntimeError ('Linear least-squares fit failed: singular matrix')

    return c


# Coordinate foo

def precess (jd1, ra1, dec1, jd2):
    """Precess a coordinate from one Julian Date to another.

Arguments:
jd1  - The JD of the input coordinates
ra1  - The input RA in radians
dec1 - The input dec in radians
jd2  - The JD to precess to

Returns: (ra2, dec2), where
ra2  - The output RA in radians
dec2 - The output dec in radians

Claimed accuracy is 0.3 arcsec over 50 years. Based on the
algorithm described in the Explanatory Supplement to the
Astronomical Almanac, 1993, pp 105-106. Does not account
for atmospheric refraction, nutation, aberration, or
gravitational deflection.
"""
    return ll.precess (jd1, ra1, dec1, jd2)

def equToHorizon (ra, dec, lst, lat):
    """Convert equatorial coordinates to horizon coordinates.

Arguments:
ra  - The apparent RA in radians
dec - The apparent dec in radians
lst - The local sidereal time in radians
lat - The geodetic latitude of the observatory in radians

Returns: (az, el), where
az - The azimuth coordinate in radians
el - The elevation coordinate in radians

If available, this should be superseded by the RALP/NOVAS conversion
function, which I suspect will be superior to the MIRIAD function.
"""
    return ll.azel (ra, dec, lst, lat)
