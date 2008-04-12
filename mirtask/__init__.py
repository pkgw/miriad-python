"""This module exposes the Miriad subroutine library in a Pythonic
manner, allowing you to write Miriad tasks in Python.
"""

import lowlevel
MiriadError = lowlevel.MiriadError

from base import *
import util
