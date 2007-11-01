#include <string.h> /* strerror */

#include "mirtasksupport.h"

#include "hio.h"
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
    char *keyword;

    if (!PyArg_ParseTuple (args, "is", &tno, &keyword))
	return NULL;

    MTS_CHECK_BUG;
    hdelete_c (tno, keyword, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}

static PyObject *
py_haccess (PyObject *self, PyObject *args)
{
    int tno, itno, iostat;
    char *keyword, *status;

    if (!PyArg_ParseTuple (args, "iss", &tno, &keyword, &status))
	return NULL;

    MTS_CHECK_BUG;
    haccess_c (tno, &itno, keyword, status, &iostat);
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
    char *keyword;

    if (!PyArg_ParseTuple (args, "is", &tno, &keyword))
	return NULL;

    MTS_CHECK_BUG;
    ret = hexists_c (tno, keyword);

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

/* skip: hio, since wrapped by hread/hwrite[bijlrdc] */

static PyObject *
py_hseek (PyObject *self, PyObject *args)
{
    int ihandle;
    long offset;

    if (!PyArg_ParseTuple (args, "il", &ihandle, &offset))
	return NULL;

    MTS_CHECK_BUG;
    hseek_c (ihandle, (off_t) offset);

    Py_RETURN_NONE;
}

static PyObject *
py_htell (PyObject *self, PyObject *args)
{
    int ihandle;
    off_t retval;

    if (!PyArg_ParseTuple (args, "i", &ihandle))
	return NULL;

    MTS_CHECK_BUG;
    retval = htell_c (ihandle);

    return Py_BuildValue ("l", (long) retval);
}

static PyObject *
py_hreada (PyObject *self, PyObject *args)
{
    int ihandle, iostat;
    char line[BUFSZ];

    if (!PyArg_ParseTuple (args, "i", &ihandle))
	return NULL;

    MTS_CHECK_BUG;
    hreada_c (ihandle, line, BUFSZ-1, &iostat);
    CHECK_IOSTAT(iostat);

    return Py_BuildValue ("s", line);
}

static PyObject *
py_hwritea (PyObject *self, PyObject *args)
{
    int ihandle, iostat;
    char *line;
    long length;

    if (!PyArg_ParseTuple (args, "isl", &ihandle, &line, &length))
	return NULL;

    MTS_CHECK_BUG;
    hwritea_c (ihandle, line, (size_t) length, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}

/* hio macros */

enum hio_dtype { HD_INTEGER, HD_FLOAT, HD_COMPLEX };

static PyObject *
hio_generic (PyObject *self, PyObject *args, int dowrite, int type, 
	     enum hio_dtype dtype, size_t objsize)
{
    int item, iostat, typeok = 0;
    long offset, length;
    PyObject *buf;

    if (!PyArg_ParseTuple (args, "iO!ll", &item, &PyArray_Type, &buf,
			   &offset, &length))
	return NULL;

    /* verify buffer */

    switch (dtype) {
    case HD_INTEGER:
	typeok = PyArray_ISINTEGER (buf);
	break;
    case HD_FLOAT:
	typeok = PyArray_ISFLOAT (buf);
	break;
    case HD_COMPLEX:
	typeok = PyArray_ISCOMPLEX (buf);
	break;
    }

    if (!typeok) {
	PyErr_SetString (PyExc_TypeError, "buf ndarray is of wrong type");
	return NULL;
    }

    if (PyArray_ITEMSIZE (buf) != objsize) {
	PyErr_SetString (PyExc_TypeError, "buf ndarray has bad itemsize");
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (buf)) {
	PyErr_SetString (PyExc_TypeError, "buf must be contiguous ndarray");
	return NULL;
    }

    /* do it */

    MTS_CHECK_BUG;
    hio_c (item, dowrite, type, PyArray_DATA (buf), (off_t) offset, 
	   (size_t) length, &iostat);
    CHECK_IOSTAT(iostat);

    Py_RETURN_NONE;
}

#define MAKE_HIO(ident, mtype, dtype, size) \
static PyObject *py_hread##ident (PyObject *self, PyObject *args) \
{ \
    return hio_generic (self, args, FALSE, mtype, dtype, size); \
} \
static PyObject *py_hwrite##ident (PyObject *self, PyObject *args) \
{ \
    return hio_generic (self, args, TRUE, mtype, dtype, size); \
}

MAKE_HIO(b, H_BYTE, HD_INTEGER, 1)
MAKE_HIO(i, H_INT, HD_INTEGER, sizeof (int))
MAKE_HIO(j, H_INT2, HD_INTEGER, 2)
MAKE_HIO(l, H_INT8, HD_INTEGER, 8)
MAKE_HIO(r, H_REAL, HD_FLOAT, sizeof (float))
MAKE_HIO(d, H_DBLE, HD_FLOAT, sizeof (double))
MAKE_HIO(c, H_CMPLX, HD_COMPLEX, 2 * sizeof (float))

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

/* skip hisread */

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

/* skip wrhd{r,d,i,c,a} */

static PyObject *
py_rdhdr (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    float value;
    double defval;
    
    if (!PyArg_ParseTuple (args, "isd", &tno, &keyword, &defval))
	return NULL;

    MTS_CHECK_BUG;
    rdhdr_c (tno, keyword, &value, defval);

    return Py_BuildValue ("f", value);
}

static PyObject *
py_rdhdi (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    int value, defval;
    
    if (!PyArg_ParseTuple (args, "isi", &tno, &keyword, &defval))
	return NULL;

    MTS_CHECK_BUG;
    rdhdi_c (tno, keyword, &value, defval);

    return Py_BuildValue ("i", value);
}

static PyObject *
py_rdhdl (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    int8 value, defval8;
    int defval;

    if (!PyArg_ParseTuple (args, "isi", &tno, &keyword, &defval))
	return NULL;

    if (defval)
	defval8 = 1;
    else
	defval8 = 0;

    MTS_CHECK_BUG;
    rdhdl_c (tno, keyword, &value, defval8);

    return Py_BuildValue ("i", (int) value);
}

static PyObject *
py_rdhdd (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    double value, defval;
    
    if (!PyArg_ParseTuple (args, "isd", &tno, &keyword, &defval))
	return NULL;

    MTS_CHECK_BUG;
    rdhdd_c (tno, keyword, &value, defval);

    return Py_BuildValue ("d", value);
}

static PyObject *
py_rdhdc (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    float value[2], defval[2];
    
    if (!PyArg_ParseTuple (args, "is(ff)", &tno, &keyword, defval,
			   &(defval[1])))
	return NULL;

    MTS_CHECK_BUG;
    rdhdc_c (tno, keyword, value, defval);

    return Py_BuildValue ("(ff)", value[0], value[1]);
}

static PyObject *
py_rdhda (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword, *defval;
    char value[BUFSZ];
    
    if (!PyArg_ParseTuple (args, "iss", &tno, &keyword, &defval))
	return NULL;

    MTS_CHECK_BUG;
    rdhda_c (tno, keyword, value, defval, BUFSZ-1);

    return Py_BuildValue ("s", value);
}

static PyObject *
py_hdcopy (PyObject *self, PyObject *args)
{
    int tin, tout;
    char *keyword;

    if (!PyArg_ParseTuple (args, "iis", &tin, &tout, &keyword))
	return NULL;

    MTS_CHECK_BUG;
    hdcopy_c (tin, tout, keyword);

    Py_RETURN_NONE;
}

static PyObject *
py_hdprsnt (PyObject *self, PyObject *args)
{
    int tno, retval;
    char *keyword;

    if (!PyArg_ParseTuple (args, "is", &tno, &keyword))
	return NULL;

    MTS_CHECK_BUG;
    retval = hdprsnt_c (tno, keyword);

    return Py_BuildValue ("i", retval);
}

static PyObject *
py_hdprobe (PyObject *self, PyObject *args)
{
    int tno;
    char *keyword;
    char descr[BUFSZ], type[32];
    int n;

    if (!PyArg_ParseTuple (args, "is", &tno, &keyword))
	return NULL;

    MTS_CHECK_BUG;
    hdprobe_c (tno, keyword, descr, BUFSZ, type, &n);

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
    int tno, n, i;
    char *var;
    PyObject *retval;
    int *vals;

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (int) * n);
    uvgetvri_c (tno, var, vals, n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyInt_FromLong ((long) vals[i]));

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_uvgetvrr (PyObject *self, PyObject *args)
{
    int tno, n, i;
    char *var;
    PyObject *retval;
    float *vals;

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (float) * n);
    uvgetvrr_c (tno, var, vals, n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyFloat_FromDouble ((double) vals[i]));

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_uvgetvrd (PyObject *self, PyObject *args)
{
    int tno, n, i;
    char *var;
    PyObject *retval;
    double *vals;

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (sizeof (double) * n);
    uvgetvrd_c (tno, var, vals, n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++)
	PyTuple_SetItem (retval, i, PyFloat_FromDouble (vals[i]));

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_uvgetvrc (PyObject *self, PyObject *args)
{
    int tno, n, i;
    char *var;
    PyObject *retval;
    double *vals;

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &n))
	return NULL;

    MTS_CHECK_BUG;

    vals = PyMem_Malloc (2 * sizeof (float) * n);
    uvgetvrc_c (tno, var, vals, n);

    retval = PyTuple_New (n);

    for (i = 0; i < n; i++) {
	double real = (double) vals[2*i];
	double imag = (double) vals[2*i+1];
	PyTuple_SetItem (retval, i, PyComplex_FromDoubles (real, imag));
    }

    PyMem_Free (vals);

    return retval;
}

static PyObject *
py_uvrdvra (PyObject *self, PyObject *args)
{
    int tno;
    char *var, *dflt, value[BUFSZ];

    if (!PyArg_ParseTuple (args, "iss", &tno, &var, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    uvrdvra_c (tno, var, value, dflt, BUFSZ);

    return Py_BuildValue ("s", value);
}

static PyObject *
py_uvrdvri (PyObject *self, PyObject *args)
{
    int tno;
    char *var;
    int val, dflt;

    if (!PyArg_ParseTuple (args, "isi", &tno, &var, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    uvrdvri_c (tno, var, &val, &dflt);

    return Py_BuildValue ("i", val);
}

static PyObject *
py_uvrdvrr (PyObject *self, PyObject *args)
{
    int tno;
    char *var;
    float val, dflt;

    if (!PyArg_ParseTuple (args, "isf", &tno, &var, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    uvrdvrr_c (tno, var, &val, &dflt);

    return Py_BuildValue ("f", val);
}

static PyObject *
py_uvrdvrd (PyObject *self, PyObject *args)
{
    int tno;
    char *var;
    double val, dflt;

    if (!PyArg_ParseTuple (args, "isd", &tno, &var, &dflt))
	return NULL;

    MTS_CHECK_BUG;
    uvrdvrd_c (tno, var, &val, &dflt);

    return Py_BuildValue ("d", val);
}

static PyObject *
py_uvrdvrc (PyObject *self, PyObject *args)
{
    int tno;
    char *var;
    float val[2], dflt[2];

    if (!PyArg_ParseTuple (args, "is(ff)", &tno, &var, &dflt[0], &dflt[1]))
	return NULL;

    MTS_CHECK_BUG;
    uvrdvrd_c (tno, var, val, dflt);

    return Py_BuildValue ("ff", val[0], val[1]);
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
py_uvwrite (PyObject *self, PyObject *args)
{
    int tno, n, size;
    PyObject *preamble, *data, *flags;

    if (!PyArg_ParseTuple (args, "iO!O!O!i", &tno, &PyArray_Type, &preamble,
			   &PyArray_Type, &data, &PyArray_Type, &flags, &n))
	return NULL;

    /* verify preamble */

    if (!PyArray_ISFLOAT (preamble)) {
	PyErr_SetString (PyExc_TypeError, "preamble must be float ndarray");
	return NULL;
    }

    if (PyArray_ITEMSIZE (preamble) != NPY_SIZEOF_DOUBLE) {
	PyErr_SetString (PyExc_TypeError, "preamble must be double-sized ndarray");
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (preamble)) {
	PyErr_SetString (PyExc_TypeError, "preamble must be contiguous ndarray");
	return NULL;
    }

    /* data */

    if (!PyArray_ISCOMPLEX (data)) {
	PyErr_SetString (PyExc_TypeError, "data must be complex ndarray");
	return NULL;
    }

    if (PyArray_ITEMSIZE (data) != 2*NPY_SIZEOF_FLOAT) {
	PyErr_SetString (PyExc_TypeError, "data must be plain-complex-sized ndarray");
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (data)) {
	PyErr_SetString (PyExc_TypeError, "data must be contiguous ndarray");
	return NULL;
    }

    /* flags */

    if (!PyArray_ISINTEGER (flags)) {
	PyErr_SetString (PyExc_TypeError, "flags must be integer ndarray");
	return NULL;
    }

    if (PyArray_ITEMSIZE (flags) != NPY_SIZEOF_INT) {
	PyErr_SetString (PyExc_TypeError, "flags must be plain-int-sized ndarray");
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (flags)) {
	PyErr_SetString (PyExc_TypeError, "flags must be contiguous ndarray");
	return NULL;
    }

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
/* skip uvsela_c, uvselect_c ... too lowlevel */

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

/* uvread, uvwread, uvflgwr, uvwflgwr skipped: all too lowlevel */
/* uvinfo: too hard */

/* XXX uvio incomplete! .... */

/* uvio macros */

static PyObject *
py_uvputvri (PyObject *self, PyObject *args)
{
    int tno;
    char *name;
    PyObject *value;

    if (!PyArg_ParseTuple (args, "isO!", &tno, &name, &PyArray_Type, &value))
	return NULL;

    if (!PyArray_ISINTEGER (value)) {
	PyErr_SetString (PyExc_TypeError, "value must be integer ndarray");
	return NULL;
    }

    if (PyArray_ITEMSIZE (value) != NPY_SIZEOF_INT) {
	PyErr_Format (PyExc_TypeError, "value must be plain-int-sized ndarray "
		      "(want %d, got %d)", NPY_SIZEOF_INT, PyArray_ITEMSIZE (value));
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (value)) {
	PyErr_SetString (PyExc_TypeError, "value must be contiguous ndarray");
	return NULL;
    }

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

    if (!PyArray_ISFLOAT (value)) {
	PyErr_SetString (PyExc_TypeError, "value must be float ndarray");
	return NULL;
    }

    if (PyArray_ITEMSIZE (value) != NPY_SIZEOF_FLOAT) {
	PyErr_SetString (PyExc_TypeError, "value must be plain-float-sized ndarray");
	return NULL;
    }

    if (!PyArray_ISCONTIGUOUS (value)) {
	PyErr_SetString (PyExc_TypeError, "value must be contiguous ndarray");
	return NULL;
    }

    MTS_CHECK_BUG;

    uvputvrr_c (tno, name, PyArray_DATA (value), PyArray_SIZE (value));

    Py_RETURN_NONE;
}

/* xyio */

/* maskio */

/* xyzio */

/* bug */

#if 0 /* Python code should never call these functions - just raise
       * an exception. So say I. */

static PyObject *
py_bugseverity (PyObject *self, PyObject *args)
{
    char retval;

    if (!PyArg_ParseTuple (args, ""))
	return NULL;

    MTS_CHECK_BUG; /*???*/
    retval = bugseverity_c ();
    
    return Py_BuildValue ("c", retval);
}

static PyObject *
py_bugmessage (PyObject *self, PyObject *args)
{
    char *retval;

    if (!PyArg_ParseTuple (args, ""))
	return NULL;

    MTS_CHECK_BUG; /*???*/
    retval = bugmessage_c ();
    
    return Py_BuildValue ("s", retval);
}

static PyObject *
py_buglabel (PyObject *self, PyObject *args)
{
    char *name;

    if (!PyArg_ParseTuple (args, "s", &name))
	return NULL;

    MTS_CHECK_BUG; /*???*/
    buglabel_c (name);
    
    Py_RETURN_NONE;
}

static PyObject *
py_bugno (PyObject *self, PyObject *args)
{
    char s;
    int n;

    if (!PyArg_ParseTuple (args, "ci", &s, &n))
	return NULL;

    MTS_CHECK_BUG; /*???*/
    bugno_c (s, n);
    
    Py_RETURN_NONE;
}

static PyObject *
py_bug (PyObject *self, PyObject *args)
{
    char s, *m;

    if (!PyArg_ParseTuple (args, "cs", &s, &m))
	return NULL;

    MTS_CHECK_BUG; /*???*/
    bug_c (s, m);
    
    Py_RETURN_NONE;
}
#endif

/* no bugv -- no point in dealing with that */

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

/* vtable */

static PyMethodDef uvio_methods[] = {

    /* hio */

#define DEF(name, signature) { #name, py_##name, METH_VARARGS, #name " " signature }

    DEF(hopen, "(str name, str status) => int tno"),
    DEF(hflush, "(int tno) => void"),
    DEF(habort, "(void) => void"),
    DEF(hrm, "(int tno) => void"),
    DEF(hclose, "(int tno) => void"),
    DEF(hdelete, "(int tno, str keyword) => void"),
    DEF(haccess, "(int tno, str keyword, str status) => int itno"),
    DEF(hmode, "(int tno) => str mode"),
    DEF(hexists, "(int tno, str keyword) => int retval"),
    DEF(hdaccess, "(int ihandle) => void"),
    DEF(hsize, "(int ihandle) => long retval"),
    DEF(hseek, "(int ihandle, long offset) => void"),
    DEF(htell, "(int ihandle) => long retval"),
    DEF(hreada, "(int ihandle) => str line"),
    DEF(hwritea, "(int ihandle, str line, long length) => void"),

    /* hio macros */

#define HIO_ENTRY(ident, buftype) \
  	DEF(hread##ident, "(int ihandle, " #buftype "-ndarray buf, long offset, " \
	  "long length) => void"), \
  	DEF(hwrite##ident, "(int ihandle, " #buftype "-ndarray buf, long offset, " \
	  "long length) => void")
    
    HIO_ENTRY(b, byte),
    HIO_ENTRY(i, int),
    HIO_ENTRY(j, int2),
    HIO_ENTRY(l, int8),
    HIO_ENTRY(r, float),
    HIO_ENTRY(d, double),
    HIO_ENTRY(c, complex),

    /* headio */

    DEF(hisopen, "(int tno, str status) => void"),
    DEF(hiswrite, "(int tno, str text) => void"),
    DEF(hisclose, "(int tno) => void"),
    DEF(rdhdr, "(int tno, str keyword, double defval) => float value"),
    DEF(rdhdi, "(int tno, str keyword, int defval) => int value"),
    DEF(rdhdl, "(int tno, str keyword, bool-as-int defval) => bool-as-int value"),
    DEF(rdhdd,  "(int tno, str keyword, double defval) => double value"),
    DEF(rdhdc, "(int tno, str keyword, (float,float) defval) => (float,float) value"),
    DEF(rdhda, "(int tno, str keyword, str defval) => str value"),
    DEF(hdcopy, "(int tin, int tout, str keyword) => void"),
    DEF(hdprsnt, "(int tno, str keyword) => int retval"),
    DEF(hdprobe, "(int tno, str keyword) => (str descr, str type, int n)"),

    /* XXX headio incomplete ... */

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
    DEF(uvgetvri, "(int tno, str var, int n) => (tuple of n int values)"),
    DEF(uvgetvrr, "(int tno, str var, int n) => (tuple of n float values)"),
    DEF(uvgetvrd, "(int tno, str var, int n) => (tuple of n double values)"),
    DEF(uvgetvrc, "(int tno, str var, int n) => (tuple of n complex values)"),
    DEF(uvrdvra, "(int tno, str var, str dflt) => str retval"),
    DEF(uvrdvri, "(int tno, str var, int dflt) => int retval"),
    DEF(uvrdvrr, "(int tno, str var, float dflt) => float retval"),
    DEF(uvrdvrd, "(int tno, str var, double dflt) => double retval"),
    DEF(uvrdvrc, "(int tno, str var, (float,float) dflt) => (float,float) retval"),
    DEF(uvprobvr, "(int vhan, str var) => (char type, int length, int updated)"),
    DEF(uvtrack, "(int tno, str name, str switches) => void"),
    DEF(uvscan, "(int tno, str var) => int retval"),
    DEF(uvwrite, "(int tno, double-ndarray preamble, float-ndarray data,\n"
	" int-ndarray flags, int n) => void"),
    DEF(uvset, "(int tno, str object, str type, int n, double p1,\n"
	" double p2, double p3) => void"),

    /* XXX uvio incomplete ... */

    /* uvio macros */

    DEF(uvputvri, "(int tno, str name, int-ndarray value) => void"),
    DEF(uvputvrr, "(int tno, str name, float-ndarray value) => void"),
	
    /* XXX uvio macros incomplete ... */

    /* xyio */

    /* maskio */

    /* xyzio */

    /* bug */

#if 0
    DEF(bugseverity, "(void) => char retval"),
    DEF(bugmessage, "(void) => str retval"),
    DEF(buglabel, "(str name) => void"),
    DEF(bugno, "(char s, int n) => void"),
    DEF(bug, "(char s, str m) => void"),
    /* no bugv -- no point */
#endif

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
#       if defined(__cplusplus)
#               define PyMODINIT_FUNC extern "C" void
#       else /* __cplusplus */
#               define PyMODINIT_FUNC void
#       endif /* __cplusplus */
#endif

PyMODINIT_FUNC
init_uvio (void)
{
    PyObject *mod, *dict;

    mts_setup ("_uvio.MiriadError");

    if (PyErr_Occurred ()) {
	PyErr_SetString (PyExc_ImportError, "Can't initialize module _uvio: failed to import numpy");
	return;
    }

    mod = Py_InitModule("_uvio", uvio_methods);
    dict = PyModule_GetDict (mod);
    PyDict_SetItemString (dict, "MiriadError", mts_exc_miriad_err);
}
