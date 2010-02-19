dnl Copyright 2009, 2010 Peter Williams
dnl
dnl This file is part of miriad-python.
dnl
dnl Miriad-python is free software: you can redistribute it and/or
dnl modify it under the terms of the GNU General Public License as
dnl published by the Free Software Foundation, either version 3 of the
dnl License, or (at your option) any later version.
dnl
dnl Miriad-python is distributed in the hope that it will be useful, but
dnl WITHOUT ANY WARRANTY; without even the implied warranty of
dnl MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
dnl General Public License for more details.
dnl
dnl You should have received a copy of the GNU General Public License
dnl along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.

AC_INIT([miriad-python], [0.5.0])
AC_CONFIG_SRCDIR([mirtask/_uviomodule.c])
AC_CONFIG_MACRO_DIR(.)
AM_INIT_AUTOMAKE([foreign -Wall])
AM_MAINTAINER_MODE

AC_SUBST(ACLOCAL_AMFLAGS, ["-I ."])

dnl Used in doc/conf.py.in
AC_SUBST([MIRPY_SHORTVERSION],[0.1])
AC_SUBST([MIRPY_COPYRIGHT],["2009, Peter Williams"])

dnl Miriad.

AC_ARG_WITH([miriad],
AS_HELP_STRING([--with-miriad=PREFIX], 
[Miriad libraries and headers have been installed in prefix PREFIX]),
[],with_miriad=noextra)

orig_LIBS="$LIBS"
orig_CFLAGS="$CFLAGS"

if test x"$with_miriad" = xnoextra ; then
  MIR_LIBS="-lmir -lmir_uvio -lmir_linpack -lpgplot"
  MIR_CFLAGS=""
  MIR_DISTCHECK_CONFARG=""
  miriad_loc="system search path"
else
  MIR_LIBS="-L${with_miriad}/lib -lmir -lmir_uvio -lmir_linpack -lpgplot"
  MIR_CFLAGS="-I${with_miriad}/include/miriad-c"
  MIR_DISTCHECK_CONFARG="--with-miriad=${with_miriad}"
  LIBS="-L${with_miriad}/lib $LIBS"
  CFLAGS="$MIR_CFLAGS $CFLAGS"
  miriad_loc="$with_miriad"
fi

AC_CHECK_HEADER([miriad.h], failed=false, failed=true,
[#include "hio.h"])

if $failed ; then
  AC_MSG_ERROR([Couldn't find Miriad headers. Try the --with-miriad argument.])
fi

AC_CHECK_LIB([mir], [wrhda_], failed=false, failed=true, [-lmir_uvio -lmir_linpack -lpgplot])
AC_CHECK_LIB([mir], [bugrecover_c], nobrc=false, nobrc=true, [-lmir_uvio -lmir_linpack -lpgplot])

LIBS="$orig_LIBS"
CFLAGS="$orig_CFLAGS"

if $failed ; then
  AC_MSG_ERROR([Couldn't find Miriad libraries. Try the --with-miriad argument.])
elif $nobrc ; then
  AC_MSG_ERROR([Miriad libraries too old; see README on bugrecover_c])
fi

AC_SUBST(MIR_LIBS)
AC_SUBST(MIR_CFLAGS)
AC_SUBST(MIR_DISTCHECK_CONFARG)

dnl Checks

dnl We use this in the doc/ install rule. On my Fedora 10 computers this
dnl subst wasn't needed but on a SuSE 10.2 it was -- I think that older
dnl (<=1.9) automakes don't define this automatically whereas newer ones
dnl do.
AC_PROG_MKDIR_P
AC_SUBST([MKDIR_P])

AC_PROG_F77
AM_PROG_LIBTOOL
AM_PATH_PYTHON(2.3.5)
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_ERROR(could not find Python headers)])

AC_PATH_PROG(F2PY, f2py, false)
if test x"$F2PY" = xfalse ; then
   AC_MSG_ERROR([F2PY not found])
fi
AC_SUBST(F2PY)

if test x"$GCC" = xyes ; then
   CFLAGS="$CFLAGS -Wall -Wstrict-prototypes"
fi

dnl MIRIAD is built with large file support, so we need to have it
dnl too otherwise we'll disagree about the size of off_t

AC_SYS_LARGEFILE
AC_FUNC_FSEEKO

dnl Here we have to work around the fact that __file__ is replaced by
dnl M4. D'oh!

AM_CHECK_PYMOD(numpy,ndarray,,AC_MSG_ERROR([could not find Numpy module]))
NUMPY_INCLUDEDIR=`python -c 'import numpy, os.path as p ; f = getattr (numpy, "__" + "file__") ; print p.join (p.dirname (f), "core", "include")'`
AC_SUBST(NUMPY_INCLUDEDIR)

dnl Check for Sphinx, used to create docs

AC_PATH_PROG(SPHINXBUILD, sphinx-build, notfound)
if test x"$SPHINXBUILD" = xnotfound ; then
   AC_MSG_WARN([The program 'sphinx-build' wasn't found on your system! Documentation will not be built.])
   BUILD_DOCS=false
   DOCS_DESC="no; no 'sphinx-build' found"
else
   BUILD_DOCS=true
   DOCS_DESC="yes"
fi

AM_CONDITIONAL([BUILD_DOCS], $BUILD_DOCS)

if $BUILD_DOCS ; then
   AC_CONFIG_FILES([doc/conf.py doc/Makefile])
fi

dnl Output

AC_CONFIG_FILES([
  Makefile
  miriad-python.pc
  mirtask/Makefile
])
AC_OUTPUT

dnl Summarize important configuration options

echo "Configuration summary:"
echo "   Install prefix:  " $prefix
echo "   MIRIAD found in: " $miriad_loc
echo "   Building docs?   " $DOCS_DESC
