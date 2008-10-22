"""Miscellaneous utility MIRIAD subroutines."""

import lowlevel as ll
import numpy as N

# Banner printing (and Id string decoding)

def printBannerSvn (name, desc, idstr):
    """Print a banner string containing the name of a task, its
    description, and versioning information extracted from a
    Subversion ID string. The banner string is returned as well."""

    file, rev, date, time, user = idstr[5:-2].split ()
    
    b = '%s: %s (Python, SVN r%s, modified %s %s)' % (name.upper (), desc,
                                                      rev, date, time)
    print b
    return b

# Baseline-related stuff

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return ll.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return ll.antbas (ant1, ant2)

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
# individual feed can respond to. I am pretty sure that all or some of
# the I, Q, U, V values given below are inappropriate, but I do
# think MIRIAD can work with UV datasets given in Stokes parameters,
# so for completeness we include them here, even if there can't be
# a physical feed that corresponds to such an entity.

FPOL_X = 0
FPOL_Y = 1
FPOL_R = 2
FPOL_L = 3
FPOL_I = 4
FPOL_Q = 5
FPOL_U = 6
FPOL_V = 7

fPolNames = 'XYRLIQUV'

# This table helps split a MIRIAD/FITS pol code into a pair of f-pol values.
# The pair is packed into 8 bits, the upper 3 being for the left pol
# and the lower 4 being for the right. If the high bit is 1, the pol code
# cannot legally be split. An offset of 8 is required because the pol codes range
# from -8 to +6

_polToFPol = [0x10, 0x01, 0x11, 0x00, # YX XY YY XX
              0x32, 0x23, 0x33, 0x22, # LR RL LL RR
              0x44, # II
              0x80, 0x80, 0x80, 0x80, # I Q U V
              0x55, 0x66] # QQ UU

# This table performs the reverse mapping, with index being the two
# f-pol values packed into four bits each. A value of 99 indicates
# an illegal pairing.

_fpolToPol = N.ndarray (128, dtype=N.int)
_fpolToPol.fill (99)
_fpolToPol[0x00] = POL_XX
_fpolToPol[0x01] = POL_XY
_fpolToPol[0x10] = POL_YX
_fpolToPol[0x11] = POL_YY
_fpolToPol[0x22] = POL_RR
_fpolToPol[0x23] = POL_RL
_fpolToPol[0x32] = POL_LR
_fpolToPol[0x33] = POL_LL
_fpolToPol[0x44] = POL_II
_fpolToPol[0x55] = POL_QQ
_fpolToPol[0x66] = POL_UU

# A "portable antpol" (PAP) is a >=8-bit integer identifying an
# antenna/feed-polarization combination. It can be decoded without any
# external information.  The translation between PAP and M,FP is:
#
#   PAP = (M - 1) << 3 + FP
#
# or
#
#   M = PAP >> 3 + 1
#   P = PAP & 0x7
#
# Note that arbitrarily-large antenna numbers can be encoded
# if sufficiently many bits are used to store the PAP.

def fmtPAP (pap):
    m = (pap >> 3) + 1
    fp = pap & 0x7
    return '%d%c' % (m, fPolNames[fp])

def papAnt (pap):
    return (pap >> 3) + 1

def papFPol (pap):
    return pap & 0x7

def antpol2pap (m, fpol):
    return ((m - 1) << 3) + fpol

# Routines for dealing with a tuple of two PAPs, which can define
# a BL-pol.

def fmtPAPs (pair):
    pap1, pap2 = pair

    m1 = (pap1 >> 3) + 1
    fp1 = pap1 & 0x7
    m2 = (pap2 >> 3) + 1
    fp2 = pap2 & 0x7

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])

def paps2ants (pair):
    """Converts a tuple of two PAPs into a tuple of (ant1, ant2, pol)."""

    pap1, pap2 = pair
    m1 = (pap1 >> 3) + 1
    m2 = (pap2 >> 3) + 1
    assert m1 <= m2, 'Illegal PAP value: m1 > m2'

    idx = ((pap1 & 0x7) << 4) + (pap2 & 0x7)
    pol = _fpolToPol[idx]
    assert pol != 99, 'PAP value represents illegal polarization pairing'

    return (m1, m2, pol)

def paps2blpol (pair):
    """Converts a tuple of two PAPs into a tuple of (bl, pol) where
'bl' is the MIRIAD-encoded baseline number."""

    m1, m2, pol = paps2ants (pair)
    return (encodeBaseline (m1, m2), pol)

def mir2paps (inp, preamble):
    """Uses a UV dataset and a preamble array to return a tuple of
(pap1, pap2)."""

    pol = inp.getVarInt ('pol')
    fps = _polToFPol[pol + 8]
    assert (fps & 0x80) == 0, 'Un-breakable polarization code'

    m1, m2 = ll.basants (preamble[4], True)

    pap1 = ((m1 - 1) << 3) + ((fps >> 4) & 0x07)
    pap2 = ((m2 - 1) << 3) + (fps & 0x07)

    return pap1, pap2

def papsAreInten (pair):
    pap1, pap2 = pair
    return pap1 & 0x7 == pap2 & 0x7

# A "32-bit portable basepol" (PBP32) is a >=32-bit integer identifying a baseline
# consisting of two portable antpols. It can be decoded without
# any external information. The translation between PAP and M1,M2,FP1,FP2 is:
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
# to 4096 antennas. This should be sufficient for most applications.

def fmtPBP (pbp32):
    m1 = ((pbp32 >> 19) & 0x1FFF) + 1
    fp1 = (pbp32 >> 16) & 0x7
    m2 = ((pbp32 >> 3) & 0x1FFF) + 1
    fp2 = pbp32 & 0x7

    assert m2 >= m1, 'Illegal PBP32 in fmtPBP: m1 > m2'

    return '%d%c-%d%c' % (m1, fPolNames[fp1], m2, fPolNames[fp2])

def mir2pbp (inp, preamble):
    pol = inp.getVarInt ('pol')
    fps = _polToFPol[pol + 8]
    assert (fps & 0x80) == 0, 'Un-breakable polarization code'

    m1, m2 = ll.basants (preamble[4], True)
    
    return ((m1 - 1) << 19) + ((fps & 0x70) << 12) + ((m2 - 1) << 3) \
        + (fps & 0x7)

def pbp2paps (pbp32):
    return (pbp32 >> 16, pbp32 & 0xFFFF)

def paps2pbp (pair):
    pap1, pap2 = pair

    assert (pap1 >> 3) <= (pap2 >> 3), 'Illegal baseline pairing: m1 > m2'
    assert pap2 <= 0xFFFF, 'Antnum too high to be encoded in PBP32'

    return (pap1 << 16) + (pap2 & 0xFFFF)

def pbpIsInten (pbp32):
    return ((pbp32 >> 16) & 0x7) == pbp32 & 0x7

# FIXME: following not implemented. Not sure if it is actually
# necessary since in practice we condense down lists of basepols into
# customized arrays, since a basepol might be missing.

# An "antpol" (AP) encodes the same information as a PAP, but can only
# encode two possible polarizations. This means that external
# information is needed to decode an AP, but that it can be used to
# index into arrays efficiently (assuming a full-pol correlator
# that doesn't skip many MIRIAD antenna numbers). The assumption is that
# a set of antpols will include FPs of X & Y or R & L. In the former case
# the "reference feed polarzation" (RFP) is X; in the latter it is R.
#
# The translation between AP, RFP and M, FP is:
#
#  AP = (M - 1) << 1 + (FP - RFP)
#
# or
#
#  M = (AP >> 1) + 1
#  FP = (AP & 0x1) + RFP



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
