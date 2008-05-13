# Wrapper for invoking MIRIAD scripts

import sys, os, re, math
import os.path
from os.path import join
from subprocess import Popen, PIPE, STDOUT
import miriad

_pager = 'less'
_defaultDevice = '/xs'
_bindir = None
_childenvCopylist = ['DISPLAY', 'EDITOR', 'HOME', 'LANG', 'LOGNAME',
                     'PAGER', 'PATH', 'SHELL', 'TERM', 'UID', 'USER',
                     'VISUAL']

# Programmatically setting environment variables to find
# the Miriad executables and have them run correctly. We clear
# most environment variables; Miriad programs are essentially
# standalone, so we're only going to need a fairly constrained
# set of variables.

_childenv = {}

for var in _childenvCopylist:
    if var in os.environ:
        _childenv[var] = os.environ[var]

for (key, val) in os.environ.iteritems ():
    # We might want to copy over other things: LD_*, maybe?
    if key.startswith ('MIR'):
        _childenv[key] = val;
    if key.startswith ('PGPLOT'):
        _childenv[key] = val;

del var

def addEnvironmentClassic (home='/indirect/hp/wright/miriad/mir4',
                           hosttype='linux'):
    global _bindir, _childenv
    
    #home = '/linux-apps4/miriad3'

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

def addEnvironmentAutotools (home='/l/pkwill/opt/miriad-x86_64-Linux-suse10.1'):
    global _bindir, _childenv
    
    #home = '/linux-apps4/miriad3'
    #home = '/indirect/hp/wright/miriad/mir4'
    #home = '/l/pkwill/opt/miriad-x86_64-Linux-suse10.1'

    # FIXME: we pretty much need the source tree. The autotools setup
    # needs to be rethought a bit.
    
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
        # this is OK if the python shell was run with the Miriad programs
        # already living somewhere in $PATH.
        return name
    
    return join (_bindir, name)

# I find this class useful in interactive environments -- you can
# set Holder.foo = bar, and tab-complete on the foo later. So, basically
# a glorified hashtable, but convenient to use from time to time.
#
# We are totally abusing __repr__ here, but in interactive environments,
# I think this is more convenient.

class Holder (object):
    def __str__ (self): return str (self.__dict__)
    def __repr__ (self): return str (self)

class Options (Holder):
    def asHash (self):
        # self.__dict__ has exactly what we want: the extra properties
        # that have been set on our instance.
        return self.__dict__

    def initFrom (self, task):
        for p in task._params or []:
            setattr (self, p, getattr (task, p))
        for o in task._options or []:
            setattr (self, o, getattr (task, o))

# The MIRIAD task running framework

class DefaultedTaskType (type):
    # YES! I get to write a metaclass! This looks at the
    # _params and _options members and fills in default values
    # in the class dictionary for any parameters or options
    # not already specified. So if there is a 'foo' parameter,
    # it creates an entry in the class dictionary of 'foo = None'.
    # This allows TaskBase to just getattr() any class parameter,
    # and makes tab-completing easy.
    #
    # We also guess the task name if _name is not set. Cute.
    
    def __init__ (cls, name, bases, dict):
        type.__init__ (cls, name, bases, dict)
        
        # TaskBase doesn't get any special treatment
        if name == 'TaskBase': return 
        
        if '_name' not in dict:
            if name.startswith ('Task'):
                setattr (cls, '_name', name[4:].lower ())
            else:
                raise Exception ('Task class must define a _name member')

        for p in dict.get ('_params') or []:
            if p in dict: continue

            setattr (cls, p, None)

        for o in dict.get ('_options') or []:
            if o in dict: continue
            
            setattr (cls, o, False)

class TaskBase (object):
    """Generic MIRIAD task launcher class. The parameters to commands
    are taken from fields in the object; those with names contained in
    self._params are added to the command line in the style
    '[member name]=[member value]'. The field self._name is the name of
    the MIRIAD task to be run.

    If an element in self._params ends with an underscore, the key name
    associated with that element has the underscore stripped off. This
    allows parameters corresponding to Python keywords to be passed to
    MIRIAD programs (eg, _params = ['in_']).

    IDEA/FIXME/TODO: if an element in _params begins with *, ensure that
    it is not None before running the task.
    """

    __metaclass__ = DefaultedTaskType
    
    _name = None
    _params = None
    _options = None
    _cleanups = None

    # These are extra fake parameters that affect how the task is run. I
    # prefix special interactive-only features, such as these fake parameters,
    # with an 'x'.
    #
    # xint  - Run the task interactively: don't redirect its standard input and
    #         output.
    # xabbr - Create a short-named symbolic link to any data inputs (keyword 'in'
    #         or 'vis'). Many plots include the filename in the plot titles, and
    #         long filenames make it impossible to read the useful information.
    # xhelp - Don't actually run the command; show the help for the task to be
    #         run, and print out the command that would have been run.
    # xtra  - Either none, or an instance of Options. If it is an instance,
    #         copy over all the parameters stored in the instance before running.
    #
    # All of these fake parameters are cleared after the task has been run once.
    # Note that the values set by providing xtra will be preserved, however.
    
    xint = False
    xabbr = False
    xhelp = False
    xtra = None
    
    def __init__ (self, **kwargs):
        self.setArgs (**kwargs)

    def setArgs (self, **kwargs):
        for (key, val) in kwargs.iteritems ():
            setattr (self, key, val)
        return self

    def prepCommand (self):
        # If xabbr is True, create symbolic links to any data
        # set inputs with short names, thereby making the output
        # of things like uvplt much cleaner.

        cmd = [_mirBinPath (self._name)]
        options = []
        dindex = 0

        # extra params to set first? 

        if self.xtra is not None:
            h = self.xtra.asHash ()

            # We disallow this because snarf () and run() do some processing
            # of these options before prepCommand is called. So if we allowed
            # them we'd get inconsistent handling of the options depending on
            # how exactly you invoked the task. That's bad.
            
            if 'xint' in h: raise Exception ('Cannot set xint in Options, sorry')
            if 'xhelp' in h: raise Exception ('Cannot set xhelp in Options, sorry')
            
            self.setArgs (**h)
        
        # Options
        
        for opt in self._options or []:
            val = getattr (self, opt)

            if val is None: continue
            
            if isinstance (val, bool):
                if val: options.append (opt)
            else:
                options.append (opt)

                if not hasattr (val, '__iter__'):
                    options.append (str (val))
                else:
                    for x in val:
                        options.append (str (x))

        if len (options) > 0:
            cmd.append ('options=%s' % (','.join (options)))

        # Parameters
        
        for name in self._params or []:
            if name[-1] == '_': key = name[:-1]
            else: key = name
            
            val = getattr (self, name)

            if self.xabbr and (key == 'in' or key == 'vis'):
                data = val
                val = 'd%d' % dindex
                dindex += 1
                os.symlink (str (data), val)

                if self._cleanups: self._cleanups.append (val)
                else: self._cleanups = [val]
                
            if val is not None: cmd.append ("%s=%s" % (key, val))

        self.cmdline = ' '.join (cmd)
        return cmd

    def _cleanup (self):
        # Reset these
        self.xint = self.xabbr = self.xhelp = False
        self.xtra = None
        
        if not self._cleanups: return

        for f in self._cleanups:
            print 'xabbr cleanup: unlinking %s' % (f, )
            os.unlink (f)

        self._cleanups = None
        
    def launch (self, **kwargs):
        cmd = self.prepCommand ()
        self._was_xint = self.xint

        miriad.trace (cmd)
        
        if self.xint:
            # Run the program interactively.
            self.proc = Popen (cmd,
                               shell=False, close_fds=True, env=_childenv,
                               **kwargs)
        else:
            # Set stdin to /dev/null so that the program can't
            # block waiting for user input, and capture output.

            self.proc = Popen (cmd,
                               stdin=file (os.devnull, 'r'), stdout=PIPE, stderr=PIPE,
                               shell=False, close_fds=True, env=_childenv,
                               **kwargs)

    def checkFail (self, stderr=None):
        if not stderr: stderr = self.proc.stderr
        if isinstance (stderr, basestring):
            stderr = stderr.splitlines ()
            
        if self.proc.returncode:
            print 'Ran: %s' % self.cmdline
            print 'Task "%s" failed with exit code %d! It printed:' % \
                  (self._name, self.proc.returncode)

            if self._was_xint:
                print '\t[Task was run interactively, see output above]'
            else:
                for x in stderr: print '\t', x.strip ()
                
            #raise CalledProcessError (self.proc.returncode, self._name)
            raise OSError ('Command %s returned exit code %d' % (self._name, self.proc.returncode))

    def run (self, **kwargs):
        if self.xhelp:
            self.xHelp ()
            print 'Would run: '
            print '\t', "'" + "' '".join (self.prepCommand ()) + "'"
            
            # prepCommand creates the abbr symlinks, and besides
            # we want to reset xhelp et al.
            self._cleanup ()
            
            return self

        ignorefail = False
        
        try:
            try:
                self.launch (**kwargs)
                self.proc.wait ()
            except KeyboardInterrupt:
                # If the subprocess is control-C'ed, we'll get this exception.
                # Wait on the proc again to reap it for real. If we were interactive,
                # don't throw the exception: the user is dealing with things
                # manually and knows what just happened. If not interactive, raise
                # it, because maybe there is "for d in [100 datasets]: longTask(d)",
                # and we should bail early if that's what's been asked for.
            
                self.proc.wait ()
                ignorefail = self._was_xint
        finally:
            self._cleanup ()

        if not ignorefail: self.checkFail ()

        return self

    def snarf (self, send=None, **kwargs):
        if self.xint:
            raise Exception ('Cannot run a program interactively and also ' \
                             'snarf its output!')
        
        self.launch (**kwargs)
        (stdout, stderr) = self.proc.communicate (send)
        self._cleanup ()
        self.checkFail (stderr)
        return (stdout.splitlines (), stderr.splitlines ())

    def what (self):
        """Print some useful information about the last process that
        was invoked. This is useful if a command doesn't work for some
        nonobvious reason."""
        
        print 'Ran: %s' % self.cmdline
        print 'Task "%s", return code %d' % (self._name, self.proc.returncode)

        if self._was_xint:
            print 'Program was run interactively, so cannot recover its output'
        else:
            print 'Standard output:'
            for x in self.proc.stdout: print '\t', x.strip ()
            print 'Standard error:'
            for x in self.proc.stderr: print '\t', x.strip ()

    def cm_xHelp (klass):
        args = [_mirBinPath ('mir.help'), klass._name]
        proc = Popen (args, shell=False, close_fds=True, env=_childenv)
        proc.wait ()

    xHelp = classmethod (cm_xHelp)

    def xStatus (self):
        # Parameters
        
        for name in self._params or []:
            if name[-1] == '_': key = name[:-1]
            else: key = name
            
            val = getattr (self, name)

            if val: print "%20s = %s" % (key, val)
        
        # Options
        
        for opt in self._options or []:
            val = getattr (self, opt)

            if val is None: continue
            
            if isinstance (val, bool):
                if val: print '%20s = True' % opt
            else:
                print '%20s = %s' % (opt, val)

        return self

    def xrun (self):
        self.xint = True
        return self.run ()

class TaskCgDisp (TaskBase):
    _params = ['device', 'in_', 'type', 'region', 'xybin', 'chan',
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
    _params = ['vis', 'select', 'line', 'scale', 'recnum', 'log']
    _options = ['brief', 'data', 'average', 'allan', 'history',
                'flux', 'full', 'list', 'variables', 'stat',
                'birds', 'spectra']

class TaskUVPlot (TaskBase):
    # XXX FIXME: there is a 'log' option, but that would conflict
    # with the 'log' parameter.
    
    _name = 'uvplt'
    _params = ['vis', 'line', 'device', 'axis', 'size', 'select',
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
    _params = ['vis', 'map', 'beam', 'select', 'stokes',
               'robust', 'cell', 'fwhm', 'imsize', 'offset',
               'sup', 'line', 'ref', 'mode', 'slop']
    _options = ['nocal', 'nopol', 'nopass', 'double', 'systemp',
                'mfs', 'sdb', 'mosaic', 'imaginary', 'amplitude',
                'phase']

class TaskClean (TaskBase):
    _params = ['map', 'beam', 'out', 'niters', 'region',
               'gain', 'cutoff', 'phat', 'minpatch',
               'speed', 'mode', 'clip']
    _options = ['negstop', 'positive', 'asym', 'pad']

class TaskRestore (TaskBase):
    _name = 'restor'
    _params = ['map', 'beam', 'model', 'out', 'mode', 'fwhm',
               'pa']

class TaskImStat (TaskBase):
    _params = ['in_', 'region', 'plot', 'cutoff',
               'beam', 'axes', 'device', 'log']
    _options = ['tb', 'hanning', 'boxcar', 'deriv', 'noheader',
                'nolist', 'eformat', 'guaranteespaces', 'xmin',
                'xmax', 'ymin', 'ymax', 'title', 'style']

class TaskImHead (TaskBase):
    _params = ['in_', 'key', 'log']

    def snarfOne (self, key):
        self.key = key
        (stdout, stderr) = self.snarf ()
        
        if len(stdout) != 1:
            raise Exception ('Unexpected output from IMHEAD: %s' % \
                             stdout + '\nStderr: ' + stderr)

        return stdout[0].strip ()

class TaskIMom (TaskBase):
    _params = ['in_', 'region', 'min', 'max', 'log']
    _options = ['skew', 'clipmean', 'clip1sigma']
    
class TaskImFit (TaskBase):
    _params = ['in_', 'region', 'clip', 'object', 'spar',
               'fix', 'out']
    _options = ['residual']
    
class TaskUVAver (TaskBase):
    _params = ['vis', 'select', 'line', 'ref', 'stokes',
               'interval', 'out']
    _options = ['nocal', 'nopass', 'nopol', 'relax',
                'vector', 'scalar', 'scavec']

class TaskGPCopy (TaskBase):
    _params = ['vis', 'out', 'mode']
    _options = ['nopol', 'nocal', 'nopass']

class TaskMSelfCal (TaskBase):
    _params = ['vis', 'select', 'model', 'clip', 'interval',
               'minants', 'refant', 'flux', 'offset', 'line',
               'out']
    _options = ['amplitude', 'phase', 'smooth', 'polarized',
                'mfs', 'relax', 'apriori', 'noscale', 'mosaic',
                'verbose']

class TaskSelfCal (TaskBase):
    _params = ['vis', 'select', 'model', 'clip', 'interval',
               'minants', 'refant', 'flux', 'offset', 'line',
               'out']
    _options = ['amplitude', 'phase', 'smooth', 'polarized',
                'mfs', 'relax', 'apriori', 'noscale', 'mosaic',
                'verbose']

class TaskPutHead (TaskBase):
    _name = 'puthd'
    _params = ['in_', 'value', 'type']

class TaskGPPlot (TaskBase):
    _name = 'gpplt'
    _params = ['vis', 'device', 'log', 'yaxis', 'nxy',
               'select', 'yrange']
    _options = ['gains', 'xygains', 'xbyygain',
                'polarization', 'delays', 'speccor',
                'bandpass', 'dots', 'dtime', 'wrap']

    device = _defaultDevice

class TaskPrintHead (TaskBase):
    _name = 'prthd'
    _params = ['in_', 'log']
    _options = ['brief', 'full']

class TaskClosure (TaskBase):
    _params = ['vis', 'select', 'line', 'stokes', 'device',
               'nxy', 'yrange', 'interval']
    _options = ['amplitude', 'quad', 'avall', 'notriple', 'rms',
                'nocal', 'nopol', 'nopass']

    device = _defaultDevice

class TaskUVFlag (TaskBase):
    _params = ['vis', 'select', 'line', 'edge', 'flagval', 'log' ]
    _options = ['noapply', 'none', 'brief', 'indicative', 'full',
                'noquery', 'hms', 'decimal']

class TaskUVSpec (TaskBase):
    _params = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
               'offset', 'axis', 'yrange', 'device', 'nxy', 'log']
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all']

    device= _defaultDevice

class TaskUVSort (TaskBase):
    _params = ['vis', 'select', 'line', 'out']

class TaskMfCal (TaskBase):
    _params = ['vis', 'line', 'stokes', 'edge', 'select', 'flux',
               'refant', 'minants', 'interval', 'tol']
    _options = ['delay', 'nopassol', 'interpolate', 'oldflux']

class TaskUVIndex (TaskBase):
    _params = ['vis', 'interval', 'refant', 'log']
    _options = ['mosaic']

class TaskUVCat (TaskBase):
    _params = ['vis', 'select', 'stokes', 'out']
    _options = ['nocal', 'nopass', 'nopol', 'nowide', 'nochannel',
                'unflagged']

class SmaUVPlot (TaskBase):
    # XXX FIXME: there is a 'log' option, but that would conflict
    # with the 'log' parameter.
    
    _name = 'smauvplt'
    _params = ['vis', 'line', 'device', 'axis', 'size', 'select',
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
    
    _params = ['vis', 'select', 'line', 'stokes', 'interval', 'hann',
               'offset', 'catpath', 'vsource', 'veltype', 'veldef',
               'strngl', 'axis', 'yrange', 'dotsize', 'device',
               'nxy', 'log']
    
    _options = ['nocal', 'nopass', 'nopol', 'ampscalar', 'rms',
                'nobase', 'avall', 'dots', 'flagged', 'all',
                'jplcat', 'restfreq']

    device= _defaultDevice

class TaskUVGen (TaskBase):
    _params = ['source', 'ant', 'baseunit', 'telescop', 'corr',
               'spectra', 'time', 'freq', 'radec', 'harange',
               'ellim', 'stokes', 'polar', 'leakage', 'zeeman',
               'lat', 'cycle', 'pbfwhm', 'center', 'gnoise',
               'pnoise', 'systemp', 'tpower', 'jyperk', 'out']

class TaskUVGen2 (TaskBase):
    _params = ['source', 'ant', 'baseunit', 'telescop', 'corr',
               'spectra', 'time', 'freq', 'radec', 'harange',
               'ellim', 'stokes', 'polar', 'leakage', 'zeeman',
               'lat', 'cycle', 'pbfwhm', 'center', 'gnoise',
               'pnoise', 'systemp', 'tpower', 'jyperk', 'out']
    
class TaskUVCal (TaskBase):
    _params = ['vis', 'select', 'radec', 'badchan', 'endchan', 'nave',
               'sigma', 'scale', 'offset', 'model', 'polcal', 'polcode',
               'parot', 'seeing', 'out']

    _options = ['nocal', 'nopass', 'nopol', 'nowide', 'nochannel',
                'unflagged', 'contsub', 'conjugate', 'fxcal', 'hanning',
                'linecal', 'parang', 'passband', 'noisecal', 'uvrotate',
                'avechan', 'slope', 'holo']

class TaskUVFlux (TaskBase):
    _params = ['vis', 'select', 'line', 'stokes', 'offset']
    _options = ['nocal', 'nopol', 'nopass', 'uvpol']

class TaskUVFit (TaskBase):
    _params = ['vis', 'stokes', 'line', 'select', 'object',
               'spar', 'fix', 'out']
    _options = ['residual']

class SmaMfCal (TaskBase):
    _name = 'smamfcal'
    _params = ['vis', 'line', 'edge', 'flux', 'refant', 'minants',
               'interval', 'weight', 'smooth', 'polyfit', 'tol']
    _options = ['delay', 'nopassol', 'interpolate', 'oldflux',
                'msmooth', 'opolyfit', 'wrap', 'averrll']

class TaskMaths (TaskBase):
    _params = ['exp', 'mask', 'region', 'out', 'imsize', 'xrange',
               'yrange', 'zrange']
    _options = ['grow', 'unmask']

# These functions operate on single images or single visibilities,
# using several of the tasks defined above.

def getVisRestfreq (vis, **kwargs):
    """Returns the rest frequency of the specified visibility file
    in gigahertz. The data is obtained from the output of the miriad
    prthd task."""
    
    # FIXME: probably breaks with multifreq data! No example
    # files!

    ph = TaskPrintHead (in_=vis, full=True, **kwargs)
    (stdout, stderr) = ph.snarf ()

    sawHead = False
    
    # '  Spectrum  Channels  Freq(chan=1)  Increment  Restfreq     '
    # '      1          1       5.00020     0.011719   5.00000 GHz '
    #  012345678901234567890123456789012345678901234567890123456789'
    #  0         1         2         3         4         5         '
    #                      ^             ^          ^         ^    '

    for line in stdout:
        if 'Restfreq' in line:
            sawHead = True
        elif sawHead:
            if line[56:59] != 'GHz':
                raise Exception ('Restfreq not in GHz???: %s' % line)
            s = line[45:55].strip ()
            return float (s)

    raise Exception ('Unexpected output from prthd task: %s' % stdout)

def getImageDimensions (image, **kwargs):
    imh = TaskImHead (in_=image, **kwargs)

    naxis = int (imh.snarfOne ('naxis'))
    res = []
    
    for i in range (1, naxis + 1):
        res.append (int (imh.snarfOne ('naxis%d' % i)))
    
    return res

def getImageStats (image, **kwargs):
    # FIXME: noheader option seems a little dangerous, if we
    # ever use this for multifreq data.
    ims = TaskImStat (in_=image, noheader=True, **kwargs)
    (stdout, stderr) = ims.snarf ()
        
    if len(stdout) != 2:
        raise Exception ('Unexpected output from IMSTAT: %s' % \
                         stdout + '\nStderr: ' + stderr)

    # ' Total                  Sum      Mean      rms     Maximum   Minimum    Npoints'
    #  0123456789012345678901234567890123456789012345678901234567890123456789012345678'
    #  0         1         2         3         4         5         6         7        '
    #                       ^         ^         ^         ^         ^         ^ 
        
    sum = float (stdout[1][21:31])
    mean = float (stdout[1][31:41])
    rms = float (stdout[1][41:51])
    max = float (stdout[1][51:61])
    min = float (stdout[1][61:71])
    npts = int (stdout[1][71:])
    
    return (sum, mean, rms, max, min, npts)

def getImageMoment (image, **kwargs):
    imom = TaskIMom (in_=image, **kwargs)
    (stdout, stderr) = imom.snarf ()

    # 'Plane:    1   Centroid:  9.00143E+01  9.00160E+01 pixels'
    # 'Plane:    1     Spread:  5.14889E+01  5.15338E+01 pixels'
    #  012345678901234567890123456789012345678901234567890123456
    #  0         1         2         3         4         5      
    #                          ^            ^

    ctr1 = ctr2 = spr1 = spr2 = -1

    for line in stdout:
        if 'Centroid:' in line:
            ctr1 = int (float (line[24:37]))
            ctr2 = int (float (line[37:49]))
        elif 'Spread:' in line:
            spr1 = int (float (line[24:37]))
            spr2 = int (float (line[37:49]))

    if min (ctr1, ctr2, spr1, spr2) < 0:
        raise Exception ('Incomplete output from IMOM task?' + imom.what (stderr=stderr))

    return (ctr1, ctr2, spr1, spr2)

def getImageBeamSize (image, **kwargs):
    imh = TaskImHead (in_=image, **kwargs)

    bmaj = float (imh.snarfOne ('bmaj')) # in radians
    bmin = float (imh.snarfOne ('bmin')) # in radians
    
    return (bmaj, bmin)

def fitImagePoint (image, **kwargs):
    imf = TaskImFit (in_=image, **kwargs)
    imf.object = 'point'
    
    (stdout, stderr) = imf.snarf ()

    rms = max = dx = None
    
    for line in stdout:
        if 'RMS residual' in line:
            a = line.split (' ')
            rms = float (a[3])
        elif 'Peak value:' in line:
            # '  Peak value:                 6.9948E-04 +/-  0.0000'
            # '  Peak value:                  19.07     +/-  8.9466E-02
            #  01234567890123456789123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            max = float (line[30:40])
            err = float (line[45:56])
        elif 'Offset Position' in line:
            # '  Offset Position (arcsec):      -0.186   -37.349
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            dx = float (line[30:40])
            dy = float (line[40:50])
            
    if rms is None or max is None or dx is None:
        raise Exception ('Didn\'t get all info from imfit routine!')

    return (max, err, rms, dx, dy)

def fitImageGaussian (image, **kwargs):
    """Returns: (max, total, rms, maj, min)"""
    
    imf = TaskImFit (in_=image, **kwargs)
    imf.object = 'gaussian'
    
    (stdout, stderr) = imf.snarf ()

    rms = max = total = maj = min = None
    
    for line in stdout:
        if 'RMS residual' in line:
            a = line.split (' ')
            rms = float (a[3])
        elif 'Peak value:' in line:
            # '  Peak value:                 6.9948E-04 +/-  0.0000'
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            max = float (line[30:40])
        elif 'Total integrated' in line:
            # '  Total integrated flux:       1559.'
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            total = float (line[30:40])
        elif 'Major axis' in line:
            # '  Major axis (arcsec):           0.394 +/-  0.009
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            maj = float (line[30:38])
        elif 'Minor axis' in line:
            # '  Minor axis (arcsec):           0.394 +/-  0.009
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            min = float (line[30:38])

    if rms is None or max is None or maj is None \
           or total is None or min is None:
        raise Exception ('Didn\'t get all info from imfit routine!')

    return (max, total, rms, maj, min)

def fitUVPoint (vis, **kwargs):
    uvf = TaskUVFit (vis=vis, **kwargs)
    uvf.object = 'point'
    
    (stdout, stderr) = uvf.snarf ()

    rms = max = dx = None
    
    for line in stdout:
        if 'RMS residual' in line:
            rms = float (line.split (' ')[3])
        elif 'Flux:' in line:
            # '  Flux:                          3.792     +/- 8.62E-02'
            #  01234567890123456789123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            max = float (line[32:42])
            err = float (line[47:58])
        elif 'Offset Position' in line:
            # '  Offset Position (arcsec):      -4.48    -1.33'
            #  012345678901234567890123456789012345678901234567890123456
            #  0         1         2         3         4         5      
            dx = float (line[30:40])
            dy = float (line[40:50])
            
    if rms is None or max is None or dx is None:
        raise Exception ('Didn\'t get all info from imfit routine!')

    return (max, err, rms, dx, dy)
