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
