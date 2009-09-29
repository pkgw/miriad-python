# Copyright 2009 Peter Williams
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

'''mirtask.keys - wrappers for the MIRIAD keyword handline routines

Public routines are:

keyword  - Register a keyword
keymatch - Register a keymatch keyword (like an enumeration)
option   - Register an option
init     - Tell the keyword routines what our arguments were.
process  - Process keywords and return an object with the arguments.
'''


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
default - The default value of the keyword. The default for a multivalued
          keyword is ignored and should be None.
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

    _keywords[name] = (None, nmax, None, allowed, None)

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

_uvdatFlags = None
_uvdatCals = False
_uvdatViskey = None

def doUvdat (flags, calOpts, viskey='vis'):
    """Initialize the UVDAT subsystem when reading in keywords.
Parameters:

flags   - Flags to the MIRIAD UVDATINP routine. See the documentation
          to uvdat.init () for allowed flags and their meaning.

calOpts - If true, automatically enable the calibration options 'nocal',
          'nopass', and 'nopol', and apply calibrations in UVDAT unless
          those options are given. You should use this mechanism instead
          of passing the 'c', 'e', and 'f' flags to uvdat.init ()

Returns: None.
"""
    global _uvdatFlags, _uvdatCals, _uvdatViskey

    _uvdatFlags = flags
    _uvdatCals = calOpts
    _uvdatViskey = viskey
    
    if calOpts:
        option ('nocal', 'nopol', 'nopass')

__all__ += ['doUvdat']

def init (args=None):
    """Re-initialize the MIRIAD database of keyword arguments. You do not
need to call this function explicitly if you are going to call process (),
since that function calls init () itself.

Parameters:

args - The argv array of this program. If None, sys.argv is used.
"""
    
    if args is None: args = sys.argv

    ll.keyini (args)

def process (args=None):
    """Process the arguments to this task. Returns an object with fields
set to the values of the registered keyword and option arguments. A warning
will be issued if any un-registered keywords or options were given.

Parameters:

args - The argv array of this program. If None, sys.argv is used.
"""

    init (args)
    
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
                    val = ll.mkeya (name, nmax)
                elif kind == 'i':
                    val = ll.mkeyi (name, nmax)
                elif kind == 'd':
                    val = ll.mkeyd (name, nmax)
                elif kind == 'f':
                    val = ll.mkeyf (name, nmax)
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

    # UVDAT initialization

    if _uvdatFlags is not None:
        import uvdat

        f = _uvdatFlags
        
        if _uvdatCals:
            if not res.nocal: f += 'c'
            if not res.nopass: f += 'f'
            if not res.nopol: f += 'e'

        try:
            uvdat.init (f, _uvdatViskey)
        except MiriadError, e:
            # Prettier error message if argument problem.
            print 'Error:', e
            sys.exit (1)
    
    # All done. Check if any unexhausted keywords.

    ll.keyfin ()
    
    return res

__all__ += ['init', 'process']
