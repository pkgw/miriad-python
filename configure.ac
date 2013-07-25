dnl Copyright 2009-2013 Peter Williams
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

AC_INIT([miriad-python], [1.2.3])
AC_CONFIG_SRCDIR([mirtask/_miriad_cmodule.c])
AC_CONFIG_AUX_DIR([build-aux])
AC_CONFIG_MACRO_DIR([build-aux])
AM_INIT_AUTOMAKE([foreign -Wall])
AM_MAINTAINER_MODE

AM_PROG_AR dnl needed to make libtool happy
LT_INIT

dnl Used in doc/conf.py.in
AC_SUBST([MIRPY_SHORTVERSION],[1.2])
AC_SUBST([MIRPY_COPYRIGHT],["2009-2012 Peter Williams"])


dnl Compiler flags. Python 2.x code needs -fno-strict-aliasing if
dnl available.

AC_LANG([C])

AX_CHECK_COMPILE_FLAG([-fno-strict-aliasing],[
  AM_CFLAGS="$AM_CFLAGS -fno-strict-aliasing"
])

AX_CHECK_COMPILE_FLAG([-Wall],[
  AM_CFLAGS="$AM_CFLAGS -Wall"
])

AX_CHECK_COMPILE_FLAG([-Wstrict-prototypes],[
  AM_CFLAGS="$AM_CFLAGS -Wstrict-prototypes"
])

AC_SUBST([AM_CFLAGS])

dnl ============================================================
dnl Checking for MIRIAD. We try to support both old-style binary
dnl packages and autoconf installs.

dnl MIRIAD: prerequsities

AC_PROG_MKDIR_P
AC_SUBST([MKDIR_P]) dnl might only be needed for very old autoconf
AC_PROG_LN_S

dnl MIRIAD: --with-miriad handling
dnl We need two versions of search paths: one for makefiles, one for
dnl config checks.

AC_ARG_WITH([miriad],
AS_HELP_STRING([--with-miriad=PREFIX],
[Miriad libraries and headers have been installed in prefix PREFIX]),
[],with_miriad=noextra)

AC_SUBST(MIR_DISTCHECK_CONFARG)
AC_MSG_CHECKING([type of MIRIAD installation])

if test x"$with_miriad" = xnoextra ; then
  AC_MSG_RESULT([system package (use --with-miriad=... if this fails)])
  miriad_loc="system search path"
elif test -f "${with_miriad}/src/inc/maxdim.h" ; then
  AC_MSG_RESULT([old-style binary package])
  miriad_loc="$with_miriad (old-style binary package)"
  MIR_DISTCHECK_CONFARG="--with-miriad=${with_miriad}"

  AC_MSG_CHECKING([for host type of old-style MIRIAD build])
  mirhosttype=`uname -s |tr A-Z a-z`
  AC_MSG_RESULT([$mirhosttype])

  dnl Symlinking like this makes it so we don't have to worry about
  dnl whether $with_miriad is absolute/relative, etc.
  rm -rf mirinc mirpkg
  $LN_S "${with_miriad}" mirpkg
  $MKDIR_P mirinc/wcslib
  (cd mirinc
   $LN_S ../mirpkg/src/inc/maxdim.h .
   for h in miriad.h sysdep.h ; do
     $LN_S ../mirpkg/src/subs/$h .
   done
  )
  (cd mirinc/wcslib
   $LN_S ../../mirpkg/borrow/wcslib/wcsconfig.h .
   for h in ../../mirpkg/borrow/wcslib/C/*.h ; do
     $LN_S $h .
   done
  )

  mir_output_libdir='-L${abs_top_builddir}/mirpkg/lib/'"$mirhosttype"
  mir_output_cppflags='-I${top_builddir}/mirinc'
  mir_cfg_libdir="-Lmirpkg/lib/$mirhosttype"
  mir_cfg_cppflags="-Imirinc"
else
  AC_MSG_RESULT([standard])
  miriad_loc="$with_miriad (standard installation)"
  MIR_DISTCHECK_CONFARG="--with-miriad=${with_miriad}"

  mir_output_libdir="-L${with_miriad}/lib"
  mir_output_cppflags="-I${with_miriad}/include/miriad-c"
  mir_cfg_libdir="$mir_output_libdir"
  mir_cfg_cppflags="$mir_output_cppflags"
fi

dnl MIRIAD: headers

orig_CPPFLAGS="$CPPFLAGS"
CPPFLAGS="$mir_cfg_cppflags $CPPFLAGS"

AC_CHECK_HEADER([miriad.h],[],[
  AC_MSG_ERROR([Couldn't find Miriad headers. See README on --with-miriad.])
])

AC_CHECK_HEADER([wcslib/wcs.h],[],[
  AC_MSG_ERROR([Couldn't find wcslib headers. See README on wcslib headers.])
])

CPPFLAGS="$orig_CPPFLAGS"
MIR_CPPFLAGS="$mir_output_cppflags"
AC_SUBST(MIR_CPPFLAGS)

dnl MIRIAD: libraries to link

mir_libs="-lm"

AC_CHECK_LIB([mir_wcs], [wcsini], [
  mir_libs="-lmir_wcs $mir_libs"
], [
  AC_CHECK_LIB([wcs], [wcsini],[
    mir_libs="-lwcs $mir_libs"
  ],[
    AC_MSG_ERROR([couldn't find a WCS library])
  ],[$mir_cfg_libdir $mir_libs])
],[$mir_cfg_libdir $mir_libs])

AC_CHECK_LIB([mir], [wrhda_],[
  mir_libs="-lmir $mir_libs"
],[
  AC_MSG_ERROR([Couldn't find Miriad libraries. See README on --with-miriad.])
],[$mir_cfg_libdir $mir_libs])

AC_CHECK_LIB([mir], [bughandler_c], [
  : dnl do nothing; if left empty, autoconf adds another -lmir
],[
  AC_MSG_ERROR([Miriad libraries too old; see README on bughandler_c])
], [$mir_cfg_libdir $mir_libs])

AC_CHECK_LIB([mir], [uvchkshadow_c], [
    chkshadow=1 chkshadowstr=yes
],[
    chkshadow=0 chkshadowstr=no
],[$mir_cfg_libdir $mir_libs])

AC_DEFINE_UNQUOTED([HAVE_UVCHKSHADOW], [$chkshadow],
  [Define if the MIRIAD library provides uvchkshadow_c().])

AC_CHECK_LIB([mir], [sdot_], [
  : dnl do nothing; if left empty, autoconf adds another -lmir
], [
  AC_CHECK_LIB([linpack], [sdot_],[
    mir_libs="$mir_libs -llinpack"
  ],[
    AC_MSG_ERROR([couldn't determine how to link in linpack routines])
  ],[$mir_cfg_libdir $mir_libs])
], [$mir_cfg_libdir $mir_libs])

MIR_LIBS="$mir_output_libdir $mir_libs"
AC_SUBST(MIR_LIBS)


dnl Checks for other dependencies

dnl AC_PROG_F77 doesn't raise an error if no compiler was found, and
dnl doesn't actually check whether the compiler works ...
AC_PROG_F77
test -z "$F77" && AC_MSG_FAILURE([no acceptable Fortran 77 compiler was found in \$PATH])
AC_LANG_PUSH([Fortran 77])
AC_MSG_CHECKING([whether $F77 can link a simple test program])
AC_LINK_IFELSE([AC_LANG_PROGRAM([],[])],[AC_MSG_RESULT([yes])],
  [AC_MSG_RESULT([no])
   AC_MSG_FAILURE([the Fortran 77 compiler $F77 couldn't link a simple test program])])
AC_LANG_POP([Fortran 77])

AM_PATH_PYTHON(2.3.5)
AM_CHECK_PYTHON_HEADERS(,[AC_MSG_FAILURE(could not find Python headers)])

AC_PATH_PROG(F2PY, f2py, false)
if test x"$F2PY" = xfalse ; then
   AC_MSG_ERROR([F2PY not found; see README on f2py])
fi
AC_SUBST(F2PY)

dnl MIRIAD is built with large file support, so we need to have it
dnl too otherwise we'll disagree about the size of off_t

AC_SYS_LARGEFILE
AC_FUNC_FSEEKO

dnl Here we have to work around the fact that __file__ is replaced by
dnl M4. D'oh!

AM_CHECK_PYMOD(numpy,ndarray,,AC_MSG_FAILURE([could not find the Python module "numpy"]))
NUMPY_INCLUDEDIR=`$PYTHON -c 'import numpy, os.path as p ; f = getattr (numpy, "__" + "file__") ; print p.join (p.dirname (f), "core", "include")'`
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
  examples/Makefile
  miriad-python.pc
  mirtask/Makefile
])
AC_OUTPUT

dnl Summarize important configuration options

echo "Configuration summary:"
echo "                   Install prefix: " $prefix
echo "                  MIRIAD found in: " $miriad_loc
echo "                    Building docs? " $DOCS_DESC
echo "   uvchkshadow function available? " $chkshadowstr
