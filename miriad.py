import sys, os
from os.path import join
from stat import ST_MTIME

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

class Data (object):
    def __init__ (self, basedata):
        self.base = basedata

    def __str__ (self):
        return self.base

    def __repr__ (self):
        return '<MIRIAD data, base "%s">' % self.base

    def __eq__ (self, other):
        # We could see if other was an instance of self.__class__, but
        # two different subclasses of data that are pointing to the same
        # path really are referring to the same object, so I think it's
        # more correct to just verify that other is an instance of Data.
        return isinstance (other, Data) and self.realPath () == other.realPath ()

    def __hash__ (self):
        return hash (self.realPath ())
    
    # Low-level attributes
    
    @property
    def exists (self):
        """True if the data specified by this class actually exists.
        (If False, the data corresponding to this object will probably
        be created by the execution of a command.)"""
        return os.path.exists (self.base)

    @property
    def mtime (self):
        """The modification time of this dataset."""
        # Once the set is created, it can be modified without updating
        # the mtime of the directory. But, assuming normal Miriad operating
        # conditions, the history file should always be modified when the
        # dataset is modified, and the history file should always be there.
        return os.stat (join (self.base, 'history'))[ST_MTIME]
    
    @property
    def umtime (self):
        """The "unconditional" modification time of this dataset --
zero is returned if the dataset does not exist."""
        try:
            return os.stat (join (self.base, 'history'))[ST_MTIME]
        except OSError, e:
            if e.errno == 2: return 0
            raise e
    
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

        inst = kind (self.base + '.' + name)
        assert isinstance (inst, Data)
        return inst

    _defVisClass = None
    _defImClass = None

    @classmethod
    def defaultVisClass (klass, vclass):
        if not issubclass (vclass, VisData):
            raise ValueError ('vclass')

        klass._defVisClass = vclass

    @classmethod
    def defaultImClass (klass, iclass):
        if not issubclass (iclass, ImData):
            raise ValueError ('iclass')

        klass._defImClass = iclass

    def vvis (self, name):
        return self.makeVariant (name, self._defVisClass)
    
    def vim (self, name):
        return self.makeVariant (name, self._defImClass)

    # Detailed access to dataset.

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
        return self._openImpl (mode)

__all__ += ['Data']


# Visibility data

class VisData (Data):
    def _openImpl (self, mode):
        from mirtask import UVDataSet
        return UVDataSet (self, mode)

    def readLowlevel (self, saveFlags, **kwargs):
        from mirtask import uvdat
        return uvdat.readFileLowlevel (self.base, saveFlags, **kwargs)
    
    # Not-necessarily-interactive operations

    def apply (self, task, **params):
        task.vis = self
        task.setArgs (**params)
        return task

    def xapply (self, task, **params):
        task.vis = self
        task.xint = True
        task.setArgs (**params)
        return task

    def catTo (self, dest, **params):
        self.checkExists ()

        from mirexec import TaskUVCat
        self.apply (TaskUVCat, out=dest, **params).run ()

    def averTo (self, dest, interval, **params):
        self.checkExists ()

        from mirexec import TaskUVAver
        self.apply (TaskUVAver, out=dest, interval=interval,
                    **params).run ()


__all__ += ['VisData']


# Image data

class ImData (Data):
    # FIXME: haven't yet wrapped XYIO routines to
    # make it possible to open and read images.

    def apply (self, task, **params):
        task.in_ = self
        task.setArgs (**params)
        return task

    def xapply (self, task, **params):
        task.in_ = self
        task.xint = True
        task.setArgs (**params)
        return task

__all__ += ['ImData']


# Initialize default variant classes

Data.defaultVisClass (VisData)
Data.defaultImClass (ImData)
