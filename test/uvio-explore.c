#include <stdio.h>
#include <string.h>
#include <unistd.h>
#include <stdlib.h>

#include "miriad.h"

/* uvopen: status is "old" (rw), "new" (create, write only),
 * or "append" (write only)
 */

#define MAXCHAN 4096

#define MAXCHAR 512

/* preamble is either 4 or 5 elements, depending on if W data is
 * recorded along with U and V. Elements are U, V, [W], time, baseline.
 *
 * U, V, W: appear to be kilo-lambdas
 * time: appears to be Julian date
 * Baseline number format: rounded to nearest integer. Seems to be 
 *  (num of ant 1) * K + (num of ant 2). K = 256 for ATA data. And for
 *  CARMA data. Require ant 1 < ant 2, and (ant1,ant2) > 0. See basant.for.
 */

#define PREAMBLE_4_U 0
#define PREAMBLE_4_V 1
#define PREAMBLE_4_T 2
#define PREAMBLE_4_BL 3

#define PREAMBLE_5_U 0
#define PREAMBLE_5_V 1
#define PREAMBLE_5_W 2
#define PREAMBLE_5_T 3
#define PREAMBLE_5_BL 4

/* uvread_c: Reads out nread channels of data.
 *
 * preamble: 4 of 5 doubles, described above
 * data: 2 * nread floats, real/imag pairs
 * flags: nread ints, each 1 or 0 for if the channel is good
 *   or bad
 *
 */

/* uvinfo_c: read metadata
 *
 * object: What to read:
 *  "velocity" -> [vel of channel in km/s] * nread
 *  "restfreq" -> ["rest freq" of channel in GHz] * nread 
 *  "frequency" -> ["rest frame freq" of channel in Ghz] * nread
 *  "sfreq" -> ["sky frequency" of chan in Ghz] * nchan
 *  "bandwidth" -> [BW of channel in GHz] * nread
 *  "visno" -> number of visibilities read from file
 *  "amprange" -> [amp sel code, range min, range max] where
 *    sel code is: -1 if data outside range was rejected
 *                 0 if no selection in effect
 *                 1 if data inside range was rejected
 *  "line" -> [type, n, start, width, step, "first window used"]
 *    where type is (1, 2, 3) <=> (channel, wide, velocity)
 *  "variance" -> "variance (based on system temp) of the first 
 *    channel", or 0 "if this cannot be determined".
 *
 */

/* low-level (?) variable tracking: 
 *
 * uvvarini_c: allocates a variable handle
 * uvvarset_c: set a handle to track a named variable. Names?
 * uvvarcpy_c: seems to copy a var from one data set to another
 * uvvarupd_c: unclear? returns boolean
 */

/* higher-level (?) variable tracking:
 *
 * One can see a list of variables names and types in the 'vartable' file
 * in a Miriad dataset.
 *
 * uvrdvr_c: get "first" value of a variable
 *  tno: UV file handle
 *  type: destination data type: H_BYTE, H_INT, H_REAL, H_DBLE, H_CMPLX
 *     (variables will be upcast between int/real/double)
 *  var: the name of the variable. Comes from ... ?
 *  data: value lands here; pointer type should agree with 'type'
 *  n: length of 'data'; only relevant for H_BYTE, which deals in byte
 *     arrays. It seems that these are assumed to be strings, but nul
 *     termination looks sloppy.
 *
 * uvrdvr{a,i,r,d,c}_c: wrap around the above. Only uvrdvra_c takes a 
 * len parameter.
 *
 * uvgetvr_c: get "current" value of a variable
 *  tno: UV file handle
 *  type: as uvrdvr_c
 *  var: as uvrdvr_c
 *  data: as uvrdvr_c
 *  n: number of elements expected. Must agree with what is actually 
 *    retrieved, except in the case of byte variables, in which case
 *    n must be strictly greater than the variable size.
 *
 * uvgetvr{a,i,r,d,c}_c: similar wrappers.
 *
 * uvprobvr_c: check for changes to a variable value and find the 
 * current variable length
 *
 * uvtrack_c: set how a variable is tracked. If 'u' in switches,
 * uvupdate returns TRUE if the variable is updated. If 'c' in
 * switches, copy the new variable value in uvcopyvr if the variable
 * has been updated. (uvupdate merely takes a tno and returns a bool.)
 *
 * uvscan_c: scan through file until the variable changes. Returns 0
 * of found something, -1 on EOF, "standard error number" otherwise.
 */

/* Selection. There must be a higher-level function to implement
 * selection like the keyword.
 *
 * uvsela_c: Apply string selection criteria
 *  object: what to filter on. Only "source" allowed
 *  string: the value to match
 *  datasel: true to include the data, false to discard it
 *
 * uvselect_c: Analogous for numerical values
 *
 */

int 
compare (const void *left, const void *right)
{
    int l, r;

    l = *((const int *) left);
    r = *((const int *) right);

    if (l < r) return -1;
    if (l == r) return 0;
    return 1;
}

int
main (int argc, char **argv)
{
    int handle, i;

    int nread;
    int nrec = 0;
    double preamble[5] = {-1, -1, -1, -1, -1};
    float data[2*MAXCHAN];
    int flags[MAXCHAN];

    char buf[MAXCHAR];
    int ivar, idef;
    float fvar, fdef;
    double dvar, ddef;
    float cvar[2], cdef[2];
    
    int blcodes[32000], lastbl, nprint;

    if (argc != 2) {
	fprintf (stderr, "Usage: %s [vis data]\n", argv[0]);
	return 1;
    }
    
    uvopen_c (&handle, argv[1], "old");

    uvread_c (handle, preamble, data, flags, MAXCHAN, &nread);

    while (nread > 0) {
	nrec += 1;

	if (nrec % 100 == 0) {
	    printf ("%06d: %lf, %lf, %lf, %lf, %lf : %d\n", nrec,
		    preamble[0], preamble[1], preamble[2], preamble[3],
		    preamble[4], nread);
	    printf ("        %lf, %lf ; %lf, %lf ; %lf, %lf ; %lf\n", 
		    data[0], data[1], data[1023], data[1024],
		    data[1547], data[1548], data[2049]);
	    printf ("        %x, %x ; %x, %x ; %x, %x ; %x\n", 
		    flags[0], flags[1], flags[1023], flags[1024],
		    flags[2047], flags[2048], flags[2049]);
	}

	if (nrec < 32000)
	    blcodes[nrec-1] = (int) preamble[3];
	
	uvread_c (handle, preamble, data, flags, MAXCHAN, &nread);
    }

    printf ("Read %d records.\n", nrec);

    printf ("\n");

    qsort (blcodes, nrec > 32000 ? 32000 : nrec, sizeof (int), compare);
    printf ("Beginning of sorted baseline codes:\n");
    lastbl = -1;
    nprint = 0;
    for (i = 0; i < nrec && nprint < 50; i++) {
	if (blcodes[i] == lastbl)
	    continue;

	printf (" %d", blcodes[i]);
	lastbl = blcodes[i];
	nprint += 1;
    }
    printf ("\n\n");
    
    memset (buf, '\0', MAXCHAR);
    uvrdvra_c (handle, "operator", buf, "", MAXCHAR-1);
    printf ("Operator: %s\n", buf);

    idef = -1;
    uvrdvri_c (handle, "nchan", &ivar, &idef);
    printf ("Number of channels: %d\n", ivar);

    fdef = -1.;
    uvrdvrr_c (handle, "inttime", &fvar, &fdef);
    printf ("Integration time: %f\n", fvar);

    ddef = -1.;
    uvrdvrd_c (handle, "ra", &dvar, &ddef);
    printf ("ra: %lf\n", dvar);

    ddef = -1.;
    uvrdvrd_c (handle, "obsra", &dvar, &ddef);
    printf ("obsra: %lf\n", dvar);

    cdef[0] = -1; cdef[1] = -1;
    uvrdvrc_c (handle, "wcorr", cvar, cdef);
    printf ("wcorr: (%f, %f)\n", cvar[0], cvar[1]);

    uvclose_c (handle);

    return 0;
}
