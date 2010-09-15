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
            if ds is not None and ds.isOpen (): ds.close ()

            (status, tin) = ll.uvdatopn ()

            if not status:
                break

            ds = UVDatDataSet (tin)
            yield ds
    finally:
        # In case of exception, clean up after ourselves.
        if ds is not None and ds.isOpen (): ds.close ()

    if ds is None:
        raise RuntimeError ('No input UV data sets?')


def _readFileLowlevel_gen (inp, saveFlags, uvdatrd, preamble,
                           data, flags, maxchan, rewrite):
    try:
        if saveFlags:
            while True:
                nread = uvdatrd (preamble, data, flags, maxchan)
                if nread == 0: break

                f = flags[:nread]
                yield inp, preamble, data[:nread], f
                rewrite (f)
        else:
            while True:
                nread = uvdatrd (preamble, data, flags, maxchan)
                if nread == 0: break

                yield inp, preamble, data[:nread], flags[:nread]
    finally:
        if inp.isOpen (): inp.close ()
