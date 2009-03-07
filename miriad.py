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
    """:synopsis: Generic reference to MIRIAD datasets.
:arg: basedata
:type: anything upon which :func:`str` can be called

The constructor returns a new instance that references a dataset with
the filename *basedata*.

The stringification of a :class:`Data` instance returns the filename
of the underlying dataset.

:class:`Data` implements equality testing and hashing. One dataset is
equal to another if and only if both are instances of :class:`Data`
*or any of its subclasses* and the :func:`os.path.realpath` of the
filenames underlying both datasets are equal.
"""

    def __init__ (self, basedata):
        self.base = str (basedata)

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
        "Test documentation."""
        return hash (self.realPath ())
    
    # Low-level attributes
    
    @property
    def exists (self):
        """Read-only :class:`bool`. :const:`True` if the dataset specified
        by this class actually exists. (If :const:`False`, the dataset
        corresponding to this object can be created by the execution
        of a command.)"""
        return os.path.exists (self.base)

    @property
    def mtime (self):
        """Read-only :class:`int`. The modification time of the
history item of this dataset. Raises :class:`OSError` if the
dataset does not exist. Useful for checking whether a dataset
needs to be regenerated, in conjunction with the :attr:`umtime`
attribute::

  def maybeCat (src, dest, **params):
    # If dest doesn't exist or src has been modified more
    # recently than src, perform a uvcat.
    if dest.umtime < src.mtime:
       src.catTo (dest, **params)
"""
        # Once the set is created, it can be modified without updating
        # the mtime of the directory. But, assuming normal Miriad operating
        # conditions, the history file should always be modified when the
        # dataset is modified, and the history file should always be there.
        return os.stat (join (self.base, 'history'))[ST_MTIME]
    
    @property
    def umtime (self):
        """Read-only :class:`int`. The "unconditional" modification
time of this dataset -- equivalent to :attr:`mtime`, but zero is
returned if the dataset does not exist. See the example in
:attr:`mtime` for potential uses."""
        try:
            return os.stat (join (self.base, 'history'))[ST_MTIME]
        except OSError, e:
            if e.errno == 2: return 0
            raise e
    
    def checkExists (self):
        """:rtype: :const:`None`

Check if the :class:`~Data` exists on disk. If so, do nothing
and return. If not, raise an :class:`Exception`."""
        if self.exists: return

        raise Exception ('Data set %s does not exist' % self.base)

    def realPath (self):
        """:rtype: :class:`str`
:returns: The real path (as defined by :func:`os.path.realpath`
          to this dataset.
"""
        return os.path.realpath (self.base)
    
    # Low-level operations
    
    def moveTo (self, dest):
        """Move the dataset to a new location.

:arg: dest
:type: :class:`str`, or anything upon which :func:`str` can be called.
:rtype: :class:`~Data`
:returns: :const:`self`

Renames this dataset to a new location on disk. The dataset
must exist. Uses :func:`os.rename`, so renaming a dataset across
devices will not work, but the rename is atomic. :func:`trace` is
called with a "[rename]" operation.
"""

        self.checkExists ()
        dest = str (dest)
        
        trace (['[rename]', 'from=%s' % self, 'to=%s' % dest])
        
        os.rename (self.base, dest)
        self.base = dest

        return self


    def copyTo (self, dest):
        """Copy the dataset to a new location.

:arg: dest
:type: :class:`str`, or anything upon which :func:`str` can be called.
:rtype: :class:`~Data`
:returns: :const:`self`

Copies this dataset to a new location on disk. The dataset must
exist. Approximately equivalent to :command:`cp -r $self
$dest`. :func:`trace` is called with a "[copy]" operation.

FIXME: Doesn't clean up correctly if an error occurs midway
through the copy.
"""
        self.checkExists ()
        dest = str (dest)

        trace (['[copy]', 'from=%s' % self, 'to=%s' % dest])

        from shutil import copy

        os.mkdir (dest)

        for f in os.listdir (self.base):
            copy (join (self.base, f), join (dest, f))

        return self

    
    def delete (self):
        """Delete the dataset.

:rtype: :class:`~Data`
:returns: :const:self

Deletes the dataset from disk. If the dataset doesn't exist,
silently does nothing. Approximately equivalent to
:command:`rm -r $self`. If deletion occurs, :func:`trace` is called
with a "[delete]" operation.
"""
        if not self.exists: return

        trace (['[delete]', 'in=%s' % self])
        
        for e in os.listdir (self.base):
            os.remove (join (self.base, e))
        os.rmdir (self.base)

        return self

    def apply (self, task, **params):
        """Configure a task to run on this dataset.

:arg: task
:type: :class:`~mirexec.TaskBase`
:arg: params
:type: Extra keyword parameters
:rtype: :class:`~mirexec.TaskBase`
:returns: *task*

Set the appropriate input option ('vis' or 'in') of the
:class:`mirexec.TaskBase` *task* to :const:`self`. Also apply any
keywords in *params* to *task* via
:meth:`mirexec.TaskBase.applyParams`. Returns *task* for easy
chaining::

  import miriad
  from mirtask import TaskUVFlag
  v = miriad.VisData ('dataset')
  v.apply (TaskUVFlag (), flagval='f', select='ant(1)').run ()

  # The above example could also be written:

  TaskUVFlag (vis=v, flagval='f', select='ant(1)').run ()

This function isn't implemented in the generic :class:`Data`
class. The subclasses :class:`VisData` and :class:`ImData` override it
to set the appropriate task input keyword.
"""
        raise NotImplementedError ()

    def xapply (self, task, **params):
        """Configure a task to run verbosely on this dataset.

:arg: task
:type: :class:`~mirexec.TaskBase`
:arg: params
:type: Extra keyword parameters
:rtype: :class:`~mirexec.TaskBase`
:returns: *task*

Identical to :meth:`apply`, but also sets the
:attr:`~mirexec.TaskBase.xint` attribute of the *task* to
:const:`True`, causing the task to run verbosely.
"""
        self.apply (task, **params)
        task.xint = True
        return task

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

__all__ += ['ImData']


# Initialize default variant classes

Data.defaultVisClass (VisData)
Data.defaultImClass (ImData)
