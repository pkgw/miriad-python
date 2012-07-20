dnl Copied from pygtk SVN HEAD, directory m4, 1/16/2007.
dnl Portions Copyright 2012 Peter Williams
dnl   (modified to improve logging)
dnl
dnl It looks like the file originated with Johan Dahlin, but it does not
dnl contain a copyright notice.
dnl
dnl The license of PyGTK is the GNU Lesser General Public License,
dnl version 2.1. We assume that this file is licensed under those
dnl terms. That file is included with this software in the file
dnl LICENSE.LGPLv2.1.

## this one is commonly used with AM_PATH_PYTHONDIR ...
dnl AM_CHECK_PYMOD(MODNAME [,SYMBOL [,ACTION-IF-FOUND [,ACTION-IF-NOT-FOUND]]])
dnl Check if a module containing a given symbol is visible to python.
AC_DEFUN([AM_CHECK_PYMOD],
[AC_REQUIRE([AM_PATH_PYTHON])
py_mod_var=`echo $1['_']$2 | sed 'y%./+-%__p_%'`
AC_MSG_CHECKING(for ifelse([$2],[],,[$2 in ])python module $1)
AC_CACHE_VAL(py_cv_mod_$py_mod_var, [
ifelse([$2],[], [prog="try:
  import $1
except ImportError:
  raise"], [prog="import $1 ; $1.$2"])
echo "$as_me:$LINENO: $PYTHON -c \"$prog\"" >&AS_MESSAGE_LOG_FD
$PYTHON -c "$prog" 1>&AS_MESSAGE_LOG_FD 2>&AS_MESSAGE_LOG_FD
_py_status=$?
echo "$as_me:$LINENO: \$? = $_py_status" >&AS_MESSAGE_LOG_FD
if (exit $_py_status)
  then
    eval "py_cv_mod_$py_mod_var=yes"
  else
    eval "py_cv_mod_$py_mod_var=no"
  fi
])
py_val=`eval "echo \`echo '$py_cv_mod_'$py_mod_var\`"`
if test "x$py_val" != xno; then
  AC_MSG_RESULT(yes)
  echo "$as_me:$LINENO: found $1 at:" >&AS_MESSAGE_LOG_FD
  dnl m4 parses __file__:
  $PYTHON -c "import $1; print getattr($1,'__'+'file__')" >&AS_MESSAGE_LOG_FD
  ifelse([$3], [],, [$3
])dnl
else
  AC_MSG_RESULT(no)
  echo "$as_me:$LINENO: search path was:" >&AS_MESSAGE_LOG_FD
  $PYTHON -c "import sys; print ' '.join(sys.path)" >&AS_MESSAGE_LOG_FD
  ifelse([$4], [],, [$4
])dnl
fi
])

dnl a macro to check for ability to create python extensions
dnl  AM_CHECK_PYTHON_HEADERS([ACTION-IF-POSSIBLE], [ACTION-IF-NOT-POSSIBLE])
dnl function also defines PYTHON_INCLUDES
AC_DEFUN([AM_CHECK_PYTHON_HEADERS],
[AC_REQUIRE([AM_PATH_PYTHON])
AC_MSG_CHECKING(for headers required to compile python extensions)
dnl deduce PYTHON_INCLUDES
py_prefix=`$PYTHON -c "import sys; print sys.prefix"`
py_exec_prefix=`$PYTHON -c "import sys; print sys.exec_prefix"`
PYTHON_INCLUDES="-I${py_prefix}/include/python${PYTHON_VERSION}"
if test "$py_prefix" != "$py_exec_prefix"; then
  PYTHON_INCLUDES="$PYTHON_INCLUDES -I${py_exec_prefix}/include/python${PYTHON_VERSION}"
fi
AC_SUBST(PYTHON_INCLUDES)
dnl check if the headers exist:
save_CPPFLAGS="$CPPFLAGS"
CPPFLAGS="$CPPFLAGS $PYTHON_INCLUDES"
AC_TRY_CPP([#include <Python.h>],dnl
[AC_MSG_RESULT(found)
$1],dnl
[AC_MSG_RESULT(not found)
$2])
CPPFLAGS="$save_CPPFLAGS"
])
