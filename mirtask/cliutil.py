# Copyright 2009, 2010 Peter Williams
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

""":synopsis: Utilities for programs run from the command line.

.. moduleauthor:: Peter Williams <peter@newton.cx>

When this module is imported, it replaces the system exception handler
(:data:`sys.excepthook`) with a new one that prints out
:class:`mirtask.ProgramFailError` exceptions as (comparatively) terse
error messages without tracebacks. Other exceptions are presented in a
format similar to the one employed by the default Python handler.

The motivation for this functionality is that MIRIAD tasks often need
to abort abruptly but that doing so by raising Python exceptions
creates cluttered output (*e.g.* deep tracebacks) that can be
confusing for the user. This module makes it possible to use
:class:`mirtask.ProgramFailError` exceptions to terminate a program
while maintaining more control over the output presented to the
user. Example usage would be::

   from mirtask import ProgramFailError, cliutil

   def my_deep_function ():
       # ...
       if index < 0 and isinf (fmax):
           raise ProgramFailError ('negative index %f disallowed with '
                                   'infinite max frequency %f', index, fmax)

Uncaught instances of :class:`ProgramFailError` are printed preceded
by the string "Error:", so your exception message should begin with a
lower-case letter.

The original system exception handler is stored in the variable
:data:`prev_except_hook`.

If the environment variable :envvar:`MIRTASK_FULL_ERRORS` is nonempty,
tracebacks will be printed for all exceptions.
"""

import sys, os, traceback
from base import ProgramFailError

__all__ = ['prev_except_hook']

prev_except_hook = sys.excepthook
"""This variable stores the original value of
:data:`sys.excepthook` before it is overwritten with the module's version."""

def _mirtask_except_hook (etype, exc, tb):
    if issubclass (etype, ProgramFailError) and \
            not ('MIRTASK_FULL_ERRORS' in os.environ):
        print >>sys.stderr, 'Error:', exc.message
        sys.exit (1)

    # We're intentionally making things a little opaque-sounding here.
    # Hopefully the user will get the impression that this is an
    # unexpected error message.
    print >>sys.stderr, 'Internal state traceback (most recent call last):'
    traceback.print_tb (tb, file=sys.stderr)

    print >>sys.stderr
    print >>sys.stderr, 'Internal Error: uncaught %s exception' % etype.__name__
    print >>sys.stderr, 'Exception details:', exc
    sys.exit (1)

sys.excepthook = _mirtask_except_hook
