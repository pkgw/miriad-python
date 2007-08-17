"""This module exposes the Miriad subroutine library in a Pythonic
manner, allowing you to write Miriad tasks in Python.
"""

import _uvio # then io check bug symbols
import _mirgood, _mirugly # now can do the full Fortran.
import lowlevel

MiriadError = _uvio.MiriadError

# Higher-level APIs

import base
from base import *

import keys, readgains, uvdat

# Automatically do this -- will do a keyini with sys.argv.

keys.init ()
