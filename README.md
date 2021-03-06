miriad-python 1.2.4
===================

miriad-python is a bridge between the MIRIAD radio analysis package and
the Python programming language. It allows you to:

* read and write MIRIAD datasets in Python,
* execute MIRIAD tasks from Python, and
* write MIRIAD tasks in Python.

This file contains detailed installation instructions. For all other
matters, the best resource is the miriad-python website:

  https://www.cfa.harvard.edu/~pwilliam/miriad-python/

The website includes up-to-date contact information for the
developers, who will be happy to assist you if you have trouble
installing or using miriad-python.

If you use miriad-python in academic research, please cite Williams
et al., 2012 PASP 124 624 (doi:10.1086/666604) in any resulting
publications.


Installation Instructions
=========================

The basic installation recipe is the standard Linux one:

    ./configure --prefix=PREFIX --with-miriad=MIRIAD_LOCATION
    make && make install

where `PREFIX` and `MIRIAD_LOCATION` are replaced with appropriate
values. Many more details are below.

Requirements
------------

The following packages are required to install miriad-python:

 * Python version 2.5 or greater
 * NumPy version 1.2 or greater
 * Matching C and Fortran-77 compilers (we use gcc and gfortran 4.8)
 * A recent working installation of CARMA MIRIAD. More on this below.

If you're using a Mac, the best way to get an installation of Python with
Numpy is to install the latest version of the "Anaconda" Python distribution,
found here:

  http://www.continuum.io/downloads

If you install this Python distribution, make sure to start a new terminal
that picks up the custom Anaconda `python` program before proceeding. You
should also make sure to install miriad-python into the same location as
Anaconda so that it can find the miriad-python modules automatically.

There are multiple divergent MIRIAD codebases, and multiple ways to build
them. Miriad-python must be built against the CARMA version of MIRIAD. We
attempt to support a variety of installations, but the most reliable setup is
a recent installation based on the "new-style" autotools build system.

CARMA MIRIAD's homepage is

  http://carma.astro.umd.edu/wiki/index.php/Miriad

The binary packages distributed at that site are built with the "old style"
system. Miriad-python aims to be compatible with these packages, but there
are some issues with the way that they're built that can prevent things
from working.

If you use a Mac and the CARMA binary packages don't work for you, we
suggest the MIRIAD MacPort:

  https://www.cfa.harvard.edu/~pwilliam/miriad-macport/

If you don't use a Mac, it's not too hard to build CARMA MIRIAD with
the "new-style" (autotools) build system yourself. It is easiest to
start with the most recent source code package used by the MacPort:

  https://www.cfa.harvard.edu/~pwilliam/miriad-macport/miriad-latest.tar.gz

For the very latest MIRIAD source code, you may find it useful to
access Peter Williams' GitHub mirror of the CARMA MIRIAD source
tree.

  https://github.com/pkgw/carma-miriad

This option presents the same autotools-related challenges as those
relating to Git checkouts of this package -- see the following
section.

The miriad-python build configuration step should give you an error if
it encounters an install of MIRIAD that it can’t handle.

Pre-Configuration
-----------------

If the file `configure` exists in the same directory as this file, you
may skip this section. And you want to skip this section if you
possibly can.

If you're still here, you've probably downloaded miriad-python from
the Git repository, and the GNU "autotools" build system needs to be
set up. Sometimes the setup process works like a charm; other times
things go down in flames and no one except a deep autotools expert can
figure out how to fix things.

So:

  * If the `configure` script exists and you're not *very comfortable*
    with what you're doing, skip this step!

  * If the following pre-configuration steps give you any problems,
    go to the website and download an official release archive, for
    which this step is not necessary. If the official releases are
    too old for your purposes, ask for a new one to be made.

  * The autotools have one advantage in that they're widely used.
    If you absolutely must fight through them, contact your local
    system administrator or Linux expert. He or she can probably
    help without needing to know any specifics about miriad-python.

If you're still still here, the setup process is simple in
theory. In this directory, run:

    ACLOCAL="aclocal -I build-aux" autoreconf -fi

(This assumes you use a Bourne shell. If you don't know what that is
or if you are, you should probably stick with official release
archives.)

If these steps succeed, that's good. But these steps may succeed and
still lead to bizarre failures farther downstream in the build
process. If anything happens that you can't figure out, it is *highly
recommended* that you try out an official release to see if that
sidesteps the problem.

Configuration
-------------

The first real step to installation is to configure the build. The
`configure` program will check for a variety of features of your
computer and report and error if anything is amiss. You must give
`configure` two pieces of information:

  * The "prefix" where miriad-python files will be installed.  The
    default is `/usr/local`. The main miriad-python modules will land
    in a directory named something like
    `PREFIX/lib/python2.6/site-modules/`

  * The location where your MIRIAD installation is found. There is
    no default.

This is all accomplished by running the `configure` script like so:

    ./configure --prefix=PREFIX --with-miriad=MIRPATH

Here, MIRPATH is where MIRIAD has been installed. If you use a "new-style"
installation, the following files should exist:
`MIRPATH/include/miriad-c/miriad.h` and `MIRPATH/lib/libmir.EXT`, where `EXT`
is `so` on Linux machines and `dylib` on Macs. If you're using a CARMA
precompiled distribution, the file `MIRPATH/src/inc/maxdim.h` should exist.

If you believe that you're specifying the correct --with-miriad
argument and the `configure` checks are still failing, you can peruse
the file `config.log`, created by `configure`, for the particular
error that led the tool to fail. Sometimes unrelated problems can show
up in this phase of the configuration process. If you still have
trouble, consult your local system administrator (with complete
contextual information) or the miriad-python developers.

For thorough but generic instructions on running the `configure`
program, see

  http://git.savannah.gnu.org/cgit/automake.git/tree/INSTALL

Compilation
-----------

Just run `make`. If the configuration step completes successfully,
compilation should always succeed. If it doesn't, these generic
instructions are unable to help you.

Installation
------------

If the compilation step succeeds, you can install. Run `make install`
or `sudo make install` or `su -c 'make install'` as appropriate.

Verification
------------

In order to use miriad-python in your programs, your Python
interpreter must be able to find the miriad-python modules. If you
configure miriad-python with a prefix matching that of your Python
interpreter, this should happen automatically. Otherwise, you may need
to use the `$PYTHONPATH` environment variable. The directory that must
be searched is

    PREFIX/lib/python2.6/site-packages

with two important caveats: firstly, replace the `2.6` with the
appropriate version of your Python interpreter; secondly, if the
directory

    PREFIX/lib64/python2.6/site-packages

exists, it must be added to the Python search path as well.

To superficially check that everything is accessible to the Python
interpreter, you can run

    python -c "import mirtask, mirexec, miriad"

If no errors are reported, things are working.

Some example programs are included in the examples/ directory. They
require real input datasets to operate, but if you have some data
on-hand you can try them out. Each program is contains extensive
internal documentation. See also examples/README.


Bug Reports
===========

We use the GitHub issue tracker for handling bug reports. See

  https://github.com/pkgw/miriad-python/issues


wcslib headers
==============

(This section documents an error that may be reported by the `configure`
script in certain conditions.)

First of all, sorry for the terse error message produced by the
`configure` program -- the tools we use make it really hard to produce
helpful, descriptive output at that point.

If you encounter this error, your installation of Miriad is not recent
enough to contain certain files needed to compile miriad-python
successfully. Installations of Miriad with source code more recent
than January 3, 2012 should work. (Version numbers aren't very helpful
in this case because Miriad releases are very infrequent.) The
particular error is a lack of private wcslib headers. Consult your
local Miriad-installation guru for more help if you're not sure how to
react to this situation.


bughandler_c
============

(This section documents an error that may be reported by the `configure`
script in certain conditions.)

First of all, sorry for the terse error message produced by the
`configure` program -- the tools we use make it really hard to produce
helpful, descriptive output at that point.

The source of this error is that your installation of Miriad is not
recent enough to contain certain hooks that are necessary for reliable
operation of miriad-python. Installations of Miriad with source code
more recent than February 13, 2009 should work. (Version numbers
aren't very helpful in this case because Miriad releases are very
infrequent.) The particular error is a lack of the bughandler_c
function, which should be found in the libmir library. Consult your
local Miriad-installation guru for more help if you're not sure how to
react to this situation.


f2py
====

(This section documents an error that may be reported by the `configure`
script in certain conditions.)

First of all, sorry for the terse error message produced by the
`configure` program -- the tools we use make it really hard to produce
helpful, descriptive output at that point.

The source of this error is that your system does not have the `f2py`
program available. This program is usually distributed with the Numpy
package for numerical work in Python. If Numpy isn't available at all,
you need to install it. You may also need to install additional packages
to get the f2py program in particular. On most OSes, both pieces are
available as a prebuilt binary package that should be easy to install.
Here are the package names for some common Linux distributions:

      Fedora: numpy, numpy-f2py
      Ubuntu: python-numpy
    OpenSuSE: python-numpy

If Numpy isn't available as a prebuilt binary package, you'll need to install
it manually, instructions for which are beyond the scope of this document. See
http://numpy.scipy.org or http://www.continuum.io/downloads.


Contact Information
===================

Check the miriad-python website for up-to-date information. At the
time of release, the best contact person is Peter Williams,
pwilliams@cfa.harvard.edu . For bug reports, use the issue
tracker on the miriad-python GitHub page:

  https://github.com/pkgw/miriad-python/issues


Copyright Notice
================

Copyright 2009-2013 Peter Williams

This file is free documentation; the copyright holder gives unlimited
permission to copy, distribute, and modify it.
