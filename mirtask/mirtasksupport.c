#define __MIR_TASK_SUPPORT_C
#include "mirtasksupport.h"

#include "hio.h"
#include "miriad.h"

#define BUFSZ 512

PyObject *mts_exc_miriad_err;
jmp_buf mts_bug_recover;

static char bug_msg[BUFSZ];

static void
bug_handler (void)
{
    char sev = bugseverity_c ();
    char *msg = bugmessage_c ();

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
    bugrecover_c (bug_handler);

    import_array ();
}

