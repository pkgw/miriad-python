# Copyright 2009, 2010, 2011 Peter Williams
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

import sys, os.path, traceback, tempfile

__all__ = ['prev_except_hook']

prev_except_hook = sys.excepthook
"""This variable stores the original value of
:data:`sys.excepthook` before it is overwritten with the module's version."""

def _cli_except_hook (etype, exc, tb):
    """User-friendly exceptions, for the following definition of
    user-friendly:

    - EnvironmentErrors (IOErrors and OSErrors) are printed to the
    user with their strerror and filename information, in the hope
    that the user will be able to understand why the error
    occurred. (Permission denied, no space left on device, etc.) The
    calling function is identified but the full traceback is NOT
    printed.

    - KeyboardInterrupts are reported without any further information.

    - Other unhandled exceptions are reported briefly as unhandled
    internal errors, and the full exception and traceback information
    are logged to a file if at all possible. These are not expected to
    be "user-servicable" exceptions so the idea is to hide the lengthy
    and confusing technical information. Saving the information to a
    file also hopefully makes it more likely that the technical
    details can be sent to the developer exactly and fully.

    - If the information can't be logged to a file, it's printed for
    lack of a better alternative.

    - If the environment variable MIRPY_PRINT_EXCEPTIONS is set and
    nonempty, the traceback information is printed for all exceptions
    (including EnvironmentErrors) and it's always printed to standard
    error.
    """

    forcestderr = len (os.environ.get ('MIRPY_PRINT_EXCEPTIONS', '')) > 0
    details = []
    skiptb = False

    if isinstance (exc, KeyboardInterrupt):
        msg = 'interrupted by user'
        skiptb = not forcestderr
    elif not isinstance (exc, EnvironmentError):
        msg = 'unhandled internal exception of kind ' + etype.__name__
        details.append ('Technical detail: ' + str (exc))
    else:
        hasfn = hasattr (exc, 'filename') and exc.filename is not None

        if isinstance (exc, IOError):
            if hasfn:
                op = 'failure performing I/O on path \"%s\"' % exc.filename
            else:
                op = 'I/O failure'
        elif isinstance (exc, OSError):
            if hasfn:
                op = 'OS reported failure operating on path \"%s\"' % exc.filename
            else:
                op = 'OS reported a failure'
        else:
            if hasfn:
                op = '%s operating on path \"%s\"' % (etype.__name__, exc.filename)
            else:
                op = etype.__name__

        msg = '%s: %s' % (op, exc.strerror)
        filename, lineno, func, text = traceback.extract_tb (tb)[-1]
        details.append  ('The error occurred in the function %s (%s:%d)' %
                         (func, filename, lineno))
        skiptb = not forcestderr

    if not skiptb:
        log = None

        if not forcestderr:
            logfnbase = 'bug_%d.txt' % os.getpid ()

            for logfn in (logfnbase, os.path.join (tempfile.gettempdir (), logfnbase)):
                try:
                    log = open (logfn, 'a')
                    logmsg = 'in the file "%s".' % logfn
                    break
                except StandardError:
                    pass

        if log is None:
            log = sys.stderr
            logmsg = 'below.\n'

        details.append ('Debugging information is logged ' + logmsg)

    print >>sys.stderr, 'Error:', msg
    for detail in details:
        print >>sys.stderr, '      ', detail

    if skiptb:
        return

    def p (format, *args):
        print >>log, format % args

    p ('Please report this error information to the developer completely and')
    p ('exactly to aid in the debugging process.')
    p ('')
    p ('Traceback (most recent call last):')
    traceback.print_tb (tb, file=log)
    p ('')
    p ('%s exception: %s', etype.__name__, exc)

sys.excepthook = _cli_except_hook
