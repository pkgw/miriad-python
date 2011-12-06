'''mirexec - classes for executing MIRIAD tasks'''

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

import sys, os, re, math
import os.path
from os.path import join
from subprocess import Popen, PIPE, STDOUT
import miriad

# Compatibility with Python 2.4. It seems safest to give the exception
# class a unique name so that callers don't build in a Python >=2.5
# dependency by expecting our exception class to be CalledProcessError
# itself.
try:
    from subprocess import CalledProcessError as _CPE
    class TaskFailError (_CPE): pass
    del _CPE
except ImportError:
    class TaskFailError (Exception):
        def __init__ (self, returncode, cmd):
            self.returncode = returncode
            self.cmd = cmd
        def __str__ (self):
            return "Command '%s' returned non-zero exit status %d" % (self.cmd,
                                                                      self.returncode)

class TaskLaunchError (Exception):
    """Indicates that it was not possible to launch the desired
task. A common cause of this is that the task was not found in the
executable search path.

Instances have an attribute **command**, an array of strings giving
the command and arguments whose invocation was attempted. The zeroth
string is the task name.

Instances also have an attribute **detail**, which is a string giving
a more detailed explanation of what failed. This is currently the
stringification of any :exc:`OSError` that was raised in the attempt
to launch the task.
"""

    def __init__ (self, command, fmt, *args):
        self.command = command
        self.detail = fmt % args
    def __str__ (self):
        return 'Could not launch \"%s\": %s' % (' '.join (self.command), self.detail)


# Management of the environment of the tasks that we spawn.  By
# default we clear most environment variables; Miriad programs are
# essentially standalone, so we're only going to need a fairly
# constrained set of variables.

_bindir = None
_childenv = {}

_childenvCopylist = ['DISPLAY', 'EDITOR', 'HOME', 'LANG', 'LOGNAME',
                     'PAGER', 'PATH', 'SHELL', 'TERM', 'UID', 'USER',
                     'VISUAL']

def _initchildenv ():
    for var in _childenvCopylist:
        if var in os.environ:
            _childenv[var] = os.environ[var]

    for (key, val) in os.environ.iteritems ():
        # another other wildcards to copy over?
        if key.startswith ('MIR'):
            _childenv[key] = val
        elif key.startswith ('PGPLOT'):
            _childenv[key] = val
        elif key.startswith ('LD_'):
            _childenv[key] = val
        elif key.startswith ('DYLD_'):
            _childenv[key] = val

_initchildenv ()
del _initchildenv


def addEnvironmentClassic (home, hosttype):
    global _bindir, _childenv
    
    _bindir = join (home, 'bin', hosttype)
    
    _childenv['MIR'] = home
    _childenv['MIRHOST'] = hosttype
    _childenv['AIPSTV'] = 'XASIN'
    _childenv['MIRBIN'] = _bindir
    _childenv['MIRCAT'] = join (home, 'cat')
    _childenv['MIRDEF'] = '.'
    _childenv['MIRDOC'] = join (home, 'doc')
    _childenv['MIRLIB'] = join (home, 'lib', hosttype)
    _childenv['MIRNEWS'] = join (home, 'news')
    _childenv['MIRPAGER'] = 'doc'
    _childenv['MIRSRC'] = join (home, 'src')
    _childenv['MIRPROG'] = join (home, 'src', 'prog')
    _childenv['MIRSUBS'] = join (home, 'src', 'subs')
    _childenv['MIRPDOC'] = join (home, 'doc', 'prog')
    _childenv['MIRSDOC'] = join (home, 'doc', 'subs')
    _childenv['PGPLOT_DIR'] = _childenv['MIRLIB']

    # Need this to find pgxwin_server if using PGPlot.
    _childenv['PATH'] += ':' + _childenv['MIRBIN']

    _childenv['LD_LIBRARY_PATH'] = _childenv['MIRLIB']


def addEnvironmentAutotools (home):
    global _bindir, _childenv
    
    _bindir = join (home, 'bin')
    
    _childenv['MIR'] = home
    _childenv['AIPSTV'] = 'XASIN'
    _childenv['MIRBIN'] = _bindir
    _childenv['MIRCAT'] = join (home, 'share', 'miriad')
    _childenv['MIRDEF'] = '.'
    _childenv['MIRDOC'] = join (home, 'share', 'miriad', 'doc')
    _childenv['MIRLIB'] = join (home, 'lib')
    _childenv['MIRPAGER'] = 'doc'
    _childenv['PGPLOT_DIR'] = join (home, 'libexec')


def _mirBinPath (name):
    if _bindir is None:
        # this may be OK if the python shell was run with the Miriad
        # programs already living somewhere in $PATH. If that's not
        # the case, we'll find out a in a second when the launch of
        # the task fails.
        return name
    
    return join (_bindir, name)


# The MIRIAD task running framework

class DefaultedTaskType (type):
    # YES! I get to write a metaclass! This looks at the
    # _keywords and _options members and fills in default values
    # in the class dictionary for any keywords or options
    # not already specified. So if there is a 'foo' keyword,
    # it creates an entry in the class dictionary of 'foo = None'.
    # This allows TaskBase to just getattr() any class parameter,
    # and makes tab-completing easy.
    #
    # We also guess the task name if _name is not set. Cute.
    
    def __init__ (cls, name, bases, dict):
        type.__init__ (cls, name, bases, dict)
        
        # TaskBase doesn't get any special treatment
        if name == 'TaskBase':
            return
        
        if '_name' not in dict:
            if name.startswith ('Task'):
                setattr (cls, '_name', name[4:].lower ())
            else:
                raise Exception ('Task class must define a _name member')

        for p in dict.get ('_keywords', []):
            if p not in dict:
                setattr (cls, p, None)

        for o in dict.get ('_options', []):
            if o not in dict:
                setattr (cls, o, False)


class MiriadSubprocess (Popen):
    # In this class, we work around the crappy API of the Python standard libraries.

    """:synopsis: a handle to a MIRIAD task that was launched.

:arg command: an iterable of strings giving the command and
  arguments to launch. Saved as the :attr:`command` attribute
  after initialization.
:arg kwargs: extra arguments to be passed to
  :class:`subprocess.Popen`.
:raises: the same things that :class:`subprocess.Popen` may raise;
  :exc:`OSError` in most cases.

This class allows you to interact with a running MIRIAD task and
interrogate it after the task finishes. Generally, you won't create
:class:`MiriadSubprocess` instances yourself, but instead will have
them returned to you from calls to :meth:`TaskBase.launch`,
:meth:`~TaskBase.launchpipe`, or :meth:`~TaskBase.launchsilent`.

:class:`MiriadSubprocess` is a subclass of :class:`subprocess.Popen`
and offers all of the same features. This class additionally provides
:meth:`checkwait` which waits for the task to finish, then raises
:exc:`TaskFailError` if the task failed. The :meth:`checkcommunicate`
method does the same thing but also allows the task output to be
captured. (It also allows input to be sent to the task, though this is
less often useful.)

The creation of a :class:`MiriadSubprocess` instance is synonymous
with launching a subprocess -- if the creation succeeds, the
subprocess is launched.
"""

    command = None
    """An iterable of strings giving the command and arguments that
    were executed."""

    def __init__ (self, command, **kwargs):
        # Raise a TypeError if command is not iterable.
        iter (command)

        super (MiriadSubprocess, self).__init__ (command, **kwargs)
        self.command = command


    def checkFailNoPipe (self, log=None):
        """Raise an exception if the task failed; to be used if the
task output was not captured. Assumes the subprocess has finished
executing.

:arg filelike log: if the task did indeed fail, print extra debugging
  information to this stream, unless it is :const:`None` (the
  default).
:returns: self
:raises: :exc:`StandardError` if the task has not yet finished running
:raises: :exc:`TaskFailError` if the task failed.

Note that this function only returns if the task finished
successfully. Otherwise, an exception is raised.
"""

        if self.returncode is None:
            raise StandardError ('Have not yet waited on child process')
        if self.returncode == 0:
            return self

        if log is not None:
            print >>log, 'Task "%s" failed with exit code %d!' % \
                (self.command[0], self.returncode)
            print >>log, 'Command line:', ' '.join (self.command)
            print >>log, 'Task output was not captured; it may be printed above.'

        raise TaskFailError (self.returncode, ' '.join (self.command))


    def checkFailPipe (self, stdout, stderr, log=None):
        """Raise an exception if the task failed; to be used if the
task output was captured. Assumes the subprocess has finished
executing.

:arg str stdout: a single string giving the captured standard output
  of the task.
:arg str stderr: a single string giving the captured standard error
  of the task.
:arg filelike log: if the task did indeed fail, print extra debugging
  information to this stream, unless it is :const:`None` (the
  default). Unlike :meth:`checkFailNoPipe`, this debugging information
  contains the contents of *stdout* and *stderr*.
:returns: self
:raises: :exc:`StandardError` if the task has not yet finished running
:raises: :exc:`TaskFailError` if the task failed.

Note that this function only returns if the task finished
successfully. Otherwise, an exception is raised.

Also note that *stdout* and *stderr* are only used to log extra
debugging information. It is important to do this, because if the task
output is captured and the task fails, the user will have no way of
knowing *why* the task failed unless the task output is logged
somewhere.
"""

        if self.returncode is None:
            raise StandardError ('Have not yet waited on child process')
        if self.returncode == 0:
            return self

        if log is not None:
            stdout = stdout.splitlines ()
            stderr = stderr.splitlines ()

            print >>log, 'Task "%s" failed with exit code %d!' % \
                (self.command[0], self.returncode)
            print >>log, 'Command line:', ' '.join (self.command)
            print >>log, 'Task\'s standard output was:'
            for l in stdout:
                print >>log, '\t', l
            print >>log, 'Task\'s standard error was:'
            for l in stderr:
                print >>log, '\t', l

        raise TaskFailError (self.returncode, ' '.join (self.command))


    def checkwait (self, failok=False, log=None):
        """Wait for the task to complete, then raise an exception if
it failed.

:arg bool failok: if :const:`True`, don't raise an exception if the
  task failed -- this is equivalent to just calling
  :meth:`~subprocess.Popen.wait`. The default is :const:`False`.
:arg filelike log: if the task did indeed fail, extra debugging
  information will be printed to this stream, unless it is
  :const:`None` (the default).
:returns: self
:raises: :exc:`TaskFailError` if the task failed and *failok* was
  :const:`False`.

This method assumes that the task output has not been captured and
hence uses :meth:`checkFailNoPipe`. If the output should be captured,
used :meth:`checkcommunicate`.
"""

        self.wait ()
        if not failok:
            self.checkFailNoPipe (log)
        return self


    def checkcommunicate (self, send=None, failok=False, log=None):
        """Exchange input and output with the task, wait for it to
complete, and then raise an exception if it failed.

:arg str send: input to send to the subprocess in its standard input
  stream, or :const:`None` to send nothing.
:arg bool failok: if :const:`True`, don't raise an exception if the
  task failed -- this is equivalent to just calling
  :meth:`~subprocess.Popen.communicate`. The default is :const:`False`.
:arg filelike log: if the task did indeed fail, extra debugging
  information will be printed to this stream, unless it is
  :const:`None` (the default).
:returns: a tuple ``(stdout, stderr)``, two strings of the output
  captured from the subprocess.
:raises: :exc:`TaskFailError` if the task failed and *failok* was
  :const:`False`.

The returned *stdout* and *stderr* contents are all buffered into
single Python strings, so this method is not appropriate if the task
will generate very large amounts of output.

This method captures the task output and hence uses
:meth:`checkFailPipe`. If the output should be not captured, used
:meth:`checkwait`.
"""
        stdout, stderr = self.communicate (send)
        if not failok:
            self.checkFailPipe (stdout, stderr, log)
        return stdout, stderr


class TaskBase (object):
    """:synopsis: Generic MIRIAD task launcher
:arg kwargs: attributes to set on the object

A generic launcher class for MIRIAD tasks. Don't create instances
of this class --- instead, create instances of its subclasses,
such as :class:`TaskInvert` or :class:`TaskUVCat`. If you
want to invoke a task that hasn't been wrapped in the :mod:`mirexec`
module, it's easy to wrap it yourself: see :ref:`customtasks`.
"""

    __metaclass__ = DefaultedTaskType
    
    _name = None
    _keywords = None
    _options = None

    def __init__ (self, **kwargs):
        self.set (**kwargs)


    def set (self, **kwargs):
        """Set keywords and options on the task

:arg kwargs: the values to set
:returns: *self*

This function is merely a shorthand that sets attributes on the
instance via :func:`setattr`.
"""

        for (key, val) in kwargs.iteritems ():
            setattr (self, key, val)
        return self


    def commandLine (self):
        cmd = [_mirBinPath (self._name)]

        # Options
        
        options = []

        for opt in self._options or []:
            val = getattr (self, opt)

            # I think it'd be really confusing to set options based on
            # the Python truthiness of option fields -- e.g., task.foo = 'hello'
            # causing "task options=foo" to be run, if "foo" is an option.
            # So the only valid values for an option are True, False, and None.
            # I have a dim memory of there being a task or two that actually
            # accept nonboolean inputs through the options keyword in some
            # evil way, but if I ever run into that again that can be dealt
            # with.

            if val is None:
                continue

            if not isinstance (val, bool):
                raise ValueError ('Option %s set to non-bool, non-None value %s' \
                                      % (opt, val))

            if val:
                options.append (opt)

        if len (options) > 0:
            cmd.append ('options=' + ','.join (options))

        # Keywords
        
        for name in self._keywords or []:
            key = name

            if key[-1] == '_':
                key = key[:-1]
            
            val = getattr (self, name)

            if val is None:
                continue

            cmd.append ("%s=%s" % (key, miriad.commasplice (val)))

        return cmd


    def launch (self, **kwargs):
        """Launch an invocation of the task with the current keywords

:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess` constructor
:returns: a :class:`MiriadSubprocess` instance
:raises: :exc:`TaskLaunchError` if there was an error launching the task

This task launches an instance of the task. It does not wait for that
instance to complete; you must use the returned :class:`MiriadSubprocess`
instance to wait for completion and check results.

This function can be useful if you want to launch several tasks in parallel.
To wait for the task to complete, use :meth:`run`. To wait for the task and
obtain its output, use :meth:`snarf`. To wait for the task and discard its
output, use :meth:`runsilent`.
"""
        cmd = self.commandLine ()
        miriad.trace (cmd)
        try:
            return MiriadSubprocess (cmd, shell=False, close_fds=True,
                                     env=_childenv, **kwargs)
        except OSError, e:
            if e.errno == 2:
                raise TaskLaunchError (cmd, 'executable not found in $PATH')
            raise TaskLaunchError (cmd, str (e))


    def launchpipe (self, **kwargs):
        """Launch an invocation of the task with the current keywords,
redirecting its output so that it may be examined by the caller.

:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess` constructor
:returns: a :class:`MiriadSubprocess` instance
:raises: :exc:`TaskLaunchError` if there was an error launching the task

This task launches an instance of the task. It does not wait for that
instance to complete; you must use the returned
:class:`MiriadSubprocess` instance to wait for completion and check
results. To access the task output, use the methods and attributes
provided by :class:`MiriadSubprocess`.

This function can be useful if you want to launch several tasks in
parallel. To just wait for the task, use :meth:`snarf`. To wait for
the task and ignore its output, use :meth:`run`. To wait for the task
and discard its output, use :meth:`runsilent`.
"""
        return self.launch (stdin=file (os.devnull, 'r'), stdout=PIPE, stderr=PIPE,
                            **kwargs)


    def launchsilent (self, **kwargs):
        """Launch an invocation of the task with the current keywords,
discarding its output.

:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess` constructor
:returns: a :class:`MiriadSubprocess` instance
:raises: :exc:`TaskLaunchError` if there was an error launching the task

This task launches an instance of the task. It does not wait for that
instance to complete; you must use the returned
:class:`MiriadSubprocess` instance to wait for completion and check
results.

The task output is discarded. This is not recommended in most
situations, since usually the task output is the only means by which
errors can be diagnosed.

This function can be useful if you want to launch several tasks in
parallel. To just wait for the task, use :meth:`runsilent`. To launch
the task and ignore its output, use :meth:`launch`. To wait for the
task and ignore its output, use :meth:`run`.
"""
        nullout = file (os.devnull, 'w')
        return self.launch (stdin=file (os.devnull, 'r'), stdout=nullout, stderr=nullout,
                            **kwargs)


    def run (self, failok=False, log=None, **kwargs):
        """Run the task with the current keywords.

:arg bool failok: if :const:`True`, no exception will be raised if the
  task returns a nonzero exit code.
:arg filelike log: where to log debugging information if the task
  fails, or :const:`None` (the default) not to log this information.
:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess`
  constructor.
:raises: :exc:`TaskLaunchError` if there was an error launching the task.
:raises: :exc:`TaskFailError` if the task returns a nonzero exit code.
:returns: *self*

Runs the task and waits for it to complete. By default, if the task returns
an error code, a :exc:`TaskFailError` is raised, but this can be disabled
by setting *failok* to :const:`True`. The standard output and error of the
task will not be redirected.

To retrieve the output of the task, use :meth:`snarf`. To not wait for
the task to complete, use :meth:`launch`. To discard the output of the
task, use :meth:`runsilent`.
"""

        self.launch (**kwargs).checkwait (failok, log)
        return self


    def runsilent (self, failok=False, log=None, **kwargs):
        """Run the task with the current keywords, discarding its output.

:arg bool failok: if :const:`True`, no exception will be raised if the
  task returns a nonzero exit code.
:arg filelike log: where to log debugging information if the task
  fails, or :const:`None` (the default) not to log this information.
:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess` constructor.
:raises: :exc:`TaskLaunchError` if there was an error launching the task.
:raises: :exc:`TaskFailError` if the task returns a nonzero exit code.
:returns: *self*

Runs the task and waits for it to complete. By default, if the task returns
an error code, a :exc:`TaskFailError` is raised, but this can be disabled
by setting *failok* to :const:`True`.

The task output is discarded. This is not recommended in most
situations, since usually the task output is the only means by which
errors can be diagnosed.

To ignore the output of the task, use :meth:`run`. To not wait for
the task to complete, use :meth:`launchsilent`.
"""
        self.launchsilent (**kwargs).checkwait (failok, log)
        return self


    def snarf (self, send=None, failok=False, log=sys.stderr, **kwargs):
        """Run the task and retrieve its output.

:arg str send: input to send the task on its standard input, or :const:`None`
  not to do so
:arg bool failok: if :const:`True`, no exception will be raised if the
  task returns a nonzero exit code
:arg log: where to log the task's output if it fails, or :const:`None`
  not to log the output. Default is ``sys.stderr``.
:arg kwargs: extra arguments to pass to the :class:`MiriadSubprocess` constructor
:raises: :exc:`TaskLaunchError` if there was an error launching the task.
:raises: :exc:`TaskFailError` if the task returns a nonzero exit code
:returns: ``(stdout, stderr)``, both of which are arrays of strings of the
  task's output split on line boundaries (via :meth:`str.splitlines`). They
  correspond to the standard output and standard error of the task subprocess,
  respectively. Note that the proper interleaving of the outputs (i.e., where
  the standard error messages appear, relative to the standard output lines)
  is unknowable.

Runs the task, wais for it to complete, and returns its textual
output. By default, if the task returns an error code, a
:exc:`TaskFailError` is raised, but this can be disabled by setting
*failok* to :const:`True`.

To leave the output of the task un-redirected, use :meth:`run`. To not
wait for the task to complete, use :meth:`launch`. To discard the
output of the task, use :meth:`runsilent`.
"""
        # Use the checkFail "log" feature by default, since otherwise
        # it'll probably be impossible to diagnose why the program failed.
        stdout, stderr = self.launchpipe (**kwargs).checkcommunicate (send, failok, log)
        return stdout.splitlines (), stderr.splitlines ()


class TaskCgDisp (TaskBase):
    _keywords = ['device', 'in_', 'type', 'region', 'xybin', 'chan',
                 'slev', 'levs1', 'levs2', 'levs3', 'cols1', 'range',
                 'vecfac', 'boxfac', 'nxy', 'labtyp', 'beamtyp',
                 '3format', 'lines', 'break', 'csize', 'scale', 'olay']

    _options = ['abut', 'beamAB', 'blacklab', 'conlabel', 'fiddle',
                'full', 'gaps', 'grid', 'mirror', 'nodistort',
                'noepoch', 'noerase', 'nofirst', 'corner', 'relax',
                'rot90', 'signs', 'single', 'solneg1', 'solneg2',
                'solneg3', 'trlab', 'unequal', 'wedge', '3pixel',
                '3value']


class TaskUVList (TaskBase):
    _keywords = ['vis', 'select', 'line', 'scale', 'recnum', 'log']
    _options = ['brief', 'data', 'average', 'allan', 'history',
                'flux', 'full', 'list', 'variables', 'stat',
                'birds', 'spectra']


class TaskUVPlot (TaskBase):
    # XXX FIXME: there is a 'log' option, but that would conflict
    # with the 'log' parameter.
    
    _name = 'uvplt'
    _keywords = ['vis', 'line', 'device', 'axis', 'size', 'select',
                 'stokes', 'xrange', 'yrange', 'average', 'hann',
                 'inc', 'nxy', 'log', 'comment']
    _options = ['nocal', 'nopol', 'nopass', 'nofqav', 'nobase',
                '2pass', 'scalar', 'avall', 'unwrap', 'rms',
                'mrms', 'noerr', 'all', 'flagged', 'nanosec',
                'days', 'hours', 'seconds', 'xind', 'yind',
                'equal', 'zero', 'symbols', 'nocolour', 'dots',
                'source', 'inter']


class TaskInvert (TaskBase):
    _keywords = ['vis', 'map', 'beam', 'select', 'stokes',
                 'robust', 'cell', 'fwhm', 'imsize', 'offset',
                 'sup', 'line', 'ref', 'mode', 'slop']
    _options = ['nocal', 'nopol', 'nopass', 'double', 'systemp',
                'mfs', 'sdb', 'mosaic', 'imaginary', 'amplitude',
                'phase']


class TaskClean (TaskBase):
    _keywords = ['map', 'beam', 'out', 'niters', 'region',
                 'gain', 'cutoff', 'phat', 'minpatch',
                 'speed', 'mode', 'clip', 'model']
    _options = ['negstop', 'positive', 'asym', 'pad']


class TaskRestore (TaskBase):
    _name = 'restor'
    _keywords = ['map', 'beam', 'model', 'out', 'mode', 'fwhm',
                 'pa']


class TaskImStat (TaskBase):
    _keywords = ['in_', 'region', 'plot', 'cutoff',
                 'beam', 'axes', 'device', 'log']
    _options = ['tb', 'hanning', 'boxcar', 'deriv', 'noheader',
                'nolist', 'eformat', 'guaranteespaces', 'xmin',
                'xmax', 'ymin', 'ymax', 'title', 'style']


class TaskImHead (TaskBase):
    _keywords = ['in_', 'key', 'log']


class TaskIMom (TaskBase):
    _keywords = ['in_', 'region', 'min', 'max', 'log']
    _options = ['skew', 'clipmean', 'clip1sigma']

    
class TaskImFit (TaskBase):
    _keywords = ['in_', 'region', 'clip', 'object', 'spar',
                 'fix', 'out']
    _options = ['residual']

    
class TaskUVAver (TaskBase):
    _keywords = ['vis', 'select', 'line', 'ref', 'stokes',
                 'interval', 'out']
    _options = ['nocal', 'nopass', 'nopol', 'relax',
                'vector', 'scalar', 'scavec']


class TaskGPCopy (TaskBase):
    _keywords = ['vis', 'out', 'mode']
    _options = ['nopol', 'nocal', 'nopass']


class TaskMSelfCal (TaskBase):
    _keywords = ['vis', 'select', 'model', 'clip', 'interval',
                 'minants', 'refant', 'flux', 'offset', 'line',
                 'out']
    _options = ['amplitude', 'phase', 'smooth', 'polarized',
                'mfs', 'relax', 'apriori', 'noscale', 'mosaic',
                'verbose']


class TaskSelfCal (TaskBase):
    _keywords = ['vis', 'select', 'model', 'clip', 'interval',
                 'minants', 'refant', 'flux', 'offset', 'line',
                 'out']
    _options = ['amplitude', 'phase', 'smooth', 'polarized',
                'mfs', 'relax', 'apriori', 'noscale', 'mosaic']


class TaskPutHead (TaskBase):
    _name = 'puthd'
    _keywords = ['in_', 'value', 'type']


class TaskGPPlot (TaskBase):
    _name = 'gpplt'
    _keywords = ['vis', 'device', 'log', 'yaxis', 'nxy',
                 'select', 'yrange']
    _options = ['gains', 'xygains', 'xbyygain',
                'polarization', 'delays', 'speccor',
                'bandpass', 'dots', 'dtime', 'wrap']


class TaskPrintHead (TaskBase):
    _name = 'prthd'
    _keywords = ['in_', 'log']
    _options = ['brief', 'full']


class TaskClosure (TaskBase):
    _keywords = ['vis', 'select', 'line', 'stokes', 'device',
                 'nxy', 'yrange', 'interval']
    _options = ['amplitude', 'quad', 'avall', 'notriple', 'rms',
                'nocal', 'nopol', 'nopass']


class TaskUVFlag (TaskBase):
    _keywords = ['vis', 'select', 'line', 'edge', 'flagval', 'log' ]
    _options = ['noapply', 'none', 'brief', 'indicative', 'full',
                'noquery', 'hms', 'decimal']


class TaskUVSpec (TaskBase):
    _keywords = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
                 'offset', 'axis', 'yrange', 'device', 'nxy', 'log']
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all']


class TaskUVSort (TaskBase):
    _keywords = ['vis', 'select', 'line', 'out']


class TaskMfCal (TaskBase):
    _keywords = ['vis', 'line', 'stokes', 'edge', 'select', 'flux',
                 'refant', 'minants', 'interval', 'tol']
    _options = ['delay', 'nopassol', 'interpolate', 'oldflux', 'noxyalign']


class TaskUVIndex (TaskBase):
    _keywords = ['vis', 'interval', 'refant', 'log']
    _options = ['mosaic']


class TaskUVCat (TaskBase):
    _keywords = ['vis', 'select', 'stokes', 'out']
    _options = ['nocal', 'nopass', 'nopol', 'nowide', 'nochannel',
                'unflagged']


class SmaUVPlot (TaskBase):
    # XXX FIXME: there is a 'log' option, but that would conflict
    # with the 'log' parameter.
    
    _name = 'smauvplt'
    _keywords = ['vis', 'line', 'device', 'axis', 'size', 'select',
                 'stokes', 'xrange', 'yrange', 'average', 'hann',
                 'inc', 'nxy', 'log', 'comment', 'dotsize', 'filelabel']
    _options = ['nocal', 'nopol', 'nopass', 'nofqav', 'nobase',
                '2pass', 'scalar', 'avall', 'unwrap', 'rms',
                'mrms', 'noerr', 'all', 'flagged', 'nanosec',
                'days', 'hours', 'seconds', 'xind', 'yind',
                'equal', 'zero', 'symbols', 'nocolor', 'dots',
                'source', 'inter', 'notitle']


class SmaUVSpec (TaskBase):
    _name = 'smauvspec'
    
    _keywords = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
                 'offset', 'catpath', 'vsource', 'veltype', 'veldef',
                 'strngl', 'axis', 'yrange', 'dotsize', 'device',
                 'nxy', 'log']
    
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all',
                'jplcat', 'restfreq']


class TaskUVGen (TaskBase):
    _keywords = ['source', 'ant', 'baseunit', 'telescop', 'corr',
                 'spectra', 'time', 'freq', 'radec', 'harange',
                 'ellim', 'stokes', 'polar', 'leakage', 'zeeman',
                 'lat', 'cycle', 'pbfwhm', 'center', 'gnoise',
                 'pnoise', 'systemp', 'tpower', 'jyperk', 'out']


class TaskUVGen2 (TaskBase):
    _keywords = ['source', 'ant', 'baseunit', 'telescop', 'corr',
                 'spectra', 'time', 'freq', 'radec', 'harange',
                 'ellim', 'stokes', 'polar', 'leakage', 'zeeman',
                 'lat', 'cycle', 'pbfwhm', 'center', 'gnoise',
                 'pnoise', 'systemp', 'tpower', 'jyperk', 'out']

    
class TaskUVCal (TaskBase):
    _keywords = ['vis', 'select', 'radec', 'badchan', 'endchan', 'nave',
                 'sigma', 'scale', 'offset', 'model', 'polcal', 'polcode',
                 'parot', 'seeing', 'out']

    _options = ['nocal', 'nopass', 'nopol', 'nowide', 'nochannel',
                'unflagged', 'contsub', 'conjugate', 'fxcal', 'hanning',
                'linecal', 'parang', 'passband', 'noisecal', 'uvrotate',
                'avechan', 'slope', 'holo']


class TaskUVFlux (TaskBase):
    _keywords = ['vis', 'select', 'line', 'stokes', 'offset']
    _options = ['nocal', 'nopol', 'nopass', 'uvpol']


class TaskUVFit (TaskBase):
    _keywords = ['vis', 'stokes', 'line', 'select', 'object',
                 'spar', 'fix', 'out']
    _options = ['residual']


class TaskUVModel (TaskBase):
    _keywords = ['vis', 'model', 'select', 'polcor', 'clip', 'flux',
                 'offset', 'line', 'sigma', 'out']
    _options = ['add', 'subtract', 'multiply', 'divide', 'replace', 'flag',
                'polcal', 'poleak', 'unflag', 'autoscale', 'apriori', 'imhead',
                'selradec', 'polarized', 'mfs', 'zero', 'imag']


class SmaMfCal (TaskBase):
    _name = 'smamfcal'
    _keywords = ['vis', 'line', 'edge', 'flux', 'refant', 'minants',
                 'interval', 'weight', 'smooth', 'polyfit', 'tol']
    _options = ['delay', 'nopassol', 'interpolate', 'oldflux',
                'msmooth', 'opolyfit', 'wrap', 'averrll']


class TaskGPCal (TaskBase):
    _keywords = ['vis', 'select', 'line', 'flux', 'refant', 'minants',
                 'interval', 'tol', 'xyphase']
    _options = ['xyvary', 'qusolve', 'oldflux', 'circular', 'nopol',
                'noxy', 'nopass', 'noamphase', 'xyref', 'polref', 'vsolve']


class TaskMaths (TaskBase):
    _keywords = ['exp', 'mask', 'region', 'out', 'imsize', 'xrange',
                 'yrange', 'zrange']
    _options = ['grow', 'unmask']


class TaskImGen (TaskBase):
    _keywords = ['in_', 'out', 'factor', 'object', 'spar', 'imsize',
                 'cell', 'radec', 'seed']
    _options = ['totflux']


class TaskLinMos (TaskBase):
    _keywords = ['in_', 'out', 'rms']
    _options = ['taper', 'sensitivity', 'gain']


class TaskImSub (TaskBase):
    _keywords = ['in_', 'out', 'region', 'incr']


class TaskImMedian (TaskBase):
    _keywords = ['in_', 'out', 'size']


class TaskRegrid (TaskBase):
    _keywords = ['in_', 'out', 'axes', 'tin', 'desc', 'project',
                 'rotate', 'tol']
    _options = ['noscale', 'offset', 'nearest', 'galeqsw', 'equisw']


class TaskSFind (TaskBase):
    _keywords = ['in_', 'type', 'region', 'xybin', 'chan', 'slev',
                 'levs', 'range', 'cutoff', 'rmsbox', 'alpha',
                 'xrms', 'device', 'nxy', 'labtyp', 'logfile',
                 'csize']
    _options = ['fiddle', 'wedge', '3value', '3pixel', 'grid', 'noerase',
                'unequal', 'mark', 'nofit', 'asciiart', 'auto', 'negative',
                'pbcorr', 'oldsfind', 'fdrimg', 'sigmaimg', 'rmsimg',
                'normimg', 'kvannot', 'fdrpeak', 'allpix', 'psfsize']


class TaskFFT (TaskBase):
    _keywords = ['rin', 'iin', 'sign', 'center', 'rout', 'iout', 'mag', 'phase']


class TaskFits (TaskBase):
    _keywords = 'in_ op out line region select stokes velocity'.split ()
    _options = ('compress nochi lefty varwt blcal nocal nopol '
                'nopass rawdss nod2').split ()
