"""Low-level Miriad routines.

The exposed routines mirror the Miriad Fortran and C API as
closely as possible, with little or no glue on top of them.
Should be avoided in favor of higher-level, more Pythonic
APIs, if possible.
"""

import _uvio, _mirgood
import numpy as _N

# Migrate functions from _mirugly to _mirgood as their binding
# into python is verified.

from _uvio import *
from _mirgood import *

# Overwite a few bound methods in a more sane manner.

def bug (sev, msg):
    """Signal that a bug has occurred, or invalid input has been
    passed to your task. Just raises MiriadError with the given
    message if sev is 'f'.

    In hand-written code, you should just raise MiriadError yourself,
    but this routine allows more direct mapping of existing Fortran
    code to Python."""
    
    if sev == 'f':
        raise MiriadError (msg)
    else:
        from warnings import warn
        warn ('MIRIAD warning (severity %c): %s' % (sev, msg), UserWarning, 2)

def julday (julian, form):
    """Wrapper for julday. Form is one of 'D', 'F', 'H', 'T', or 'V'."""

    calday = _N.chararray (120)
    _mirgood.julday (julian, form, calday)

    for i in xrange (0, calday.size):
        if calday[i] == '': return calday[0:i].tostring ()
    
    raise MiriadError ('Output from julday exceeded buffer size')

def hisinput (tno, name, args=None):
    """Wrapper for hisinput. The Fortran implementation is not usable
    because it relies on iargc() and getarg(), which may not contain
    the arguments we are actually using."""

    if args is None: args = _sys.argv

    # I can't figure out what all the parsing of name is supposed
    # to accomplish. Ignore it all.
    
    prefix = name.upper () + ': '
    
    julian = _mirgood.todayjul ()
    file = julday (julian, 'T')
    _uvio.hiswrite (tno, prefix + 'Executed on: ' + file)
    _uvio.hiswrite (tno, prefix + 'Command line inputs follow:')
    
    prefix += '  '
    dofile = False

    for arg in args[1:]:
        if dofile:
            f = file (arg, 'r')

            for l in f:
                _uvio.hiswrite (tno, prefix + l)

            f.close ()
            dofile = False
        else:
            if arg == '-f': dofile = True
            else: _uvio.hiswrite (tno, prefix + arg)

def uvdatgta (obj):
    """Wrapper for uvdatgta that handles Fortran text inputs and outputs
    correctly... I think. Ugly."""

    aval = _N.chararray (120)
    _mirgood.uvdatgta (obj, aval)

    # Better way?

    for i in xrange (0, aval.size):
        if aval[i] == '': return aval[0:i].tostring ()
    
    raise MiriadError ('Output from uvdatgta exceeded buffer size')

def mkeyf (key, nmax, bufsz=120):
    """Wrapper for mkeyf with extra layer of string sanity."""

    value = _N.chararray ((nmax, bufsz))
    n = _mirgood.mkeyf (key, value, nmax)

    # Can't find a better way to make this work. Sigh.
    
    ret = []

    for i in xrange (0, n):
        s = ''
        for j in xrange (0, bufsz):
            if value[i,j] == '': break
            s += value[i,j]

        ret.append (s)

    return ret

def mkeya (key, nmax, bufsz=120):
    """Wrapper for mkeya with extra layer of string sanity."""

    value = _N.chararray ((nmax, bufsz))
    n = _mirgood.mkeya (key, value, nmax)

    # Can't find a better way to make this work. Sigh.
    
    ret = []

    for i in xrange (0, n):
        s = ''
        for j in xrange (0, bufsz):
            if value[i,j] == '': break
            s += value[i,j]

        ret.append (s)

    return ret

def keymatch (key, types, maxout):
    """Wrapper for keymatch with extra layer of string sanity."""

    ml = 0

    for t in types:
        ml = max (ml, len (str (t)))

    tarr = []

    for t in types:
        s = str (t)
        tarr.append (s.ljust (ml, ' '))

    out = _N.chararray ((maxout, ml))
    # Not sure why f2py thinks maxout is optional here.
    nout = _mirgood.keymatch (key, types, out, len (types), maxout)

    # Can't find a better way to make this work. Sigh.
    
    ret = []

    for i in xrange (0, nout):
        s = ''
        for j in xrange (0, ml):
            if out[i,j] == '': break
            s += out[i,j]

        ret.append (s)

    return ret
