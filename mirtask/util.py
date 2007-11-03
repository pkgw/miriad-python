"""Miscellaneous utility MIRIAD subroutines."""

import lowlevel as ll

def decodeBaseline (encoded, check=True):
    """Decode an encoded baseline double into two antenna numbers."""
    return ll.basants (encoded, check)

def encodeBaseline (ant1, ant2):
    """Encode a pair of antenna numbers into one baseline number
suitable for use in UV data preambles."""
    return ll.antbas (ant1, ant2)

def genBaselineIndexMapping (ants, includeAutos=False):
    """Generate a sequence of tuples relating a list of baselines
    (generated from a list of antennas) to a sequence of integers.
    This allows space-efficient storage of per-baseline data, given
    a known list of antennas.

    Generates a sequence of (ant1, ant2, index) associations. ant1
    will be less than ant2 if includeAutos is False, and less than
    or equal to ant2 if includeAutos is True.

    Parameters:

    ants         - A list of antenna numbers

    includeAutos - If True, the sequence will include autocorrelation
                   baselines (e.g., (1, 1, [index])). If False, these
                   will be skipped. Defaults to False.
    """

    ants = list (ants)
    ants.sort ()

    c = 0

    if includeAutos:
        for i in xrange (0, len (ants)):
            for j in xrange (0, i+1):
                yield (ants[j], ants[i], c)
                c += 1
    else:
        for i in xrange (0, len (ants)):
            for j in xrange (0, i):
                yield (ants[j], ants[i], c)
                c += 1

def baselineIndexMap (ants, includeAutos=False):
    """Return a hashtable mapping a baseline tuple (ant1, ant2) to
    an index for efficient storage of per-baseline information.
    That is:

    >>> v = baselineIndexMap ([3, 5, 11])
    >>> v[(3,5)]
    0 # maybe; order of indices not guaranteed
    >>> v[(3,3)] # -> KeyError since includeAutos was false.
    >>> len(v)
    3 # = 3 * (3 - 1) / 2
    >>> v = baselineIndexMap ([3, 5, 11], includeAutos=True)
    >>> v[(3,5)]
    1 # maybe; order of indices not guaranteed
    >>> v[(3,3)]
    0 # maybe; order of indices not guaranteed
    >>> len(v)
    6 # = 3 * (3 + 1) / 2
    """

    res = {}

    for (ant1, ant2, idx) in genBaselineIndexMapping (ants, includeAutos):
        res[(ant1, ant2)] = idx

    return res

def indexBaselineMap (ants, includeAutos=False):
    """Return a hashtable mapping an index into a baseline tuple
    (ant1, ant2) for efficient storage of per-baseline information.
    That is:

    >>> v = indexBaselineMap ([3, 5, 11])
    >>> v[0]
    (3, 5) #maybe; order of indices not guaranteed
    >>> v[1]
    (3, 11) # maybe
    >>> len(v)
    3 # = 3 * (3 - 1) / 2
    >>> v = indexBaselineMap ([3, 5, 11], includeAutos=True)
    >>> v[0]
    (3, 3) #maybe; order of indices not guaranteed
    >>> v[1]
    (3, 5) # maybe
    >>> len(v)
    6 # = 3 * (3 + 1) / 2
    """

    res = {}

    for (ant1, ant2, idx) in genBaselineIndexMapping (ants, includeAutos):
        res[idx] = (ant1, ant2)

    return res

def encodedBaselineIndexMap (ants, includeAutos=False):
    """Return a hashtable mapping a MIRIAD-encoded baseline value to
    an index for efficient storage of per-baseline information.
    That is:

    >>> v = encodedBaselineIndexMap ([3, 5, 11])
    >>> v[773.0] # = encoded representation of (3, 5) baseline
    0 # maybe; order of indices not guaranteed
    >>> v[771.0] # = encoded representation of (3, 3) baseline
    -> KeyError # since includeAutos was false.
    >>> v = encodedBaselineIndexMap ([3, 5, 11], includeAutos=True)
    >>> v[773.0]
    1 # maybe; order of indices not guaranteed
    >>> v[771.0]
    0 # maybe; order of indices not guaranteed
    """

    res = {}

    for (ant1, ant2, idx) in genBaselineIndexMapping (ants, includeAutos):
        enc = encodeBaseline (ant1, ant2)
        res[enc] = idx

    return res

def indexEncodedBaselineMap (ants, includeAutos=False):
    """Return a hashtable mapping an index directly into a
    MIRIAD-encoded baseline value. That is:

    >>> v = indexEncodedBaselineMap ([3, 5, 11])
    >>> v[0]
    773.0 # maybe; order of indices not guaranteed;
          # = encoding of (3, 5)
    >>> v[1]
    779.0 # maybe; = encoding of (3, 11)
    >>> len(v)
    3 # = 3 * (3 - 1) / 2
    >>> v = indexEncodedBaselineMap ([3, 5, 11], includeAutos=True)
    >>> v[0]
    771.0 # maybe; order of indices not guaranteed
          # = encoding of (3, 3)
    >>> v[1]
    773.0 # maybe
    >>> len(v)
    6 # = 3 * (3 + 1) / 2
    """

    res = {}

    for (ant1, ant2, idx) in genBaselineIndexMapping (ants, includeAutos):
        enc = encodeBaseline (ant1, ant2)
        res[idx] = enc

    return res

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
        if name == polname: return num

    raise Exception ('Unknown polarization name \'%s\'' % polname)

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
