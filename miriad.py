import sys, os
from os.path import join
from stat import ST_MTIME


# Tracing of MIRIAD operations. Almost always used for mirexec
# functions, but we also record delete/copy/rename in Data.

launchTrace = None

def basicTrace ():
    """Set the tracing function :data:`launchTrace` to a basic default.

:returns: :const:`None`

Sets the tracing function :data:`launchTrace` to a function that
prints out every command invoked, prefixed by "MIRIAD: ". Command
parameters are surrounded by single quotes to facilitate copying and
pasting into a shell.

The tracing function is stored in the variable :data:`launchTrace`. An
action can be traced by calling :func:`trace`.
"""

    global launchTrace

    def t (cmd):
        print "MIRIAD: '" + "' '".join (cmd) + "'"
        sys.stdout.flush ()
    
    launchTrace = t

def trace (cmd):
    """Trace the execution of *cmd*.

:arg cmd: a command and arguments
:type cmd: list of string
:returns: :const:`None`

Invokes the callable :data:`launchTrace` with *cmd* as the argument,
unless :data:`launchTrace` is :const:`None`, in which case this
function is a noop.

The function :func:`basicTrace` sets :data:`launchTrace` to a simple
default.
"""

    if launchTrace is not None:
        launchTrace (cmd)

__all__ = ['basicTrace', 'trace']


# Fundamental MIRIAD data set object.

class Data (object):
    """:synopsis: Generic reference to a MIRIAD dataset.
:arg basedata: The filename of the underyling dataset.
:type basedata: anything upon which str() can be called

The constructor returns a new instance that references a dataset with
the filename ``str(basedata)``. However, you should create
:class:`VisData` and :class:`ImData` instances rather than generic
:class:`Data` instances whenever possible, to take advantage of the
more-specialized functionality they offer.

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
       dest.delete ()
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
:returns: The real path (as defined by :func:`os.path.realpath`)
  to this dataset.
"""
        return os.path.realpath (self.base)
    
    # Low-level operations
    
    def moveTo (self, dest):
        """Move the dataset to a new location.

:arg dest: the new filename for the dataset 
:type dest: :class:`str`, or anything upon which :func:`str` can be called.
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

:arg dest: the filename of the copy of the dataset
:type dest: :class:`str`, or anything upon which :func:`str` can be called.
:rtype: :class:`~Data`
:returns: :const:`self`

Copies this dataset to a new location on disk. The dataset must
exist. Approximately equivalent to the shell command :command:`cp -r
{self} {dest}`. :func:`trace` is called with a "[copy]" operation.

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
:returns: :const:`self`

Deletes the dataset from disk. If the dataset doesn't exist,
silently does nothing. Approximately equivalent to the shell command
:command:`rm -r {self}`. If deletion occurs, :func:`trace` is called
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

:arg task: the task to set up
:type task: :class:`~mirexec.TaskBase`
:arg params: extra task parameters
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

:arg task: the task to set up
:type task: :class:`~mirexec.TaskBase`
:arg params: extra task parameters
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
        """Create another :class:`Data` instance with a similar name.

:arg name: the extension to to append to the original dataset's name
:type name: :class:`str`
:arg kind: the factory method to create the new dataset
:type kind: callable, returning :class:`Data`; if :const:`None`, use :class:`Data`
:rtype: :class:`Data`
:returns: a new dataset.

Creates a new dataset with an underlying filename of
:file:`{self}.{name}`. For example::

  v = VisData ('orig')
  d = v.makeVariant ('avg')
  v.averTo (d, 10)
  # Executes: uvaver vis=orig out=orig.avg interval=10

The argument *kind* specifies the factory function used to create
the instance. A class name or a custom function taking one string
argument are appropriate.

For the common case, the more tersely-named functions :meth:`vvis` and
:meth:`vim` will create new :class:`VisData` and :class:`ImData`
variants, respectively.
"""

        if kind is None: kind = Data # for some reason kind=Data barfs.

        inst = kind (self.base + '.' + name)
        assert isinstance (inst, Data)
        return inst

    _defVisClass = None
    _defImClass = None

    @classmethod
    def defaultVisClass (klass, vclass):
        """Set the class used by :meth:`vvis`.

:arg vclass: the class to be used by :func:`vvis`
:type vclass: any subclass of :class:`VisData`
:raises ValueError: if *vclass* is not a subclass 
  of :class:`VisData`

Sets the class instantiated by *all* calls to :meth:`vvis`. This
method is a class method, and so sets the value used by all
instances of :class:`Data`. This can be useful if you have a
customized subclass of :class:`VisData` that you want to use
throughout a program::

  class MyVis (VisData):
    def myfunc (self):
      # Perform some useful function ...

  Data.defaultVisClass (MyVis)

  v = MyVis ('foo')
  v2 = v.vvis ('avg')
  # v2 is an instance of MyVis, too

*vclass* must be a subclass of :class:`VisData`.
"""

        if not issubclass (vclass, VisData):
            raise ValueError ('vclass')

        klass._defVisClass = vclass

    @classmethod
    def defaultImClass (klass, iclass):
        """Set the class used by :meth:`vim`.

:arg: iclass: the class to be used by :func:`vim`
:type iclass: any subclass of :class:`ImData`
:raises ValueError: if *iclass* is not a subclass 
  of :class:`ImData`

Sets the class instantiated by *all* calls to :meth:`vim`. This
method is a class method, and so sets the value used by all
instances of :class:`Data`. This can be useful if you have a
customized subclass of :class:`ImData` that you want to use
throughout a program::

  class MyIm (ImData):
    def myfunc (self):
      # Perform some useful function ...

  Data.defaultImClass (MyIm)

  im = MyIm ('foo')
  im2 = im.vim ('avg')
  # im2 is an instance of MyIm, too

*iclass* must be a subclass of :class:`ImData`.
"""

        if not issubclass (iclass, ImData):
            raise ValueError ('iclass')

        klass._defImClass = iclass

    def vvis (self, name):
        """Create a :class:`VisData` variant of this dataset.

:arg name: the extension to append to the dataset's name
:type name: :class:`str`
:rtype: :class:`VisData`
:returns: a new dataset object

Returns ``self.makeVariant (name, klass)`` where *klass* is, by
default, :class:`VisData`. The value of *klass* can be overridden by
calling :meth:`defaultVisClass`.
"""

        return self.makeVariant (name, self._defVisClass)
    
    def vim (self, name):
        """Create an :class:`ImData` variant of this dataset.

:arg name: the extension to append to the dataset's name
:type name: :class:`str`
:rtype: :class:`ImData`
:returns: a new dataset object

Returns ``self.makeVariant (name, klass)`` where *klass* is, by
default, :class:`ImData`. The value of *klass* can be overridden by
calling :meth:`defaultImClass`.
"""

        return self.makeVariant (name, self._defImClass)

    # Detailed access to dataset.

    def _openImpl (self, mode):
        from mirtask import UserDataSet

        if mode == 'rw':
            create = False
        elif mode == 'c':
            create = True
        else:
            raise Exception ('Unsupported mode "%s"; "rw" and "c" are allowed' % mode)

        return UserDataSet (self, create)
    
    def open (self, mode):
        """Opens the dataset for access.

:arg mode: The mode to open the dataset in. Use 'rw' to open the
  dataset in read-write mode, 'c' to create the dataset, and 'a' to
  append to an existing dataset.  Generic :class:`Data` instances
  support 'rw' and 'c'. Instances of :class:`VisData` support 'rw',
  'c', and 'a'.
:type mode: :class:`str`
:rtype: :class:`mirtask.UserDataSet`
:returns: An opened dataset

This implementation opens the dataset in a generic way. To be able to
access visibility or image data through the usual functions, make sure
to call this function on an instance of the :class:`VisData` or
:class:`ImData` classes, which override the  implementation to open
the dataset in the correct manner for their corresponding data types.
"""

        return self._openImpl (mode)

__all__ += ['Data']


# Visibility data

class VisData (Data):
    """:synopsis: Reference to a MIRIAD visibility dataset.

This subclass of :class:`Data` is for referring to visibility
datasets. It has special functions handy for use with visibility data
and inherits many generic features from the :class:`Data` class.
"""

    def _openImpl (self, mode):
        from mirtask import UVDataSet
        return UVDataSet (self, mode)

    def readLowlevel (self, saveFlags, **kwargs):
        """Directly access the visibility data.

:arg saveFlags: whether to save modified UV flags to the dataset
  as it is read
:type saveFlags: :class:`bool`
:arg kwargs: extra arguments to
  :func:`mirtask.uvdat.readFileLowlevel`.
:rtype: generator
:returns: generates a sequence of UV information tuples. See the
  documentation of :func:`mirtask.uvdat.readFileLowlevel` for more
  information.

Calls :func:`mirtask.uvdat.readFileLowlevel` on this dataset with the
specified arguments.
"""

        from mirtask import uvdat
        return uvdat.readFileLowlevel (self.base, saveFlags, **kwargs)
    
    # Not-necessarily-interactive operations

    def apply (self, task, **params):
        task.vis = self
        task.setArgs (**params)
        return task

    def catTo (self, dest, **params):
        """:command:`uvcat` this dataset to *dest*.

:arg dest: the destination dataset
:type dest: :class:`Data`, str, or any other stringable
:arg params: extra parameters to pass to the
  :command:`uvcat` command
:rtype: :const:`None`

Invokes the task :command:`uvcat` via
:class:`mirexec.TaskUVCat`. Checks if the source dataset exists
but does no checking on the destination dataset. Approximately
equivalent to the shell command :command:`uvcat vis={self} out={dest}
{params...}`.
"""

        self.checkExists ()

        from mirexec import TaskUVCat
        self.apply (TaskUVCat (), out=dest, **params).run ()

    def averTo (self, dest, interval, **params):
        """:command:`uvaver` this dataset to *dest*.

:arg dest: the destination dataset
:type dest: :class:`Data`, str, or any other stringable
:arg interval: the averaging interval, in minutes
:type interval: numeric
:arg params: extra parameters to pass to the
  :command:`uvaver` command
:rtype: :const:`None`

Invokes the task :command:`uvaver` via
:class:`mirexec.TaskUVAver`. Checks if the source dataset exists
but does no checking on the destination dataset. Approximately
equivalent to the shell command :command:`uvaver vis={self} out={dest}
interval={interval} {params...}`.
"""
        self.checkExists ()

        from mirexec import TaskUVAver
        self.apply (TaskUVAver (), out=dest, interval=interval,
                    **params).run ()

    def lwcpTo (self, dest):
        """Make a lightweight copy of this dataset in *dest*.

:arg dest: the destination dataset
:type dest: :class:`Data`, str, or any other stringable
:rtype: :const:`None`

Creates a "lightweight" copy of the source dataset. This
is a clone of the original dataset in which all of the header items
are copied except for the "visdata" item, which is instead
symbolically linked back to the original dataset. This item is
usually by far the largest component of a UV dataset and is also
not modified during most analysis operations. Checks if the source
dataset exists and deletes the destination if it already exists.
If the copy succeeds, :func:`trace` is called with a "[lwcp]"
operation.

The implementation of the copy is simple: every regular file in
the source dataset is copied to the destination directory, except
for 'visdata' which is handled as described above. Other items
are ignored. If any errors occur, the function attempts to delete
the destination dataset.
"""
        import shutil
        self.checkExists ()

        if not isinstance (dest, Data):
            dest = VisData (str (dest))

        dest.delete ()

        try:
            success = False
            os.mkdir (dest.base)

            for fn in os.listdir (self.base):
                # We use realPath to prevent confusion
                # arising from relative symlinks.
                sfn = join (self.realPath (), fn)
                dfn = join (dest.base, fn)

                if fn == 'visdata':
                    os.symlink (sfn, dfn)
                elif os.path.isfile (sfn):
                    shutil.copy (sfn, dfn)

            trace (['[lwcp]', 'vis=%s' % self, 'out=%s' % dest])
            success = True
        finally:
            if not success:
                dest.delete ()


__all__ += ['VisData']


# Image data

class ImData (Data):
    """:synopsis: Reference to a MIRIAD image dataset.

This subclass of :class:`Data` is for referring to image datasets. It
inherits many generic features from the :class:`Data` class.
"""

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
