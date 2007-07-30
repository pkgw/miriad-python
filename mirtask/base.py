"""A module that provides an object that reads a UV data set's
gains table conveniently.
"""

import lowlevel as ll
import numpy as N
from mirtask import MiriadError

__all__ = []

# Some utility functions

def initKeys ():
    """Initialize the MIRIAD keys system based on sys.argv. Can be
    called multiple times, to iterate through the keys repeatedly."""

    from sys import argv
    ll.keyini (argv)

__all__ += ['initKeys']

# Very simple wrapper classes. Shouldn't necessarily be used,
# given that there are standard APIs like uvdat*

class DataFile (object):
    def __init__ (self, file, create=False):
        if create: mode = 'new'
        else: mode = 'old'
        
        self.tno = ll.hopen (file, mode)

    def __del__ (self):
        # tno can be None if we got an exception inside hopen.
        
        if ll is not None and hasattr (self, 'tno'):
            ll.hclose (self.tno)

__all__ += ['DataFile']
