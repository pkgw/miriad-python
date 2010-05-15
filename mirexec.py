'''mirexec - classes for executing MIRIAD tasks'''

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

import sys, os, re, math
import os.path
from os.path import join
from subprocess import Popen, CalledProcessError, PIPE, STDOUT
import miriad

_defaultDevice = '/xs'

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
    _childenv['PGPLOT_DIR'] = childenv['MIRLIB']

    # Need this to find pgxwin_server if using PGPlot.
    _childenv['PATH'] += ':' + childenv['MIRBIN']

    _childenv['LD_LIBRARY_PATH'] = childenv['MIRLIB']


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

    def __init__ (self, command, **kwargs):
        # Raise a TypeError if command is not iterable.
        iter (command)

        super (MiriadSubprocess, self).__init__ (command, **kwargs)
        self.command = command


    def checkFailNoPipe (self, log=None):
        if self.returncode is None:
            raise StandardError ('Have not yet waited on child process')
        if self.returncode == 0:
            return self

        if log is not None:
            print >>log, 'Task "%s" failed with exit code %d!' % \
                (self.command[0], self.returncode)
            print >>log, 'Command line:', ' '.join (self.command)
            print >>log, 'Task output was not captured; it may be printed above.'

        raise CalledProcessError (self.returncode, ' '.join (self.command))


    def checkFailPipe (self, stdout, stderr, log=None):
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

        raise CalledProcessError (self.returncode, ' '.join (self.command))


    def checkwait (self, failok=False, log=None):
        self.wait ()
        if not failok:
            self.checkFailNoPipe (log)
        return self


    def checkcommunicate (self, send=None, failok=False, log=None):
        stdout, stderr = self.communicate (send)
        if not failok:
            self.checkFailPipe (stdout, stderr, log)
        return stdout, stderr


class TaskBase (object):
    """Generic MIRIAD task launcher class. The parameters to commands
    are taken from fields in the object; those with names contained in
    self._keywords are added to the command line in the style
    '[member name]=[member value]'. The field self._name is the name of
    the MIRIAD task to be run.

    If an element in self._keywords ends with an underscore, the key name
    associated with that element has the underscore stripped off. This
    allows MIRIAD keywords corresponding to Python keywords to be passed to
    MIRIAD programs (eg, _keywords = ['in_']).

    IDEA/FIXME/TODO: if an element in _keywords begins with *, ensure that
    it is not None before running the task.
    """

    __metaclass__ = DefaultedTaskType
    
    _name = None
    _keywords = None
    _options = None

    def __init__ (self, **kwargs):
        self.set (**kwargs)


    def set (self, **kwargs):
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

            if not isinstance (val, basestring):
                # Treat non-string iterable values as lists of items
                # to be joined by commas, as per standard MIRIAD usage.
                try:
                    val = ','.join (str (x) for x in val)
                except TypeError:
                    pass

            cmd.append ("%s=%s" % (key, val))

        return cmd


    def launch (self, **kwargs):
        cmd = self.commandLine ()
        miriad.trace (cmd)
        return MiriadSubprocess (cmd, shell=False, close_fds=True, env=_childenv, **kwargs)


    def launchpipe (self, **kwargs):
        return self.launch (stdin=file (os.devnull, 'r'), stdout=PIPE, stderr=PIPE,
                            **kwargs)


    def launchsilent (self, **kwargs):
        nullout = file (os.devnull, 'w')
        return self.launch (stdin=file (os.devnull, 'r'), stdout=nullout, stderr=nullout,
                            **kwargs)


    def run (self, failok=False, log=None, **kwargs):
        self.launch (**kwargs).checkwait (failok, log)
        return self


    def runsilent (self, failok=False, log=None, **kwargs):
        self.launchsilent (**kwargs).checkwait (failok, log)
        return self


    def snarf (self, send=None, failok=False, log=sys.stderr, **kwargs):
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
    
    device = _defaultDevice


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
                
    device = _defaultDevice


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

    device = _defaultDevice


class TaskPrintHead (TaskBase):
    _name = 'prthd'
    _keywords = ['in_', 'log']
    _options = ['brief', 'full']


class TaskClosure (TaskBase):
    _keywords = ['vis', 'select', 'line', 'stokes', 'device',
                 'nxy', 'yrange', 'interval']
    _options = ['amplitude', 'quad', 'avall', 'notriple', 'rms',
                'nocal', 'nopol', 'nopass']

    device = _defaultDevice


class TaskUVFlag (TaskBase):
    _keywords = ['vis', 'select', 'line', 'edge', 'flagval', 'log' ]
    _options = ['noapply', 'none', 'brief', 'indicative', 'full',
                'noquery', 'hms', 'decimal']


class TaskUVSpec (TaskBase):
    _keywords = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
                 'offset', 'axis', 'yrange', 'device', 'nxy', 'log']
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all']

    device= _defaultDevice


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
                
    device = _defaultDevice


class SmaUVSpec (TaskBase):
    _name = 'smauvspec'
    
    _keywords = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
                 'offset', 'catpath', 'vsource', 'veltype', 'veldef',
                 'strngl', 'axis', 'yrange', 'dotsize', 'device',
                 'nxy', 'log']
    
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all',
                'jplcat', 'restfreq']

    device = _defaultDevice


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
