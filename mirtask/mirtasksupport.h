#ifndef _MIR_TASK_SUPPORT_H
#define _MIR_TASK_SUPPORT_H

#include <Python.h>

#define PY_ARRAY_UNIQUE_SYMBOL py_uvio_array_api
#ifndef __MIR_TASK_SUPPORT_C
#define NO_IMPORT_ARRAY
#define import_array() do {} while (0)
#endif
#include "numpy/arrayobject.h"

#include "fortranobject.h"

extern jmp_buf mts_bug_recover;
extern PyObject *mts_exc_miriad_err;

extern void mts_set_bug (void);
extern void mts_setup (char *classname);

#define MTS_CHECK_BUG if (setjmp (mts_bug_recover)) { mts_set_bug (); return NULL; }


#endif
