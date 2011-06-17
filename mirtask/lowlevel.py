'''mirtask.lowlevel - low-level exposure of MIRIAD subroutine APIs'''

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

import _miriad_c, _miriad_f
import numpy as N

from _miriad_c import *
from _miriad_f import *

# Overwite a few bound methods in a more sane manner.

def julday (julian, form):
    """Wrapper for julday. Form is one of 'D', 'F', 'H', 'T', or 'V'."""

    calday = N.chararray (120)
    _miriad_f.julday (julian, form, calday)

    for i in xrange (0, calday.size):
        if calday[i] == '': return calday[0:i].tostring ()
    
    raise MiriadError ('Output from julday exceeded buffer size')


def hisinput (tno, name, args=None):
    """Wrapper for hisinput. The Fortran implementation is not usable
    because it relies on iargc() and getarg(), which may not contain
    the arguments we are actually using."""

    if args is None:
        import sys
        args = sys.argv

    # I can't figure out what all the parsing of name is supposed
    # to accomplish. Ignore it all.
    
    prefix = name.upper () + ': '
    
    julian = _miriad_f.todayjul ()
    file = julday (julian, 'T')
    _miriad_c.hiswrite (tno, prefix + 'Executed on: ' + file)
    _miriad_c.hiswrite (tno, prefix + 'Command line inputs follow:')
    
    prefix += '  '
    dofile = False

    for arg in args[1:]:
        if dofile:
            f = file (arg, 'r')

            for l in f:
                _miriad_c.hiswrite (tno, prefix + l)

            f.close ()
            dofile = False
        else:
            if arg == '-f': dofile = True
            else: _miriad_c.hiswrite (tno, prefix + arg)


def uvdatgta (obj):
    """Wrapper for uvdatgta that handles Fortran text inputs and outputs
    correctly... I think. Ugly."""

    aval = N.chararray (120)
    _miriad_f.uvdatgta (obj, aval)

    # Better way?

    for i in xrange (0, aval.size):
        if aval[i] == '': return aval[0:i].tostring ()
    
    raise MiriadError ('Output from uvdatgta exceeded buffer size')


def uvinfo_line (tno):
    info = N.zeros (6, dtype=N.double)
    _miriad_c.uvinfo (tno, 'line', info)
    info = info.astype (N.int)
    # Convert Fortran 1-based index to 0-based
    info[2] -= 1
    info[5] -= 1
    return info


def uvinfo_visno (tno):
    info = N.zeros (1, dtype=N.double)
    _miriad_c.uvinfo (tno, 'visno', info)
    # Convert Fortran 1-based index to 0-based
    return int (info[0]) - 1


def mkeyf (key, nmax, bufsz=120):
    """Wrapper for mkeyf with extra layer of string sanity."""

    value = N.chararray ((nmax, bufsz))
    n = _miriad_f.mkeyf (key, value, nmax)

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

    value = N.chararray ((nmax, bufsz))
    n = _miriad_f.mkeya (key, value, nmax)

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

    out = N.chararray ((maxout, ml))
    # Not sure why f2py thinks maxout is optional here.
    nout = _miriad_f.keymatch (key, tarr, out, len (types), maxout)

    # Can't find a better way to make this work. Sigh.
    
    ret = []

    for i in xrange (0, nout):
        s = ''
        for j in xrange (0, ml):
            if out[i,j] == '': break
            s += out[i,j]

        ret.append (s)

    return ret
