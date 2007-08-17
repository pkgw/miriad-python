"""Python wrappers for the uvdat* routines, a standardized way of accessing
UV data for Miriad tasks. Not implemented as an object, because the uvdat
routines maintain state within the Miriad libraries.
"""

import lowlevel as ll
import numpy as N
from mirtask import MiriadError, UVDataSet

__all__ = []

def init (flags, keyword='vis'):
    """Initialize standard UV data reading subsystem. Parameters:

flags - A sequence of characters giving options to the UV reading
subsystem. Possible contents are:

  r - Get a reference linetype specification via the 'ref' keyword
  s - Get Stokes parameters / polarizations via the 'stokes' keyword
  d - Perform input selection via the 'select' keyword
  l - Get a data linetype specification via the 'line' keyword
  p - Apply planet rotation and scaling
  w - Return U and V values in wavelengths
  1 - Default number of channels is 1
  x - Data must be cross-correlation data
  a - Data must be auto-correlation data
  b - Input must be a single file
  c - Apply gain/phase and delay corrections
  e - Apply polarization leakage corrections
  f - Apply bandpass corrections
  3 - Always return a 5-element 'preamble' with UVW coordinates

keyword - The keyword from which to get one or more UV dataset names.
Defaults to 'vis', the usual value.
"""
    ll.uvdatinp (keyword, flags)

class UVDatDataSet (UVDataSet):
    def __init__ (self, tno):
        self.tno = tno
        self.name = getCurrentName ()

    def _close (self):
        ll.uvdatcls ()

def inputSets ():
    """Generate a sequence of DataSet objects representing the
visdata input sets."""

    ds = None
    
    while True:
        if ds is not None: ds.close ()
        
        (status, tin) = ll.uvdatopn ()

        if not status: break

        ds = UVDatDataSet (tin)

    if ds is None:
        raise RuntimeError ('No input UV data sets?')
    else:
        ds.close ()

def singleInputSet ():
    """Get a single DataSet object representing the visdata input set.
You should only use this function if you pass the 'b' option to
init ().
"""

    (status, tin) = ll.uvdatopn ()

    if not status: raise RuntimeError ('Unable to open input data set!')

    # Count on the user or the __del__ to close this.
    return UVDatDataSet (tin)

def readData (maxchan = 4096):
    """Generate a sequence of (preamble, data, flags, nread) tuples representing
the visibility data in the current file."""
    
    preamble = N.zeros (5, dtype=N.double)
    data = N.zeros (maxchan, dtype=N.complex64)
    flags = N.zeros (maxchan, dtype=N.int32)

    while True:
        nread = ll.uvdatrd (preamble, data, flags, maxchan)

        if nread == 0: break

        yield (preamble, data, flags, nread)

def readAll (maxchan = 4096):
    """Yield the data from all of the input datasets sequentially."""
    
    for ds in inputSets ():
        for t in readData (maxchan=maxchan):
            yield t

# Variable probes

def _getOneInt (kw):
    a = N.zeros (1, dtype=N.int32)
    ll.uvdatgti (kw, a)
    return a[0]

def _getOneFloat (kw):
    a = N.zeros (1, dtype=N.float32)
    ll.uvdatgtr (kw, a)
    return a[0]

def _getOneString (kw):
    # This is wrapped in lowlevel.
    return ll.uvdatgta (kw)

def getNPol ():
    """Return the number of simultaneous polarizations being returned by readData.
Zero indicates that this number could not be determined.
"""    
    return _getOneInt ('npol')

def getPols ():
    """Return the polarizations being returned by readData, an array of the size
returned by getNPol (). Zeros indicate an error. FIXME: what do the numerical
values mean?"""

    a = N.zeros (getNPol (), dtype=N.int32)
    ll.uvdatgti ('pols', a)
    return a

def getPol ():
    """Return the last Stokes parameter returned by readData. May vary from one
visibility to another."""

    return _getOneInt ('pol')

def getCurrentTno ():
    """Return the 'tno' of the current file being processed."""
    return _getOneInt ('number')

def getNChan ():
    """Return the number of channels being processed."""
    return _getOneInt ('nchan')

def getNFiles ():
    """Return the number of files being processed."""
    return _getOneInt ('nfiles')

def getVisNum ():
    """Return the current visibility number."""
    return _getOneInt ('visno')

def getVariance ():
    """Return the variance of the current visibility."""
    return _getOneFloat ('variance')

def getJyPerK ():
    """Return the Jansky-per-Kelvin value of the current visibility."""
    return _getOneFloat ('jyperk')

def getCurrentName ():
    """Return the name of the file currently being processed."""
    return _getOneString ('name')

def getLinetype ():
    """Return the linetype of the current visibility."""
    return _getOneString ('ltype')
