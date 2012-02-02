"""Python-2.4-compatible implementations of a few functions in mirtask.uvdat.
See _uvdat_compat_default.py for the reference implementations."""

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

from mirtask import _miriad_f

def _inputSets (UVDatDataSet):
    """Generate a sequence of DataSet objects representing the
visdata input sets."""
    ds = None
    try:
        while True:
            if ds is not None and ds.isOpen (): ds.close ()
            (status, tin) = _miriad_f.uvdatopn ()
            if not status: break
            ds = UVDatDataSet (tin)
            yield ds
    except:
        if ds is not None and ds.isOpen (): ds.close ()
    else:
        if ds is not None and ds.isOpen (): ds.close ()
    if ds is None:
        raise RuntimeError ('No input UV data sets?')


def _read_gen (saveFlags, UVDatDataSet, maxchan):
    from mirtask._miriad_f import uvdatopn, uvdatrd
    from numpy import zeros, double, complex64, int32
    inp = None
    preamble = zeros (5, dtype=double)
    data = zeros (maxchan, dtype=complex64)
    flags = zeros (maxchan, dtype=int32)
    try:
        if saveFlags:
            while True:
                if inp is not None and inp.isOpen ():
                    inp.close ()
                (status, tin) = uvdatopn ()
                if not status:
                    break
                inp = UVDatDataSet (tin)
                rewrite = inp.rewriteFlags
                while True:
                    nread = uvdatrd (preamble, data, flags, maxchan)
                    if nread == 0:
                        break
                    f = flags[:nread]
                    yield inp, preamble, data[:nread], f
                    rewrite (f)
        else:
            while True:
                if inp is not None and inp.isOpen ():
                    inp.close ()
                (status, tin) = uvdatopn ()
                if not status:
                    break
                inp = UVDatDataSet (tin)
                while True:
                    nread = uvdatrd (preamble, data, flags, maxchan)
                    if nread == 0:
                        break
                    yield inp, preamble, data[:nread], flags[:nread]
    except:
        if inp is not None and inp.isOpen ():
            inp.close ()
    else:
        if inp is not None and inp.isOpen ():
            inp.close ()
