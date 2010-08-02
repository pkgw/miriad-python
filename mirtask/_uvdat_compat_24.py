"""Python-2.4-compatible implementations of a few functions in mirtask.uvdat.
See _uvdat_compat_default.py for the reference implementations."""

import lowlevel as ll

def _inputSets (UVDatDataSet):
    """Generate a sequence of DataSet objects representing the
visdata input sets."""
    ds = None
    try:
        while True:
            if ds is not None and ds.isOpen (): ds.close ()
            (status, tin) = ll.uvdatopn ()
            if not status: break
            ds = UVDatDataSet (tin)
            yield ds
    except:
        if ds is not None and ds.isOpen (): ds.close ()
    else:
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
                yield inp, preamble, data, flags, nread
                rewrite (flags)
        else:
            while True:
                nread = uvdatrd (preamble, data, flags, maxchan)
                if nread == 0: break
                yield inp, preamble, data, flags, nread
    except:
        if inp.isOpen (): inp.close ()
    else:
        if inp.isOpen (): inp.close ()
