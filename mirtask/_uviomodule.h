#ifndef _UVIO_MODULE_H
#define _UVIO_MODULE_H

#include <Python.h>

extern void py_uvio_set_bug (void);
extern jmp_buf py_uvio_bug_recover;

#define UVIO_CHECK_BUG if (setjmp (py_uvio_bug_recover)) { py_uvio_set_bug (); return NULL; }

#endif
