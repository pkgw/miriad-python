import sys, os
from os.path import join

# Tracing of MIRIAD operations. Almost always used for mirexec
# functions, but we also record delete/copy/rename in Data.

launchTrace = None

def basicTrace ():
    global launchTrace

    def t (cmd):
        print "MIRIAD: '" + "' '".join (cmd) + "'"
        sys.stdout.flush ()
    
    launchTrace = t

def trace (cmd):
    if launchTrace is not None:
        launchTrace (cmd)

__all__ = ['basicTrace', 'trace']

# Fundamental MIRIAD data set object.

predFile = 'predecessor'
mutFile = 'mutations'
sep = '---'

class Data (object):
    def __init__ (self, basedata):
        self.base = basedata

    def __str__ (self):
        return self.base

    def __repr__ (self):
        return '<MIRIAD data, base "%s">' % self.base

    def __eq__ (self, other):
        if other is None: return False
        if not isinstance (other, Data): return False
        return self.realPath () == other.realPath ()

    def __hash__ (self):
        return hash (self.realPath ())
    
    # Low-level attributes
    
    @property
    def exists (self):
        """True if the data specified by this class actually exists.
        (If False, the data corresponding to this object will probably
        be created by the execution of a command.)"""
        return os.path.exists (self.base)

    def checkExists (self):
        if self.exists: return

        raise Exception ('Data set %s does not exist' % self.base)

    def realPath (self):
        return os.path.realpath (self.base)
    
    # Low-level operations
    
    def moveTo (self, dest):
        self.checkExists ()
        dest = str (dest)
        
        trace (['[rename]', 'from=%s' % self, 'to=%s' % dest])
        
        os.rename (self.base, dest)
        self.base = dest

    def copyTo (self, dest):
        self.checkExists ()
        dest = str (dest)

        trace (['[copy]', 'from=%s' % self, 'to=%s' % dest])

        from shutil import copy

        os.mkdir (dest)

        for f in os.listdir (self.base):
            copy (join (self.base, f), join (dest, f))
    
    def delete (self):
        # Silently not doing anything seems appropriate here.
        if not self.exists: return

        trace (['[delete]', 'in=%s' % self])
        
        for e in os.listdir (self.base):
            os.remove (join (self.base, e))
        os.rmdir (self.base)

        # Wipe out this info.
        
        self._mutations = None

    # Programming-related helpers.
    
    def makeVariant (self, name, kind=None):
        if kind is None: kind = Data # for some reason kind=Data barfs.
        if not issubclass (kind, Data): raise Exception ('blarg')

        return kind (self.base + '.' + name)

    def branch (self, name, branchOp, opParams, kind=None):
        branched = self.makeVariant (name, kind)
        branchOps[branchOp] (self, branched, *opParams)
        branched.setPredecessor (self, branchOp, opParams)
        return branched

    _openObj = None

    def _openImpl (self, mode):
        from mirtask import UserDataSet

        if mode == 'r':
            create = False
        elif mode == 'w':
            create = True
        else:
            raise Exception ('Unsupported mode ' + mode)

        return UserDataSet (self, create)
    
    def open (self, mode):
        if self._openObj is not None and self._openObj.isOpen ():
            raise Exception ('Data set %s already open' % self)
        
        self._openObj = self._openImpl (mode)
        return self._openObj
    
    # History and modification tracking stuff.

    def hasPredecessor (self):
        return os.path.exists (join (self.base, predFile))

    def setPredecessor (self, predData, branchOp, opParams):
        f = file (join (self.base, predFile), 'w')
        print >>f, predData.realPath ()
        print >>f, '%s%s%s' % (branchOp, sep, sep.join (opParams))
        f.close ()

    def getPredecessor (self, kind=None):
        if kind is None: kind = Data
        if not issubclass (kind, Data): raise Exception ('blarg2')
        
        try: f = file (join (self.base, predFile), 'r')
        except IOError: return None
            
        predBase = f.readline ().strip ()
        return kind (predBase)

    def getPredInfo (self):
        """Returns: pred-file, branch-op-name, branch-op-params."""
        
        try: f = file (join (self.base, predFile), 'r')
        except IOError: return None
            
        predBase = f.readline ().strip ()
        a = f.readline ().strip ().split (sep)

        return predBase, a[0], tuple (a[1:])

    _mutations = None

    def _loadMutations (self):
        try: f = file (join (self.base, mutFile), 'r')
        except IOError:
            self._mutations = []
            return

        m = []
        
        for line in f:
            a = line.strip ().split (sep)
            
            mutOp = a[0]
            opParams = tuple (a[1:])

            m.append ((mutOp, opParams))

        self._mutations = m
        f.close ()

    def _writeMutations (self):
        f = file (join (self.base, mutFile), 'w')

        for (mutOp, opParams) in self._mutations or []:
            print >>f, '%s%s%s' % (mutOp, sep, sep.join (opParams))

        f.close ()
    
    def getMutations (self):
        if self._mutations is None: self._loadMutations ()

        return self._mutations

    def recordMutation (self, mutOp, opParams):
        if self._mutations is None: self._loadMutations ()
            
        self._mutations.append ((mutOp, opParams))
        self._writeMutations ()

    def reconstruct (self):
        muts = self.getMutations ()
        pred = self.getPredecessor ()

        if pred is None:
            raise Exception ('Can\'t recreate precedecessor-less data!')

        pName, branchOp, brParams = self.getPredInfo ()

        # Check that we have all the necessary ops before deleting ourselves ...

        if branchOp not in branchOps:
            raise Exception ('Unknown branching operation ' + branchOp)
        for (mutOp, mutParams) in muts:
            if mutOp not in mutOps:
                raise Exception ('Unknown mutation operation ' + mutOp)

        # Looks like we're good.

        self._mutations = None
        
        backup = self.makeVariant ('orig')
        trace (['[low-level rename]', 'from=' + self.base, 'to=' + backup.base])
        os.rename (self.base, backup.base)
        
        try:
            branchOps[branchOp] (pred, self, *brParams)

            for (mutOp, mutParams) in muts:
                mutOps[mutOp] (self, *mutParams)
        except Exception:
            self.delete ()
            trace (['[low-level rename]', 'from=' + backup.base, 'to=' + self.base])
            os.rename (backup.base, self.base)
            raise

        backup.delete ()

    # Interactive helpers.

    def stack (self):
        self.checkExists ()
        
        data = self
        c = 0
        
        while data is not None:
            print str (data)
            
            for (mutOp, opParams) in data.getMutations ():
                print '   %2d   %9s : (%s)' % (c, mutOp, ', '.join (opParams))
                c += 1

            next = data.getPredecessor ()

            if next is not None:
                pred, branchOp, opParams = data.getPredInfo ()
                print '   %2d * %9s : (%s)' % (c, branchOp, ', '.join (opParams))
                c += 1

            data = next
            
        print '   %2d # --------- : [Raw observations]' % (c, )

# Branch and mutation operations.
# These should be hashtables of opName -> opFunc
# If opFunc is for a mutation, it is invoked opFunc (data, *opParams)
# If it's for a branch, it's invoked opFunc (src, dest, *opParams)
# If a mutation, it should call recordMutation on data at some point;
# if a branch, it should call setPredecessor on dest at some point.

branchOps = {}
mutOps = {}

__all__ += ['Data', 'branchOps', 'mutOps']

# Visdata

def paramConvert (**params):
    return tuple ('%s=%s' % t for t in params.iteritems ())

def paramRecover (items):
    params = {}

    for s in items:
        name, val = s.split ('=', 1)
        params[name] = val

    return params

def _catOperation (data, dest, *params):
    data.checkExists ()

    from mirexec import TaskUVCat

    paramDict = paramRecover (params)
    TaskUVCat (vis=data, out=dest, **paramDict).run ()
    dest.setPredecessor (data, 'uvcat', params)
        
def _averOperation (data, dest, *params):
    data.checkExists ()

    from mirexec import TaskUVAver

    paramDict = paramRecover (params)
    TaskUVAver (vis=data, out=dest, **paramDict).run ()
    dest.setPredecessor (data, 'uvaver', params)
        
def _flagOperation (data, select, line, flagval):
    data.checkExists ()
    from mirexec import TaskUVFlag

    if select == '': sParam = None
    else: sParam = select
        
    if line == '': lParam = None
    else: lParam = line
        
    TaskUVFlag (vis=data, select=sParam, line=lParam, flagval=flagval).run ()
    data.recordMutation ('uvflag', (select, line, flagval))

def _multiFlagOperation (data, filename):
    data.checkExists ()
    from mirexec import TaskUVFlag

    f = file (filename, 'r')
    t = TaskUVFlag (vis=data)
    first = True
    
    for l in f:
        if first:
            if l[0] != '#':
                raise Exception ('first line doesn\'t begin with # in ' + filename)
            first = False
            continue
        
        a = l.strip ().split (sep)
        if len (a) != 3: raise Exception ('Unexpected line: ' + l.strip ())

        if len (a[0]): t.select = a[0]
        else: t.select = None
        
        if len (a[1]): t.line = a[1]
        else: t.line = None

        t.flagval = a[2]

        t.run ()

    data.recordMutation ('multiflag', (filename, ))

        
def _smamfcalOperation (data, *params):
    data.checkExists ()

    from mirexec import SmaMfCal

    paramDict = paramRecover (params)
    SmaMfCal (vis=data, **paramDict).run ()
    dest.recordMutation (data, 'smamfcal', params)

def _selfcalOperation (data, *params):
    data.checkExists ()

    from mirexec import TaskSelfCal

    paramDict = paramRecover (params)
    TaskSelfCal (vis=data, **paramDict).run ()
    dest.recordMutation (data, 'selfcal', params)

branchOps['uvcat'] = _catOperation
branchOps['uvaver'] = _averOperation
mutOps['uvflag'] = _flagOperation
mutOps['multiflag'] = _multiFlagOperation
mutOps['smamfcal'] = _smamfcalOperation
mutOps['selfcal'] = _selfcalOperation

class VisData (Data):
    def apply (self, task, **params):
        task.vis = self
        task.setArgs (**params)
        return task

    def _openImpl (self, mode):
        from mirtask import UVDataSet
        return UVDataSet (self, mode)

    def readLowlevel (self, saveFlags, **kwargs):
        from mirtask import uvdat
        return uvdat.readFileLowlevel (self.base, saveFlags, **kwargs)
    
    # Not-necessarily-interactive operations

    def catTo (self, dest, **params):
        _catOperation (self, dest, *paramConvert (**params))
    
    def averTo (self, dest, interval, **params):
        _averOperation (self, dest, *paramConvert (interval=interval, **params))
    
    # Interactive helpers

    def xApply (self, task, **params):
        task.vis = self
        task.xint = True
        task.setArgs (**params)
        return task

    def xPlot (self, **params):
        self.checkExists ()
        from mirexec import SmaUVPlot
        return self.xApply (SmaUVPlot (), **params)

    def xSpec (self, **params):
        self.checkExists ()
        from mirexec import SmaUVSpec
        return self.xApply (SmaUVSpec (), **params)

    # Flagging

    def fGeneric (self, select, line=None, flagval=True):
        if flagval: flagval = 'f'
        else: flagval = 'u'

        if select is None: select = ''
        
        if line is None: line = ''
        
        _flagOperation (self, select, line, flagval)

    def fAnt (self, polStr, ant, flagval=True):
        self.fGeneric ('pol(%s),ant(%d)' % (polStr, ant), None, flagval)

    def fBL (self, polStr, ant1, ant2, flagval=True):
        if ant1 > ant2:
            ant1, ant2 = ant2, ant1

        if ant1 == ant2:
            self.fAnt (ant1, flagval)
        else:
            self.fGeneric ('pol(%s),ant(%d)(%d)' % (polStr, ant1, ant2), None, flagval)

    def fChans (self, start, count, flagval=True):
        self.fGeneric (None, 'chan,%d,%d' % (count, start), flagval)

    def fMulti (self, file):
        _multiFlagOperation (self, file)

    # Other mutations

    def smaMfCal (self, **params):
        _smamfcalOperation (self, *paramConvert (**params))

    def selfCal (self, **params):
        _selfcalOperation (self, *paramConvert (**params))

__all__ += ['VisData']

# Image data

class ImData (Data):
    def apply (self, task, **params):
        task.in_ = self
        task.setArgs (**params)
        return task

    # Interactive helpers

    def xApply (self, task, **params):
        task.in_ = self
        task.xint = True
        task.setArgs (**params)
        return task

    def xShow (self, **params):
        self.checkExists ()
        from mirexec import TaskCgDisp
        
        t = TaskCgDisp (in_='%s,%s' % (self.base, self.base),
                        type='contour,pix', labtyp='hms',
                        beamtyp='b,l', wedge=True, csize='0.6,1')
        return t
    
    def xShowFit (self, kind='p', **params):
        self.checkExists ()
        from mirexec import TaskImFit, TaskCgDisp
        
        model = self.makeVariant ('fitmodel', ImData)
        if model.exists:
            raise Exception ('Model file %s already exists?' % model)
        
        imf = TaskImFit (in_=self, out=model, **params)
        if kind == 'p':
            imf.object = 'point'
        elif kind == 'g':
            imf.object = 'gaussian'
        elif kind == 'b':
            imf.object = 'beam'
        else:
            raise Exception ('Unknown fit kind ' + kind)

        imf.run ()
        model.xShow (**params).run ()
        model.delete ()
    
    def xShowFitResidual (self, kind='p', fov=None, **params):
        self.checkExists ()
        from mirexec import TaskImFit, TaskCgDisp
        
        resid = self.makeVariant ('fitresid', ImData)
        if resid.exists:
            raise Exception ('Resid file %s already exists?' % resid)
        
        imf = TaskImFit (in_=self, out=resid, residual=True, **params)
        if kind == 'p':
            imf.object = 'point'
        elif kind == 'g':
            imf.object = 'gaussian'
        elif kind == 'b':
            imf.object = 'beam'
        else:
            raise Exception ('Unknown fit kind ' + kind)

        imf.run ()
        resid.xShow (**params).run ()
        resid.delete ()

__all__ += ['ImData']
