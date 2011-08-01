/*
 * Copyright 2009, 2010, 2011 Peter Williams
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

/*
 * This file must be included before any system headers, because it
 * #includes Python.h, which imposes that restriction. See
 *
 * http://docs.python.org/c-api/intro.html#includes
 *
 */

#ifndef _MIR_TASK_SUPPORT_H
#define _MIR_TASK_SUPPORT_H

#include <Python.h>

#define PY_ARRAY_UNIQUE_SYMBOL py_mirtask_array_api
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
