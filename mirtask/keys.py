"""Python wrappers for the MIRIAD keyword handline routines. Routines:

keyword  - Register a keyword
keymatch - Register a keymatch keyword (like an enumeration)
option   - Register an option
init     - Tell the keyword routines what our arguments were.
process  - Process keywords and return an object with the arguments.
"""

import sys
import lowlevel as ll
import numpy
from mirtask import MiriadError

__all__ = []

# Constant indicating that the keyword represents a file input.
file = '_file_keyword'

class KeyHolder (object):
    """An empty subclass of object that will have fields
set to the values of keys by the key-handling routines."""
    pass

_keywords = {}
_okkinds = ['a', 'i', 'd', 'f', 't', 'b']
_okfmts = ['dms', 'hms', 'dtime', 'atime', 'time']

def keyword (name, kind, default, nmax=1, timefmt=None):
    """Register a keyword with the key-handling system. Parameters:

name    - The name of the keyword.
kind    - The keyword kind: 'f' for filename, 'a' for textual string,
          'i' for integer, 'd' for double, 'b' for boolean, and 't'
          for time or angle.
default - The default value of the keyword.
nmax    - The maximum number of items to return for this keyword. Defaults
          to 1, indicating a single-value keyword.
timefmt - The expected format of the time value. Only needed if kind is 't'.
          Allowed values are:

          dms   - Angle given in dd:mm:ss.s or dd.ddd; output in radians.
          hms   - Angle given in hh:mm:ss.s or hh.hhh; output in radians.
          dtime - Day fraction given in hh:mm:ss.s or hh.hhh; output is
                  a day fraction between 0 and 1.
          atime - Absolute time, given in yymmmdd.ddd or yymmdd:hh:mm:ss.s
                  or an epoch (bYYYY or jYYYY); output in Julian days.
          time  - Either an absolute time or a day fraction; output is either
                  a day fraction or Julian days.
"""

    if name in _keywords: raise Exception ('Keyword already registered')
    if kind not in _okkinds: raise Exception ('Unknown keyword kind')

    if kind == 't':
        if timefmt is None:
            raise Exception ('Must provide a time format for a time keyword')
        if timefmt not in _okfmts:
            raise Exception ('Illegal time format ' + timefmt)

    if kind == 'b' and nmax != 1:
        raise Exception ('Cannot have multivalued boolean keyword')
    
    _keywords[name] = (kind, nmax, default, None, timefmt)

def keymatch (name, nmax, allowed):
    """Register an expanded multi-match (MIRIAD keymatch) keyword. Parameters:

name    - The name of the multi-match keyword
nmax    - The maximum number of items in allowed in the keyword value
allowed - The full list of allowed item values.
"""

    if name in _keywords: raise Exception ('Keyword already registered!')

    _keywords[name] = (kind, nmax, None, allowed, None)

_options = set ()

def option (*names):
    """Register options with the key-handling system. Parameters:

*names - An arbitrary number of option names.
"""

    for name in names:
        name = str (name)
        
        if name in _options: raise Exception ('Option "%s" already registered!' % name)

        _options.add (name)

__all__ += ['keyword', 'keymatch', 'option']

def init (args=None):
    """Re-initialize the MIRIAD database of keyword arguments.
Parameters:

args - The argv array of this program. If None, sys.argv is used.
"""
    
    if args is None: args = sys.argv

    ll.keyini (args)

def process ():
    """Process the arguments to this task. Returns an object with fields
set to the values of the registered keyword and option arguments. A warning
will be issued if any un-registered keywords or options were given.
"""

    res = KeyHolder ()
    
    # Keywords

    for name, (kind, nmax, default, mmallowed, timefmt) in _keywords.iteritems ():
        if mmallowed is not None:
            # This is a keymatch keyword. Easy since there is no multiplexing
            # by type.
            val = ll.keymatch (name, mmallowed, nmax)
        else:
            # Not a keymatch keyword

            if nmax == 1:
                # Single-valued too

                if kind == 'a':
                    val = ll.keya (name, str (default))
                elif kind == 'i':
                    val = ll.keyi (name, int (default))
                elif kind == 'd':
                    val = ll.keyd (name, float (default))
                elif kind == 'f':
                    val = ll.keyf (name, str (default))
                elif kind == 'b':
                    val = bool (ll.keyl (name, int (bool (default))))
                elif kind == 't':
                    val = ll.keyt (name, timefmt, str (default))
                else: raise Exception ('not reached')
            else:
                # Multi-valued
                
                if kind == 'a':
                    val = ll.mkeya (name)
                elif kind == 'i':
                    val = ll.mkeyi (name, nmax)
                elif kind == 'd':
                    val = ll.mkeyd (name, nmax)
                elif kind == 'f':
                    val = ll.mkeyf (name)
                elif kind == 't':
                    val = ll.mkeyt (name, nmax, timefmt)
                else: raise Exception ('not reached')

        # Ok now we have the value. Woo.

        setattr (res, name, val)

    # Options. Must flatten the set() into an array
    # to be sure our indexing is well-defined.

    ml = 0
    names = []
    
    for name in _options:
        ml = max (ml, len (name))
        names.append (name)

    optarr = []

    for i in range (0, len (names)):
        optarr.append (names[i].ljust (ml, ' '))

    present = ll.options ('options', optarr)

    for i in range (0, len (names)):
        setattr (res, names[i], present[i] != 0)

    # All done. Check if any unexhausted keywords.

    ll.keyfin ()
    
    return res

__all__ += ['init', 'process']
