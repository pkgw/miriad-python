"""A few functions in mirtask.uvdat that have compatibility issues
with Python 2.4 that raise SyntaxErrors. You can't catch them in
the module itself, but you can catch them on import, so this allows
us to use the ideal functions if possible but fall back if necessary."""

import lowlevel as ll

def _inputSets (UVDatDataSet):
    """Generate a sequence of DataSet objects representing the
visdata input sets."""

    ds = None

    try:
        while True:
            if ds is not None and ds.isOpen ():
                ds.close ()

            (status, tin) = ll.uvdatopn ()

            if not status:
                break

            ds = UVDatDataSet (tin)
            yield ds
    finally:
        if ds is not None and ds.isOpen ():
            ds.close ()

    if ds is None:
        raise RuntimeError ('No input UV data sets?')


def _read_gen (saveFlags, UVDatDataSet, maxchan):
    from lowlevel import uvdatopn, uvdatrd
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
    finally:
        if inp is not None and inp.isOpen ():
            inp.close ()
