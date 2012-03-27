/*
 * Copyright 2009-2012 Peter Williams
 *
 * This file is part of miriad-python.
 *
 * Miriad-python is free software: you can redistribute it and/or
 * modify it under the terms of the GNU General Public License as
 * published by the Free Software Foundation, either version 3 of the
 * License, or (at your option) any later version.
 *
 * Miriad-python is distributed in the hope that it will be useful, but
 * WITHOUT ANY WARRANTY; without even the implied warranty of
 * MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
 * General Public License for more details.
 *
 * You should have received a copy of the GNU General Public License
 * along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.
 */

#include "mirtasksupport.h"

#include <string.h> /* strerror */

#include <numpy/ndarrayobject.h>
#include <numpy/arrayscalars.h>

/* MIRIAD installs wcslib headers inside $(prefix)/include/miriad-c/wcslib
 * so this should just work. There's some danger here though since we
 * might pick up system wcslib headers if we're being compiled with a miriad
 * that doesn't include these headers. And there is of course the other
 * issue that pywcs will almost definitely be linked with a system wcslib
 * rather than MIRIAD's private version, which presumably will lead to
 * bad things happening. So far stuff seems to work, though ...
 */

#include <wcslib/wcs.h>

#include "miriad.h"

#define BUFSZ 512

static int check_iostat (int iostat);

static int
check_iostat (int iostat)
{
    if (iostat == 0)
	return 0;

    errno = iostat;
    PyErr_SetFromErrno (PyExc_IOError);
    return 1;
}

#define CHECK_IOSTAT(iostat) if (check_iostat (iostat)) return NULL


/* Array-checking utilities */

static int
check_int_array (PyObject *array, char *argname)
{
    if (!PyArray_ISINTEGER (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be an integer ndarray", argname);
	return 1;
    }

    if (PyArray_ITEMSIZE (array) != NPY_SIZEOF_INT) {
	PyErr_Format (PyExc_ValueError, "%s must be a plain-int-sized ndarray", argname);
	return 1;
    }

    if (!PyArray_ISCONTIGUOUS (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be a contiguous ndarray", argname);
	return 1;
    }

    return 0;
}


static int
check_float_array (PyObject *array, char *argname)
{
    if (!PyArray_ISFLOAT (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be an float ndarray", argname);
	return 1;
    }

    if (PyArray_ITEMSIZE (array) != NPY_SIZEOF_FLOAT) {
	PyErr_Format (PyExc_ValueError, "%s must be a plain-float-sized ndarray", argname);
	return 1;
    }

    if (!PyArray_ISCONTIGUOUS (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be a contiguous ndarray", argname);
	return 1;
    }

    return 0;
}


static int
check_double_array (PyObject *array, char *argname)
{
    if (!PyArray_ISFLOAT (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be an float ndarray", argname);
	return 1;
    }

    if (PyArray_ITEMSIZE (array) != NPY_SIZEOF_DOUBLE) {
	PyErr_Format (PyExc_ValueError, "%s must be a double-sized ndarray", argname);
	return 1;
    }

    if (!PyArray_ISCONTIGUOUS (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be a contiguous ndarray", argname);
	return 1;
    }

    return 0;
}


static int
check_complexf_array (PyObject *array, char *argname)
{
    if (!PyArray_ISCOMPLEX (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be a complex ndarray", argname);
	return 1;
    }

    if (PyArray_ITEMSIZE (array) != 2*NPY_SIZEOF_FLOAT) {
	PyErr_Format (PyExc_ValueError, "%s must be a plain-complex-sized ndarray", argname);
	return 1;
    }

    if (!PyArray_ISCONTIGUOUS (array)) {
	PyErr_Format (PyExc_ValueError, "%s must be a contiguous ndarray", argname);
	return 1;
    }

    return 0;
}


/* hio.c */

static PyObject *
py_hopen (PyObject *self, PyObject *args)
{
    char *name, *status;
    int tno, iostat;

    if (!PyArg_ParseTuple (args, "ss", &name, &status))
	return NULL;

    MTS_CHECK_BUG;
    hopen_c (&tno, name, status, &iostat);
    CHECK_IOSTAT(iostat);

    return Py_BuildValue("i", tno);
}

static PyObject *
py_hflush (PyObject *self, PyObject *args)
{
    int tno, iostat;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    hflush_c (tno, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}


static PyObject *
py_habort (PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple (args, ""))
	return NULL;

    MTS_CHECK_BUG;
    habort_c ();

    Py_RETURN_NONE;
}

static PyObject *
py_hrm (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    hrm_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_hclose (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    hclose_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_hdelete (PyObject *self, PyObject *args)
{
    int tno, iostat;
    char *itemname;

    if (!PyArg_ParseTuple (args, "is", &tno, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    hdelete_c (tno, itemname, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}

static PyObject *
py_haccess (PyObject *self, PyObject *args)
{
    int tno, itno, iostat;
    char *itemname, *status;

    if (!PyArg_ParseTuple (args, "iss", &tno, &itemname, &status))
	return NULL;

    MTS_CHECK_BUG;
    haccess_c (tno, &itno, itemname, status, &iostat);
    CHECK_IOSTAT(iostat);

    return Py_BuildValue ("i", itno);
}

static PyObject *
py_hmode (PyObject *self, PyObject *args)
{
    int tno;
    char mode[8];

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    hmode_c (tno, mode);

    return Py_BuildValue ("s", mode);
}

static PyObject *
py_hexists (PyObject *self, PyObject *args)
{
    int tno, ret;
    char *itemname;

    if (!PyArg_ParseTuple (args, "is", &tno, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    ret = hexists_c (tno, itemname);

    return Py_BuildValue ("i", ret);
}

static PyObject *
py_hdaccess (PyObject *self, PyObject *args)
{
    int ihandle, iostat;

    if (!PyArg_ParseTuple (args, "i", &ihandle))
	return NULL;

    MTS_CHECK_BUG;
    hdaccess_c (ihandle, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}

static PyObject *
py_hsize (PyObject *self, PyObject *args)
{
    int ihandle;
    off_t retval;

    if (!PyArg_ParseTuple (args, "i", &ihandle))
	return NULL;

    MTS_CHECK_BUG;
    retval = hsize_c (ihandle);

    return Py_BuildValue ("l", (long) retval);
}


static PyObject *
py_hio_generic (PyObject *self, PyObject *args)
{
    int iswrite, ihandle, mirtype, iostat;
    long offset, nbytes;
    PyObject *buf;

    if (!PyArg_ParseTuple (args, "iiO!ll", &iswrite, &ihandle, &PyArray_Type,
			   &buf, &offset, &nbytes))
	return NULL;

    if (!PyArray_ISCONTIGUOUS (buf)) {
	PyErr_SetString (PyExc_ValueError, "buf must be a contiguous ndarray");
	return NULL;
    }

    MTS_CHECK_BUG;

    switch (PyArray_TYPE (buf)) {
    case NPY_INT8:
    case NPY_UINT8:
	mirtype = H_BYTE;
	break;
    case NPY_INT16:
	/* NOTE: int16s have to be special-cased by the caller because
	 * MIRIAD unpacks the int16s into platform ints inside hio. */
	mirtype = H_INT2;
	break;
    case NPY_INT32:
	mirtype = H_INT;
	break;
    case NPY_INT64:
	mirtype = H_INT8;
	break;
    case NPY_FLOAT32:
	mirtype = H_REAL;
	break;
    case NPY_FLOAT64:
	mirtype = H_DBLE;
	break;
    case NPY_COMPLEX64:
	mirtype = H_CMPLX;
	break;
    default:
	PyErr_Format (PyExc_ValueError, "unhandled buffer type %c",
		      ((PyArrayObject *) buf)->descr->type);
	return NULL;
    }

    hio_c (ihandle, iswrite, mirtype, PyArray_DATA (buf), offset, nbytes, &iostat);
    CHECK_IOSTAT(iostat);
    Py_RETURN_NONE;
}


/* headio */

static PyObject *
py_hisopen (PyObject *self, PyObject *args)
{
    int tno;
    char *status;

    if (!PyArg_ParseTuple (args, "is", &tno, &status))
	return NULL;

    MTS_CHECK_BUG;
    hisopen_c (tno, status);

    Py_RETURN_NONE;
}

static PyObject *
py_hiswrite (PyObject *self, PyObject *args)
{
    int tno;
    char *text;

    if (!PyArg_ParseTuple (args, "is", &tno, &text))
	return NULL;

    MTS_CHECK_BUG;
    hiswrite_c (tno, text);

    Py_RETURN_NONE;
}


static PyObject *
py_hisclose (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    hisclose_c (tno);

    Py_RETURN_NONE;
}


static PyObject *
py_wrhd_generic (PyObject *self, PyObject *args)
{
    int tno, v;
    char *itemname;
    PyObject *value;

    if (!PyArg_ParseTuple (args, "isO", &tno, &itemname, &value))
	return NULL;

    MTS_CHECK_BUG;

    v = PyObject_IsInstance (value, (PyObject *) &PyString_Type);
    if (v < 0)
	return NULL;
    if (v) {
	wrhda_c (tno, itemname, PyString_AsString (value));
	Py_RETURN_NONE;
    }

    if (!PyArray_CheckScalar (value)) {
	PyErr_SetString (PyExc_ValueError, "value must be a numpy scalar");
	return NULL;
    }

    /* Assume that if the first IsInstance check doesn't give an error,
     * neither will the rest. */

    v = PyObject_IsInstance (value, (PyObject *) &PyInt32ArrType_Type);
    if (v < 0)
	return NULL;
    if (v)
	wrhdi_c (tno, itemname, PyArrayScalar_VAL (value, Int32));
    else if (PyObject_IsInstance (value, (PyObject *) &PyInt64ArrType_Type) > 0)
	wrhdl_c (tno, itemname, PyArrayScalar_VAL (value, Int64));
    else if (PyObject_IsInstance (value, (PyObject *) &PyFloat32ArrType_Type) > 0)
	wrhdr_c (tno, itemname, PyArrayScalar_VAL (value, Float32));
    else if (PyObject_IsInstance (value, (PyObject *) &PyFloat64ArrType_Type) > 0)
	wrhdd_c (tno, itemname, PyArrayScalar_VAL (value, Float64));
    else if (PyObject_IsInstance (value, (PyObject *) &PyComplex64ArrType_Type) > 0)
	wrhdc_c (tno, itemname, (float *) &(PyArrayScalar_VAL (value, Complex64)));
    else {
	PyErr_SetString (PyExc_ValueError, "value is of unexpected type");
	return NULL;
    }

    Py_RETURN_NONE;
}


static PyObject *
py_rdhd_generic (PyObject *self, PyObject *args)
{
    int tno, n, iostat, hdhandle;
    char *itemname;
    char buffer[BUFSZ], type[32];
    PyObject *result;

    if (!PyArg_ParseTuple (args, "is", &tno, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    hdprobe_c (tno, itemname, buffer, BUFSZ, type, &n);

    if (strcmp (type, "nonexistent") == 0)
	Py_RETURN_NONE;

    if (strcmp (type, "unknown") == 0) {
	PyErr_Format (PyExc_ValueError, "item \"%s\" is not of a well-defined type",
		      itemname);
	return NULL;
    }

    if (n == 0) {
	PyErr_Format (PyExc_ValueError, "the size of item \"%s\" couldn't be determined",
		      itemname);
	return NULL;
    }

    if (strcmp (type, "binary") == 0) {
	PyErr_Format (PyExc_ValueError, "item \"%s\" is of a mixed binary type",
		      itemname);
	return NULL;
    }

    if (strcmp (type, "text") == 0) {
	PyErr_Format (PyExc_ValueError, "item \"%s\" is of an extended textual type",
		      itemname);
	return NULL;
    }

    if (strcmp (type, "character") == 0)
	return PyString_FromString (buffer);

    if (n != 1) {
	PyErr_Format (PyExc_ValueError, "the size of item \"%s\" is %d, not one",
		      itemname, n);
	return NULL;
    }

    haccess_c (tno, &hdhandle, itemname, "read", &iostat);
    CHECK_IOSTAT (iostat);

    if (strcmp (type, "real") == 0) {
	result = PyArrayScalar_New (Float32);
	hio_c (hdhandle, FALSE, H_REAL, (char *) &(PyArrayScalar_VAL (result, Float32)),
	       4, 4, &iostat);
    } else if (strcmp (type, "double") == 0) {
	result = PyArrayScalar_New (Float64);
	hio_c (hdhandle, FALSE, H_DBLE, (char *) &(PyArrayScalar_VAL (result, Float64)),
	       8, 8, &iostat);
    } else if (strcmp (type, "integer*2") == 0) {
	result = PyArrayScalar_New (Int16);
	hio_c (hdhandle, FALSE, H_INT2, (char *) &(PyArrayScalar_VAL (result, Int16)),
	       4, 2, &iostat);
    } else if (strcmp (type, "integer") == 0) {
	result = PyArrayScalar_New (Int32);
	hio_c (hdhandle, FALSE, H_INT, (char *) &(PyArrayScalar_VAL (result, Int32)),
	       4, 4, &iostat);
    } else if (strcmp (type, "integer*8") == 0) {
	result = PyArrayScalar_New (Int64);
	hio_c (hdhandle, FALSE, H_INT8, (char *) &(PyArrayScalar_VAL (result, Int64)),
	       8, 8, &iostat);
    } else if (strcmp (type, "complex") == 0) {
	result = PyArrayScalar_New (Complex64);
	hio_c (hdhandle, FALSE, H_CMPLX, (char *) &(PyArrayScalar_VAL (result, Complex64)),
	       8, 8, &iostat);
    } else {
	PyErr_Format (PyExc_ValueError, "unexpected type \"%s\" for item \"%s\"",
		      type, itemname);
	result = NULL;
    }

    CHECK_IOSTAT (iostat);
    hdaccess_c (hdhandle, &iostat);
    CHECK_IOSTAT (iostat);
    return result;
}


static PyObject *
py_hdcopy (PyObject *self, PyObject *args)
{
    int tin, tout;
    char *itemname;

    if (!PyArg_ParseTuple (args, "iis", &tin, &tout, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    hdcopy_c (tin, tout, itemname);

    Py_RETURN_NONE;
}

static PyObject *
py_hdprsnt (PyObject *self, PyObject *args)
{
    int tno, retval;
    char *itemname;

    if (!PyArg_ParseTuple (args, "is", &tno, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    retval = hdprsnt_c (tno, itemname);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_hdprobe (PyObject *self, PyObject *args)
{
    int tno;
    char *itemname;
    char descr[BUFSZ], type[32];
    int n;

    if (!PyArg_ParseTuple (args, "is", &tno, &itemname))
	return NULL;

    MTS_CHECK_BUG;
    hdprobe_c (tno, itemname, descr, BUFSZ, type, &n);

    return Py_BuildValue ("(ssi)", descr, type, n);
}


/* dio */

/* uvio */

static PyObject *
py_uvopen (PyObject *self, PyObject *args)
{
    int tno;
    char *name, *status;

    if (!PyArg_ParseTuple (args, "ss", &name, &status))
	return NULL;

    MTS_CHECK_BUG;
    uvopen_c (&tno, name, status);

    return Py_BuildValue ("i", tno);
}

static PyObject *
py_uvclose (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    uvclose_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_uvflush (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    uvflush_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_uvnext (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    uvnext_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_uvrewind (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    uvrewind_c (tno);

    Py_RETURN_NONE;
}

static PyObject *
py_uvcopyvr (PyObject *self, PyObject *args)
{
    int tno, tout;

    if (!PyArg_ParseTuple (args, "ii", &tno, &tout))
	return NULL;

    MTS_CHECK_BUG;
    uvcopyvr_c (tno, tout);

    Py_RETURN_NONE;
}

static PyObject *
py_uvupdate (PyObject *self, PyObject *args)
{
    int tno, retval;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    retval = uvupdate_c (tno);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_uvvarini (PyObject *self, PyObject *args)
{
    int tno, vhan;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    uvvarini_c (tno, &vhan);

    return Py_BuildValue ("i", vhan);
}

static PyObject *
py_uvvarset (PyObject *self, PyObject *args)
{
    int vhan;
    char *var;

    if (!PyArg_ParseTuple (args, "is", &vhan, &var))
	return NULL;

    MTS_CHECK_BUG;
    uvvarset_c (vhan, var);

    Py_RETURN_NONE;
}

static PyObject *
py_uvvarcpy (PyObject *self, PyObject *args)
{
    int vhan, tout;

    if (!PyArg_ParseTuple (args, "ii", &vhan, &tout))
	return NULL;

    MTS_CHECK_BUG;
    uvvarcpy_c (vhan, tout);

    Py_RETURN_NONE;
}

static PyObject *
py_uvvarupd (PyObject *self, PyObject *args)
{
    int vhan, retval;

    if (!PyArg_ParseTuple (args, "i", &vhan))
	return NULL;

    MTS_CHECK_BUG;
    retval = uvvarupd_c (vhan);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_uvgetvra (PyObject *self, PyObject *args)
{
    int tno;
    char *var, value[BUFSZ];

    if (!PyArg_ParseTuple (args, "is", &tno, &var))
	return NULL;

    MTS_CHECK_BUG;
    uvgetvra_c (tno, var, value, BUFSZ);

    return Py_BuildValue ("s", value);
}

static PyObject *
py_uvgetvri (PyObject *self, PyObject *args)
{
    int tno, n;
    char *var;
    PyObject *retval;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    /* See py_uvgetvrj for commentary on why we are allocating
       a platform "int" and not specifically an int32.
    */

    dims[0] = n;
    retval = PyArray_SimpleNew (1, dims, NPY_INT);
    uvgetvri_c (tno, var, PyArray_DATA (retval), n);
    return retval;
}

static PyObject *
py_uvgetvrj (PyObject *self, PyObject *args)
{
    int tno, n;
    char *var;
    PyObject *retval;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    /* So, the uvgetvr* functions convert variables from their
       storage ("external") type to in-memory ("internal") types.
       A 16-bit integer is stored as two bytes, but expanded to
       a platform "int", which will presumably be 32 or 64 bytes.
       This is why we allocate a plain int array, and not one of
       type NPY_INT16.
     */

    dims[0] = n;
    retval = PyArray_SimpleNew (1, dims, NPY_INT);
    uvgetvrj_c (tno, var, PyArray_DATA (retval), n);
    return retval;
}

static PyObject *
py_uvgetvrr (PyObject *self, PyObject *args)
{
    int tno, n;
    char *var;
    PyObject *retval;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    dims[0] = n;
    retval = PyArray_SimpleNew (1, dims, NPY_FLOAT);
    uvgetvrr_c (tno, var, PyArray_DATA (retval), n);
    return retval;
}

static PyObject *
py_uvgetvrd (PyObject *self, PyObject *args)
{
    int tno, n;
    char *var;
    PyObject *retval;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    dims[0] = n;
    retval = PyArray_SimpleNew (1, dims, NPY_DOUBLE);
    uvgetvrd_c (tno, var, PyArray_DATA (retval), n);
    return retval;
}

static PyObject *
py_uvgetvrc (PyObject *self, PyObject *args)
{
    int tno, n;
    char *var;
    PyObject *retval;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    dims[0] = n;
    retval = PyArray_SimpleNew (1, dims, NPY_CFLOAT);
    uvgetvrc_c (tno, var, PyArray_DATA (retval), n);
    return retval;
}


static PyObject *
py_uvrdvr_generic (PyObject *self, PyObject *args)
{
    int tno, length, updated;
    char *var, type;
    PyObject *result;

    if (!PyArg_ParseTuple (args, "is", &tno, &var))
	return NULL;

    MTS_CHECK_BUG;
    uvprobvr_c (tno, var, &type, &length, &updated);

    if (type == ' ' || length == 0)
	Py_RETURN_NONE;

    if (type == 'j') {
	/* uvrdvr_c doesn't support H_INT2. Do it ourselves, less
	 efficiently.  As in py_uvgetvrj, the int2 is expanded to
	 sizeof(int) by MIRIAD. We un-convert to maintain the type
	 information. */
	npy_intp dims[1] = { length };
	PyObject *tmp = PyArray_SimpleNew (1, dims, NPY_INT);
	uvgetvr_c (tno, H_INT2, var, PyArray_DATA (tmp), length);
	result = PyArrayScalar_New (Int16);
	PyArrayScalar_ASSIGN (result, Int16, *((int *) PyArray_DATA (tmp)));
	Py_XDECREF (tmp);
	return result;
    }

    switch (type) {
    case 'a':
	/* A little bit of special-casing; we don't fetch just one byte ... */
	result = PyString_FromStringAndSize (NULL, length + 1);
	uvgetvr_c (tno, H_BYTE, var, PyString_AsString (result), length + 1);
	break;
    case 'i':
	result = PyArrayScalar_New (Int32);
	uvrdvr_c (tno, H_INT, var, (char *) &(PyArrayScalar_VAL (result, Int32)), 0, 1);
	break;
    case 'r':
	result = PyArrayScalar_New (Float32);
	uvrdvr_c (tno, H_REAL, var, (char *) &(PyArrayScalar_VAL (result, Float32)), 0, 1);
	break;
    case 'd':
	result = PyArrayScalar_New (Float64);
	uvrdvr_c (tno, H_DBLE, var, (char *) &(PyArrayScalar_VAL (result, Float64)), 0, 1);
	break;
    case 'c':
	result = PyArrayScalar_New (Complex64);
	uvrdvr_c (tno, H_CMPLX, var, (char *) &(PyArrayScalar_VAL (result, Complex64)), 0, 1);
	break;
    default:
	PyErr_Format (PyExc_RuntimeError, "unknown MIRIAD typecode %c", type);
	return NULL;
    }

    return result;
}


/* skip uvputvr_c generic versions */

static PyObject *
py_uvprobvr (PyObject *self, PyObject *args)
{
    int tno, length, updated;
    char *var, type;

    if (!PyArg_ParseTuple (args, "is", &tno, &var))
	return NULL;

    MTS_CHECK_BUG;
    uvprobvr_c (tno, var, &type, &length, &updated);

    return Py_BuildValue ("cii", type, length, updated);
}

static PyObject *
py_uvtrack (PyObject *self, PyObject *args)
{
    int tno;
    char *name, *switches;

    if (!PyArg_ParseTuple (args, "iss", &tno, &name, &switches))
	return NULL;

    MTS_CHECK_BUG;
    uvtrack_c (tno, name, switches);

    Py_RETURN_NONE;
}

static PyObject *
py_uvscan (PyObject *self, PyObject *args)
{
    int tno, retval;
    char *var;

    if (!PyArg_ParseTuple (args, "is", &tno, &var))
	return NULL;

    MTS_CHECK_BUG;
    retval = uvscan_c (tno, var);
    if (retval != -1)
	CHECK_IOSTAT(retval);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_uvread (PyObject *self, PyObject *args)
{
    int tno, n, size, nread;
    PyObject *preamble, *data, *flags;

    if (!PyArg_ParseTuple (args, "iO!O!O!i", &tno, &PyArray_Type, &preamble,
			   &PyArray_Type, &data, &PyArray_Type, &flags, &n))
	return NULL;

    if (check_double_array (preamble, "preamble"))
	return NULL;

    if (check_complexf_array (data, "data"))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    /* higher-level checks */

    size = PyArray_SIZE (preamble);

    if (size != 4 && size != 5) {
	PyErr_SetString (PyExc_ValueError, "preamble array must have 4 or 5 elements");
	return NULL;
    }

    size = PyArray_SIZE (flags);
    if (size < n) {
	PyErr_Format (PyExc_ValueError, "flags array must have at least %d elements",
		      n);
	return NULL;
    }

    size = PyArray_SIZE (data);
    if (size < n) {
	PyErr_Format (PyExc_ValueError, "data array must have at least %d elements",
		      n);
	return NULL;
    }

    /* finally ... */
    MTS_CHECK_BUG;
    uvread_c (tno, PyArray_DATA (preamble), PyArray_DATA (data),
	      PyArray_DATA (flags), n, &nread);

    return PyInt_FromLong ((long) nread);
}

static PyObject *
py_uvwrite (PyObject *self, PyObject *args)
{
    int tno, n, size;
    PyObject *preamble, *data, *flags;

    if (!PyArg_ParseTuple (args, "iO!O!O!i", &tno, &PyArray_Type, &preamble,
			   &PyArray_Type, &data, &PyArray_Type, &flags, &n))
	return NULL;

    if (check_double_array (preamble, "preamble"))
	return NULL;

    if (check_complexf_array (data, "data"))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    /* higher-level checks */

    size = PyArray_SIZE (preamble);

    if (size != 4 && size != 5) {
	PyErr_SetString (PyExc_ValueError, "preamble array must have 4 or 5 elements");
	return NULL;
    }

    size = PyArray_SIZE (flags);
    if (size < n) {
	PyErr_Format (PyExc_ValueError, "flags array must have at least %d elements",
		      n);
	return NULL;
    }

    size = PyArray_SIZE (data);
    if (size < n) {
	PyErr_Format (PyExc_ValueError, "data array must have at least %d elements",
		      n);
	return NULL;
    }

    /* finally ... */
    MTS_CHECK_BUG;
    uvwrite_c (tno, PyArray_DATA (preamble), PyArray_DATA (data),
	       PyArray_DATA (flags), n);

    Py_RETURN_NONE;
}

/* skip uvwwrite_c ... lazy */
/* skip uvsela_c, ... too lowlevel */

static PyObject *
py_uvselect (PyObject *self, PyObject *args)
{
    int tno, flag;
    char *object;
    double p1, p2;

    if (!PyArg_ParseTuple (args, "isddi", &tno, &object, &p1, &p2,
			   &flag))
	return NULL;

    MTS_CHECK_BUG;
    uvselect_c (tno, object, p1, p2, flag);

    Py_RETURN_NONE;
}

static PyObject *
py_uvset (PyObject *self, PyObject *args)
{
    int tno, n;
    char *object, *type;
    double p1, p2, p3;

    if (!PyArg_ParseTuple (args, "issiddd", &tno, &object, &type,
			   &n, &p1, &p2, &p3))
	return NULL;

    MTS_CHECK_BUG;
    uvset_c (tno, object, type, n, p1, p2, p3);

    Py_RETURN_NONE;
}

/* uvwread, uvwflgwr skipped */

static PyObject *
py_uvflgwr (PyObject *self, PyObject *args)
{
    int tno;
    PyObject *flags;

    if (!PyArg_ParseTuple (args, "iO!", &tno, &PyArray_Type, &flags))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    MTS_CHECK_BUG;
    uvflgwr_c (tno, PyArray_DATA (flags));
    Py_RETURN_NONE;
}

/* uvinfo */

static PyObject *
py_uvinfo (PyObject *self, PyObject *args)
{
    int tno;
    char *object;
    PyObject *data;

    if (!PyArg_ParseTuple (args, "isO!", &tno, &object, &PyArray_Type, &data))
	return NULL;

    if (check_double_array (data, "data"))
	return NULL;

    MTS_CHECK_BUG;
    uvinfo_c (tno, object, PyArray_DATA (data));
    Py_RETURN_NONE;
}

/* uvio macros */

static PyObject *
py_uvputvri (PyObject *self, PyObject *args)
{
    int tno;
    char *name;
    PyObject *value;

    if (!PyArg_ParseTuple (args, "isO!", &tno, &name, &PyArray_Type, &value))
	return NULL;

    if (check_int_array (value, "value"))
	return NULL;

    MTS_CHECK_BUG;
    uvputvri_c (tno, name, PyArray_DATA (value), PyArray_SIZE (value));
    Py_RETURN_NONE;
}

static PyObject *
py_uvputvrr (PyObject *self, PyObject *args)
{
    int tno;
    char *name;
    PyObject *value;

    if (!PyArg_ParseTuple (args, "isO!", &tno, &name,
			   &PyArray_Type, &value))
	return NULL;

    if (check_float_array (value, "value"))
	return NULL;

    MTS_CHECK_BUG;
    uvputvrr_c (tno, name, PyArray_DATA (value), PyArray_SIZE (value));
    Py_RETURN_NONE;
}

static PyObject *
py_uvputvrd (PyObject *self, PyObject *args)
{
    int tno;
    char *name;
    PyObject *value;

    if (!PyArg_ParseTuple (args, "isO!", &tno, &name,
			   &PyArray_Type, &value))
	return NULL;

    if (check_double_array (value, "value"))
	return NULL;

    MTS_CHECK_BUG;
    uvputvrd_c (tno, name, PyArray_DATA (value), PyArray_SIZE (value));
    Py_RETURN_NONE;
}

static PyObject *
py_uvputvra (PyObject *self, PyObject *args)
{
    int tno;
    char *name, *value;

    if (!PyArg_ParseTuple (args, "iss", &tno, &name, &value))
	return NULL;

    MTS_CHECK_BUG;
    uvputvra_c (tno, name, value);
    Py_RETURN_NONE;
}

#if HAVE_UVCHKSHADOW
static PyObject *
py_uvchkshadow (PyObject *self, PyObject *args)
{
    int tno;
    double diameter_meters;

    if (!PyArg_ParseTuple (args, "id", &tno, &diameter_meters))
	return NULL;

    MTS_CHECK_BUG;

    if (uvchkshadow_c (tno, diameter_meters))
	Py_RETURN_TRUE;
    Py_RETURN_FALSE;
}

static PyObject *
py_probe_uvchkshadow (PyObject *self, PyObject *args)
{
    Py_RETURN_TRUE;
}
#else
static PyObject *
py_uvchkshadow (PyObject *self, PyObject *args)
{
    PyErr_SetString (PyExc_NotImplementedError,
		     "no uvchkshadow_c() in underlying MIRIAD library");
    return NULL;
}

static PyObject *
py_probe_uvchkshadow (PyObject *self, PyObject *args)
{
    Py_RETURN_FALSE;
}
#endif


/* xyio

Skipped because not used by clients: xymkrd, xymkwr
*/

static PyObject *
py_xyopen (PyObject *self, PyObject *args)
{
    int tno, naxis;
    char *path, *status;
    PyObject *axes;

    if (!PyArg_ParseTuple (args, "ssiO!", &path, &status, &naxis,
			   &PyArray_Type, &axes))
	return NULL;

    if (check_int_array (axes, "axes"))
	return NULL;

    MTS_CHECK_BUG;
    xyopen_c (&tno, path, status, naxis, PyArray_DATA (axes));
    return Py_BuildValue ("i", tno);
}


static PyObject *
py_xyclose (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    xyclose_c (tno);
    Py_RETURN_NONE;
}


static PyObject *
py_xyflush (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    xyflush_c (tno);
    Py_RETURN_NONE;
}


static PyObject *
py_xyread (PyObject *self, PyObject *args)
{
    int tno, index;
    PyObject *data;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &index, &PyArray_Type, &data))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    MTS_CHECK_BUG;
    xyread_c (tno, index, PyArray_DATA (data));
    Py_RETURN_NONE;
}


static PyObject *
py_xywrite (PyObject *self, PyObject *args)
{
    int tno, index;
    PyObject *data;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &index, &PyArray_Type, &data))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    MTS_CHECK_BUG;
    xywrite_c (tno, index, PyArray_DATA (data));
    Py_RETURN_NONE;
}


static PyObject *
py_xyflgrd (PyObject *self, PyObject *args)
{
    int tno, index;
    PyObject *flags;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &index, &PyArray_Type, &flags))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    MTS_CHECK_BUG;
    xyflgrd_c (tno, index, PyArray_DATA (flags));
    Py_RETURN_NONE;
}


static PyObject *
py_xyflgwr (PyObject *self, PyObject *args)
{
    int tno, index;
    PyObject *flags;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &index, &PyArray_Type, &flags))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    MTS_CHECK_BUG;
    xyflgwr_c (tno, index, PyArray_DATA (flags));
    Py_RETURN_NONE;
}


static PyObject *
py_xysetpl (PyObject *self, PyObject *args)
{
    int tno, naxis;
    PyObject *axes;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &naxis, &PyArray_Type, &axes))
	return NULL;

    if (check_int_array (axes, "axes"))
	return NULL;

    MTS_CHECK_BUG;
    xysetpl_c (tno, naxis, PyArray_DATA (axes));
    Py_RETURN_NONE;
}


/* maskio */

static PyObject *
py_mkopen (PyObject *self, PyObject *args)
{
    int tno;
    char *name, *status, *handle;
    long handint;

    if (!PyArg_ParseTuple (args, "iss", &tno, &name, &status))
	return NULL;

    MTS_CHECK_BUG;
    handle = mkopen_c (tno, name, status);
    if (handle == NULL) {
	PyErr_Format (PyExc_IOError, "Failed to open mask item \"%s\"", name);
	return NULL;
    }

    handint = (long) handle;

    return Py_BuildValue ("l", handint);
}


static PyObject *
py_mkclose (PyObject *self, PyObject *args)
{
    long handint;
    char *handle;

    if (!PyArg_ParseTuple (args, "l", &handint))
	return NULL;

    handle = (char *) handint;

    MTS_CHECK_BUG;
    mkclose_c (handle);

    Py_RETURN_NONE;
}


static PyObject *
py_mkread (PyObject *self, PyObject *args)
{
    long handint, offset;
    char *handle;
    int mode, n, nread, nsize;
    PyObject *flags;

    if (!PyArg_ParseTuple (args, "liO!li", &handint, &mode, &PyArray_Type,
			   &flags, &offset, &n))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    handle = (char *) handint;
    nsize = PyArray_SIZE (flags);

    /* handle: handle to flags state item
     * mode: flag storage mode: MK_FLAGS = 1 (expanded) or MK_RUNS = 2 (RLE)
     * flags: integer array in which to store flags
     * offset: offset into the file at which to read; counted in bits
     * n: number of flag bits to read
     * nsize: size of flag buffer
     * return value: number of flag items read
     */

    MTS_CHECK_BUG;
    nread = mkread_c (handle, mode, PyArray_DATA (flags), (off_t) offset, n, nsize);

    return Py_BuildValue ("i", nread);
}


static PyObject *
py_mkwrite (PyObject *self, PyObject *args)
{
    long handint, offset;
    char *handle;
    int mode, n, nsize;
    PyObject *flags;

    if (!PyArg_ParseTuple (args, "liO!li", &handint, &mode, &PyArray_Type,
			   &flags, &offset, &n))
	return NULL;

    if (check_int_array (flags, "flags"))
	return NULL;

    handle = (char *) handint;
    nsize = PyArray_SIZE (flags);

    /* handle: handle to flags state item
     * mode: flag storage mode: MK_FLAGS = 1 (expanded) or MK_RUNS = 2 (RLE)
     * flags: integer array in which to store flags
     * offset: offset into the file at which to read; counted in bits
     * n: number of flag bits to read
     * nsize: size of flag buffer; if MK_RUNS, should be set such that decoding
     *  @nsize items will result in @n flag values.
     */

    MTS_CHECK_BUG;
    mkwrite_c (handle, mode, PyArray_DATA (flags), (off_t) offset, n, nsize);

    Py_RETURN_NONE;
}


static PyObject *
py_mkflush (PyObject *self, PyObject *args)
{
    long handint;
    char *handle;

    if (!PyArg_ParseTuple (args, "l", &handint))
	return NULL;

    handle = (char *) handint;

    MTS_CHECK_BUG;
    mkflush_c (handle);

    Py_RETURN_NONE;
}


/* xyzio

Skipped, due to extremely rare usage: xyzplnrd, xyzpixwr, xyzplnwr
 */

static PyObject *
py_xyzopen (PyObject *self, PyObject *args)
{
    int tno, naxis;
    char *path, *status;
    PyObject *axlen;

    if (!PyArg_ParseTuple (args, "ssiO!", &path, &status, &naxis,
			   &PyArray_Type, &axlen))
	return NULL;

    if (check_int_array (axlen, "axlen"))
	return NULL;

    MTS_CHECK_BUG;
    xyzopen_c (&tno, path, status, &naxis, PyArray_DATA (axlen));
    return Py_BuildValue ("ii", tno, naxis);
}


static PyObject *
py_xyzclose (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    xyzclose_c (tno);
    Py_RETURN_NONE;
}


static PyObject *
py_xyzflush (PyObject *self, PyObject *args)
{
    int tno;

    if (!PyArg_ParseTuple (args, "i", &tno))
	return NULL;

    MTS_CHECK_BUG;
    xyzflush_c (tno);
    Py_RETURN_NONE;
}


static PyObject *
py_xyzsetup (PyObject *self, PyObject *args)
{
    int tno;
    char *subcube;
    PyObject *blc, *trc, *viraxlen, *vircubesize;
    npy_intp dims[1];

    if (!PyArg_ParseTuple (args, "isO!O!", &tno, &subcube, &PyArray_Type, &blc,
			   &PyArray_Type, &trc))
	return NULL;

    if (check_int_array (blc, "blc"))
	return NULL;

    if (check_int_array (trc, "trc"))
	return NULL;

    dims[0] = PyArray_DIM (blc, 0);
    viraxlen = PyArray_SimpleNew (1, dims, NPY_INT);
    vircubesize = PyArray_SimpleNew (1, dims, NPY_INT);

    MTS_CHECK_BUG;
    xyzsetup_c (tno, subcube, PyArray_DATA (blc), PyArray_DATA (trc),
		PyArray_DATA (viraxlen), PyArray_DATA (vircubesize));
    return Py_BuildValue ("OO", viraxlen, vircubesize);
}


static PyObject *
py_xyzs2c (PyObject *self, PyObject *args)
{
    int tno, subcubenr;
    PyObject *coords;

    if (!PyArg_ParseTuple (args, "iiO!", &tno, &subcubenr, &PyArray_Type, &coords))
	return NULL;

    if (check_int_array (coords, "coords"))
	return NULL;

    MTS_CHECK_BUG;
    xyzs2c_c (tno, subcubenr, PyArray_DATA (coords));
    Py_RETURN_NONE;
}


static PyObject *
py_xyzc2s (PyObject *self, PyObject *args)
{
    int tno, subcubenr;
    PyObject *coords;

    if (!PyArg_ParseTuple (args, "iO!", &tno, &PyArray_Type, &coords))
	return NULL;

    if (check_int_array (coords, "coords"))
	return NULL;

    MTS_CHECK_BUG;
    xyzc2s_c (tno, PyArray_DATA (coords), &subcubenr);
    return Py_BuildValue ("i", subcubenr);
}


static PyObject *
py_xyzread (PyObject *self, PyObject *args)
{
    int tno, ndata;
    PyObject *coords, *data, *mask;

    if (!PyArg_ParseTuple (args, "iO!O!O!", &tno, &PyArray_Type, &coords,
	    &PyArray_Type, &data, &PyArray_Type, &mask))
	return NULL;

    if (check_int_array (coords, "coords"))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    if (check_int_array (mask, "mask"))
	return NULL;

    MTS_CHECK_BUG;
    xyzread_c (tno, PyArray_DATA (coords), PyArray_DATA (data), PyArray_DATA (mask),
	       &ndata);
    return Py_BuildValue ("i", ndata);
}


static PyObject *
py_xyzpixrd (PyObject *self, PyObject *args)
{
    int tno, pixnum, mask;
    float data;

    if (!PyArg_ParseTuple (args, "ii", &tno, &pixnum))
	return NULL;

    MTS_CHECK_BUG;
    xyzpixrd_c (tno, pixnum, &data, &mask);
    return Py_BuildValue ("fi", data, mask);
}


static PyObject *
py_xyzprfrd (PyObject *self, PyObject *args)
{
    int tno, profnum, ndata;
    PyObject *data, *mask;

    if (!PyArg_ParseTuple (args, "iiO!O!", &tno, &profnum, &PyArray_Type, &data,
			   &PyArray_Type, &mask))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    if (check_int_array (mask, "mask"))
	return NULL;

    MTS_CHECK_BUG;
    xyzprfrd_c (tno, profnum, PyArray_DATA (data), PyArray_DATA (mask), &ndata);
    return Py_BuildValue ("i", ndata);
}


static PyObject *
py_xyzwrite (PyObject *self, PyObject *args)
{
    int tno, ndata;
    PyObject *coords, *data, *mask;

    if (!PyArg_ParseTuple (args, "iO!O!O!i", &tno, &PyArray_Type, &coords,
			   &PyArray_Type, &data, &PyArray_Type, &mask, &ndata))
	return NULL;

    if (check_int_array (coords, "coords"))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    if (check_int_array (mask, "mask"))
	return NULL;

    MTS_CHECK_BUG;
    xyzwrite_c (tno, PyArray_DATA (coords), PyArray_DATA (data), PyArray_DATA (mask),
		&ndata);
    /* even though ndata is a pointer arg, it's not modified when writing */
    Py_RETURN_NONE;
}


static PyObject *
py_xyzprfwr (PyObject *self, PyObject *args)
{
    int tno, profnum, ndata;
    PyObject *data, *mask;

    if (!PyArg_ParseTuple (args, "iiO!O!i", &tno, &profnum, &PyArray_Type, &data,
			   &PyArray_Type, &mask, &ndata))
	return NULL;

    if (check_float_array (data, "data"))
	return NULL;

    if (check_int_array (mask, "mask"))
	return NULL;

    MTS_CHECK_BUG;
    xyzprfwr_c (tno, profnum, PyArray_DATA (data), PyArray_DATA (mask), &ndata);
    /* even though ndata is a pointer arg, it's not modified when writing */
    Py_RETURN_NONE;
}

/* scrio */

/* key */

static PyObject *
py_keyinit (PyObject *self, PyObject *args)
{
    char *task;

    if (!PyArg_ParseTuple (args, "s", &task))
	return NULL;

    MTS_CHECK_BUG;
    keyinit_c (task);

    Py_RETURN_NONE;
}

static PyObject *
py_keyput (PyObject *self, PyObject *args)
{
    char *task, *string;

    if (!PyArg_ParseTuple (args, "ss", &task, &string))
	return NULL;

    MTS_CHECK_BUG;
    keyput_c (task, string);

    Py_RETURN_NONE;
}

static PyObject *
py_keyini (PyObject *self, PyObject *args)
{
    PyObject *list;
    int len, i;
    char **argv;

    if (!PyArg_ParseTuple (args, "O!", &PyList_Type, &list))
	return NULL;

    MTS_CHECK_BUG;

    /* We must copy the strings individually because keyini
     * modifies them. Could be smarter about memory allocation,
     * but this isn't exactly a performance-sensitive routine. */

    len = PyList_Size (list);
    argv = PyMem_Malloc (sizeof (char *) * len);

    for (i = 0; i < len; i++) {
	PyObject *as_str = PyList_GetItem (list, i);
	char *s = PyString_AsString (as_str);

	argv[i] = PyMem_Malloc (sizeof (char) * (strlen (s) + 1));
	strcpy (argv[i], s);
    }

    keyini_c (len, argv);

    for (i = 0; i < len; i++)
	PyMem_Free (argv[i]);

    PyMem_Free (argv);

    Py_RETURN_NONE;
}

static PyObject *
py_keyfin (PyObject *self, PyObject *args)
{
    if (!PyArg_ParseTuple (args, ""))
	return NULL;

    MTS_CHECK_BUG;
    keyfin_c ();

    Py_RETURN_NONE;
}


static PyObject *
py_keyprsnt (PyObject *self, PyObject *args)
{
    char *keyword;
    int retval;

    if (!PyArg_ParseTuple (args, "s", &keyword))
	return NULL;

    MTS_CHECK_BUG;
    retval = keyprsnt_c (keyword);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_keya (PyObject *self, PyObject *args)
{
    char *keyword, value[BUFSZ], *dflt;

    if (!PyArg_ParseTuple (args, "ss", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keya_c (keyword, value, dflt);

    return Py_BuildValue ("s", value);
}

static PyObject *
py_keyf (PyObject *self, PyObject *args)
{
    char *keyword, value[BUFSZ], *dflt;

    if (!PyArg_ParseTuple (args, "ss", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keyf_c (keyword, value, dflt);

    return Py_BuildValue ("s", value);
}

static PyObject *
py_keyd (PyObject *self, PyObject *args)
{
    char *keyword;
    double value, dflt;

    if (!PyArg_ParseTuple (args, "sd", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keyd_c (keyword, &value, dflt);

    return Py_BuildValue ("d", value);
}

static PyObject *
py_keyr (PyObject *self, PyObject *args)
{
    char *keyword;
    float value, dflt;

    if (!PyArg_ParseTuple (args, "sf", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keyr_c (keyword, &value, dflt);

    return Py_BuildValue ("f", value);
}

static PyObject *
py_keyi (PyObject *self, PyObject *args)
{
    char *keyword;
    int value, dflt;

    if (!PyArg_ParseTuple (args, "si", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keyi_c (keyword, &value, dflt);

    return Py_BuildValue ("i", value);
}

static PyObject *
py_keyl (PyObject *self, PyObject *args)
{
    char *keyword;
    int value, dflt;

    if (!PyArg_ParseTuple (args, "si", &keyword, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    keyl_c (keyword, &value, dflt);

    return Py_BuildValue ("i", value);
}

static PyObject *
py_mkeyd (PyObject *self, PyObject *args)
{
    char *keyword;
    double *vals;
    int n, i, nmax;
    PyObject *retval;

    if (!PyArg_ParseTuple (args, "si", &keyword, &nmax))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (double) * nmax);
    mkeyd_c (keyword, vals, nmax, &n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyFloat_FromDouble (vals[i]));

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_mkeyr (PyObject *self, PyObject *args)
{
    char *keyword;
    float *vals;
    int n, i, nmax;
    PyObject *retval;

    if (!PyArg_ParseTuple (args, "si", &keyword, &nmax))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (float) * nmax);
    mkeyr_c (keyword, vals, nmax, &n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyFloat_FromDouble ((double) vals[i]));

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_mkeyi (PyObject *self, PyObject *args)
{
    char *keyword;
    int *vals;
    int n, i, nmax;
    PyObject *retval;

    if (!PyArg_ParseTuple (args, "si", &keyword, &nmax))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (int) * nmax);
    mkeyi_c (keyword, vals, nmax, &n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyInt_FromLong ((long) vals[i]));

    PyMem_Free (vals);

    return retval;
}

/* mir */

/* interface - not needed, just c <-> fortran helpers */

/* wcs -- some helpers to access WCS routines not provided
 * by pywcs, needed to emulate coReinit to get proper WCS
 * support in MIRIAD images
 *
 * In all of these, would be nice to have some type checking
 * to know we're not scribbling all over random memory.
 **/

typedef struct {
    PyObject_HEAD
    struct wcsprm params;
} MirWCSObject;


static PyObject *
py_mirwcs_set_celoffset (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    int value;

    if (!PyArg_ParseTuple (args, "Oi", &wcs, &value))
	return NULL;

    wcs->params.cel.offset = value;
    Py_RETURN_NONE;
}


static PyObject *
py_mirwcs_set_celphitheta (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    double phi0, theta0;

    if (!PyArg_ParseTuple (args, "Odd", &wcs, &phi0, &theta0))
	return NULL;

    wcs->params.cel.phi0 = phi0;
    wcs->params.cel.theta0 = theta0;
    Py_RETURN_NONE;
}


static PyObject *
py_mirwcs_set_celref (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    double lng0, lat0;

    if (!PyArg_ParseTuple (args, "Odd", &wcs, &lng0, &lat0))
	return NULL;

    wcs->params.cel.ref[0] = lng0;
    wcs->params.cel.ref[1] = lat0;
    Py_RETURN_NONE;
}


static PyObject *
py_mirwcs_set_prjcode (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    char *code;

    if (!PyArg_ParseTuple (args, "Os", &wcs, &code))
	return NULL;

    memset (wcs->params.cel.prj.code, 0, 4);
    strncpy (wcs->params.cel.prj.code, code, 3);
    Py_RETURN_NONE;
}


static PyObject *
py_mirwcs_set_prjpv (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    int index;
    double value;

    if (!PyArg_ParseTuple (args, "Oid", &wcs, &index, &value))
	return NULL;

    wcs->params.cel.prj.pv[index] = value;
    Py_RETURN_NONE;
}


static PyObject *
py_mirwcs_celset (PyObject *self, PyObject *args)
{
    MirWCSObject *wcs;
    int status;

    if (!PyArg_ParseTuple (args, "O", &wcs))
	return NULL;

    status = celset (&(wcs->params.cel));

    if (status)
	return Py_BuildValue ("s", cel_errmsg[status]);

    Py_RETURN_NONE;
}


/* vtable */

static PyMethodDef methods[] = {

    /* hio */

#define DEF(name, signature) { #name, py_##name, METH_VARARGS, #name " " signature }

    DEF(hopen, "(str name, str status) => int tno"),
    DEF(hflush, "(int tno) => void"),
    DEF(habort, "(void) => void"),
    DEF(hrm, "(int tno) => void"),
    DEF(hclose, "(int tno) => void"),
    DEF(hdelete, "(int tno, str itemname) => void"),
    DEF(haccess, "(int tno, str itemname, str status) => int itno"),
    DEF(hmode, "(int tno) => str mode"),
    DEF(hexists, "(int tno, str itemname) => int retval"),
    DEF(hdaccess, "(int ihandle) => void"),
    DEF(hsize, "(int ihandle) => long retval"),
    DEF(hio_generic, "(int iswrite, int ihandle, ndarray buf, long offset, "
	"long nbytes) => void"),

    /* headio */

    DEF(hisopen, "(int tno, str status) => void"),
    DEF(hiswrite, "(int tno, str text) => void"),
    DEF(hisclose, "(int tno) => void"),
    DEF(wrhd_generic, "(int tno, str itemname, object value) => void"),
    DEF(rdhd_generic, "(int tno, str itemname) => obj value"),
    DEF(hdcopy, "(int tin, int tout, str itemname) => void"),
    DEF(hdprsnt, "(int tno, str itemname) => int retval"),
    DEF(hdprobe, "(int tno, str itemname) => (str descr, str type, int n)"),

    /* dio */

    /* uvio */

    DEF(uvopen, "(str name, str status) => int tno"),
    DEF(uvclose, "(int tno) => void"),
    DEF(uvflush, "(int tno) => void"),
    DEF(uvnext, "(int tno) => void"),
    DEF(uvrewind, "(int tno) => void"),
    DEF(uvcopyvr, "(int tno, int tout) => void"),
    DEF(uvupdate,  "(int tno) => int retval"),
    DEF(uvvarini, "(int tno) => int vhan"),
    DEF(uvvarset, "(int vhan, str var) => void"),
    DEF(uvvarcpy, "(int vhan, int tout) => void"),
    DEF(uvvarupd, "(int vhan) => int retval"),
    DEF(uvgetvra, "(int tno, str var) => str retval"),
    DEF(uvgetvri, "(int tno, str var, int n) => (tuple of n int32 values)"),
    DEF(uvgetvrj, "(int tno, str var, int n) => (tuple of n int16 values)"),
    DEF(uvgetvrr, "(int tno, str var, int n) => (tuple of n float values)"),
    DEF(uvgetvrd, "(int tno, str var, int n) => (tuple of n double values)"),
    DEF(uvgetvrc, "(int tno, str var, int n) => (tuple of n complex values)"),
    DEF(uvrdvr_generic, "(int tno, str var) => obj value"),
    DEF(uvprobvr, "(int vhan, str var) => (char type, int length, int updated)"),
    DEF(uvtrack, "(int tno, str name, str switches) => void"),
    DEF(uvscan, "(int tno, str var) => int retval"),
    DEF(uvread, "(int tno, double-ndarray preamble, float-ndarray data,\n"
	" int-ndarray flags, int n) => int retval"),
    DEF(uvwrite, "(int tno, double-ndarray preamble, float-ndarray data,\n"
	" int-ndarray flags, int n) => void"),
    DEF(uvselect, "(int tno, str object, double p1, double p2, int flag) => None"),
    DEF(uvset, "(int tno, str object, str type, int n, double p1,\n"
	" double p2, double p3) => void"),
    DEF(uvflgwr, "(int tno, int-ndarray flags) => void"),
    DEF(uvinfo, "(int tno, str object, double-ndarray data) => void"),
    DEF(uvchkshadow, "(int tno, double diameter_meters) => bool"),
    DEF(probe_uvchkshadow, "() => bool"),

    /* uvio macros */

    DEF(uvputvri, "(int tno, str name, int-ndarray value) => void"),
    DEF(uvputvrr, "(int tno, str name, float-ndarray value) => void"),
    DEF(uvputvrd, "(int tno, str name, double-ndarray value) => void"),
    DEF(uvputvra, "(int tno, str name, str value) => void"),

    /* xyio */

    DEF(xyopen, "(str path, str mode, int naxis, int-ndarray axes) => int tno"),
    DEF(xyclose, "(int tno) => void"),
    DEF(xyflush, "(int tno) => void"),
    DEF(xyread, "(int tno, int index, float-ndarray data) => void"),
    DEF(xywrite, "(int tno, int index, float-ndarray data) => void"),
    DEF(xyflgrd, "(int tno, int index, int-ndarray flags) => void"),
    DEF(xyflgwr, "(int tno, int index, int-ndarray flags) => void"),
    DEF(xysetpl, "(int tno, int naxis, int-ndarray axes) => void"),

    /* maskio */

    DEF(mkopen, "(int tno, str name, str status) => int handle"),
    DEF(mkclose, "(int handle) => void"),
    DEF(mkread, "(int handle, int mode, int-ndarray flags, int offset, int n) => int nread"),
    DEF(mkwrite, "(int handle, int mode, int-ndarray flags, int offset, int n) => void"),
    DEF(mkflush, "(int handle) => void"),

    /* xyzio */

    DEF(xyzopen, "(str path, str mode, int naxis, int-ndarray axlen) => (int tno, int naxis)"),
    DEF(xyzclose, "(int tno) => void"),
    DEF(xyzflush, "(int tno) => void"),
    DEF(xyzsetup, "(int tno, str subcube, int-ndarray blc, int-ndarray trc) => "
	"(int-ndarray viraxlen, int-ndarray vircubesize)"),
    DEF(xyzs2c, "(int tno, int subcubenr, int-ndarray coords) => void"),
    DEF(xyzc2s, "(int tno, int-ndarray coords) => int subcubenr"),
    DEF(xyzread, "(int tno, int-ndarray coords, float-ndarray data, int-ndarray mask) => "
	"int ndata"),
    DEF(xyzpixrd, "(int tno, int pixnum) => (float data, int mask)"),
    DEF(xyzprfrd, "(int tno, int profnum, float-ndarray data, int-ndarray mask) => "
	"int ndata"),
    DEF(xyzwrite, "(int tno, int-ndarray coords, float-ndarray data, int-ndarray mask, "
	"int ndata) => void"),
    DEF(xyzprfwr, "(int tno, int profnum, float-ndarray data, int-ndarray mask, "
	"int ndata) => void"),

    /* scrio */

    /* key */

    DEF(keyinit, "(str task) => void"),
    DEF(keyput, "(str task, str string) => void"),
    DEF(keyini, "(list argv) => void"),
    DEF(keyfin, "(void) => void"),
    DEF(keyprsnt, "(str keyword) => int retval"),
    DEF(keya, "(str keyword, str default) => str value [for words]"),
    DEF(keyf, "(str keyword, str default) => str value [for filenames]"),
    DEF(keyd, "(str keyword, double default) => double value"),
    DEF(keyr, "(str keyword, float default) => float value"),
    DEF(keyi, "(str keyword, int default) => int value"),
    DEF(keyl, "(str keyword, int default) => int value [for booleans]"),
    DEF(mkeyd, "(str keyword, int nmax) => (tuple of double values)"),
    DEF(mkeyr, "(str keyword, int nmax) => (tuple of float values)"),
    DEF(mkeyi, "(str keyword, int nmax) => (tuple of int values)"),

    /* mir */

    /* interface - not needed, just c <-> fortran helpers */

    /* wcs */

    DEF(mirwcs_set_celoffset, "(_Wcsprm params, int value) => void"),
    DEF(mirwcs_set_celphitheta, "(_Wcsprm params, double phi0, double theta0) => void"),
    DEF(mirwcs_set_celref, "(_Wcsprm params, double lng0, double lat0) => void"),
    DEF(mirwcs_set_prjcode, "(_Wcsprm params, str code) => void"),
    DEF(mirwcs_set_prjpv, "(_Wcsprm params, ind index, double value) => void"),
    DEF(mirwcs_celset, "(_Wcsprm params) => error-string or None"),

    /* Done. Sentinel. */

    {NULL, NULL, 0, NULL}
};

/* finally ...
 * This PyMODINIT_FUNC is copied from the Python 2.3 pyport.h, which
 * defines portability macros. Python 2.2 does not have this macro.
 * Ideally, we should also include a "__declspec(dllexport)" item
 * on Windows machines, but the check for that will be complicated.
 */

#ifndef PyMODINIT_FUNC
#  if defined(__cplusplus)
#    define PyMODINIT_FUNC extern "C" void
#  else
#    define PyMODINIT_FUNC void
#  endif
#endif

PyMODINIT_FUNC
init_miriad_c (void)
{
    PyObject *mod, *dict;

    mts_setup ("mirtask._miriad_c.MiriadError");

    if (PyErr_Occurred ()) {
	PyErr_SetString (PyExc_ImportError,
			 "Can't initialize module _miriad_c: failed to import numpy");
	return;
    }

    mod = Py_InitModule("_miriad_c", methods);
    dict = PyModule_GetDict (mod);
    PyDict_SetItemString (dict, "MiriadError", mts_exc_miriad_err);
}
