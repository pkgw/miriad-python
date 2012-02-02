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

#define __MIR_TASK_SUPPORT_C
#include "mirtasksupport.h"

#include "miriad.h"

#define BUFSZ 512

PyObject *mts_exc_miriad_err;
jmp_buf mts_bug_recover;

static char bug_msg[BUFSZ];

static void
bug_handler (char sev, const char *msg)
{
    if (sev == 'f') {
	strcpy (bug_msg, msg);
	longjmp (mts_bug_recover, 1);
    } else {
#if PY_MINOR_VERSION > 4
	PyErr_WarnEx (PyExc_UserWarning, msg, 1);
#else
	PyErr_Warn (PyExc_UserWarning, msg);
#endif
	if (PyErr_Occurred () != NULL)
	    longjmp (mts_bug_recover, 1);
    }
}

void
mts_set_bug (void)
{
    if (PyErr_Occurred () == NULL)
	/* The exception may have been set before (if the warning was
	 * promoted to an error) */
	PyErr_SetString (mts_exc_miriad_err, bug_msg);
}

void
mts_setup (char *classname)
{
    mts_exc_miriad_err = PyErr_NewException (classname, NULL, NULL);
    bughandler_c (bug_handler);

    import_array ();
}

