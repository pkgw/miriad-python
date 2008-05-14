#! /usr/bin/env python

"""A reimplentation of UVCAL with the FXCAL option. FXCAL
suffers from two failings:

* It is sensitive to the order of the data within a file:
if the (p, q) baseline appears before (p, p) or (q, q), the
data will be lost, even if the data is present with the
correct timestamp.

* It writes zeros instead of flagging invalid data.

This version avoids those issues."""

import sys
import miriad
from mirtask import uvdat, keys, util
import numpy as N

banner = 'FXCAL: reimplementation of uvcal options=fxcal'
print banner

keys.keyword ('out', 'f', ' ')
keys.doUvdat ('ds3', False)
opts = keys.process ()

if opts.out == ' ':
    print >>sys.stderr, 'Error: must give an output filename'
    sys.exit (1)

# Multifile UV copying algorithm copied from uvcat.for.

dOut = miriad.VisData (opts.out).open ('w')
dOut.setPreambleType ('uvw', 'time', 'baseline')

first = True
curFile = None
saveNPol = 0
polsVaried = False

windowVars = ['ischan', 'nschan', 'nspect', 'restfreq',
              'sdf', 'sfreq', 'systemp', 'xtsys', 'ytsys']

lastTime = None
autos = crosses = None

def dump (dOut, autos, crosses):
    for (pol, subtab) in autos.iteritems ():
        dOut.writeVarInt ('pol', pol)
                
        for (preamble, data, flags) in subtab.itervalues ():
            dOut.write (preamble, data, flags, flags.size)

    for (pol, subtab) in crosses.iteritems ():
        dOut.writeVarInt ('pol', pol)

        for (bl, (preamble, data, flags)) in subtab.iteritems ():
            if bl[0] not in autos[pol]: continue
            if bl[1] not in autos[pol]: continue

            (pa1, da1, fa1) = autos[pol][bl[0]]
            (pa2, da2, fa2) = autos[pol][bl[1]]

            fFinal = N.logical_and (flags, N.logical_and (fa1, fa2))
            
            scale = (da1 * da2)**-0.5
            scale[N.where (fFinal == 0)] = 0

            # the 0 above is just in case any values were zero.
            # the corrs are stored in 16 bits, so our dynamic range is
            # limited.

            dFinal = data * scale

            # Have to coerce this back to the desired type.
            fFinal = N.asarray (fFinal, dtype=N.int32)
            
            dOut.write (preamble, dFinal, fFinal, fFinal.size)

for dIn, preamble, data, flags, nread in uvdat.readAll ():
    anyChange = False
    
    if dIn is not curFile:
        # Started reading a new file (or the first file)
        corrType, corrLen, corrUpd = dIn.probeVar ('corr')

        if corrType != 'r' and corrType != 'j' and corrType != 'c':
            raise Exception ('No channels to copy')

        if first:
            # This is NOT a close approximation to uvcat.for
            # We don't use an 'init' var since we assume dochan=True.
            dOut.setCorrelationType (corrType)
        
        dIn.initVarsAsInput (' ') # what does ' ' signify?

        uvt = dIn.makeVarTracker ()
        uvt.track (*windowVars)

        tup = dIn.probeVar ('npol')
        doPol = tup is not None and (tup[0] == 'i')
        nPol = 0
        doneNPol = False
        curFile = dIn
        anyChange = True
        
    if first:
        # If very first file, copy the history entry.
        dIn.copyHeader (dOut, 'history')
        first = False

    if nPol == 0:
        nPol = uvdat.getNPol ()
        doneNPol = False

    if uvt.updated ():
        nAnts = dIn.getVarInt ('nants')

        tbl = {}
        
        dIn.probeVar ('nspect')
        nSpec = dIn.getVarInt ('nspect')
        tbl['nspect'] = ('i', nSpec)
        
        for v in ['nschan', 'ischan']:
            dIn.probeVar (v)
            tbl[v] = ('i', dIn.getVarInt (v, nSpec))

        for v in ['sdf', 'sfreq', 'restfreq']:
            dIn.probeVar (v)
            tbl[v] = ('d', dIn.getVarDouble (v, nSpec))

        for v in ['systemp', 'xtsys', 'ytsys', 'xyphase']:
            tup = dIn.probeVar (v)

            if tup is not None and tup[0] == 'r':
                tbl[v] = ('r', dIn.getVarFloat (v, tup[1]))

        for (name, (code, val)) in tbl.iteritems ():
            if code == 'i':
                dOut.writeVarInt (name, val)
            elif code == 'r':
                dOut.writeVarFloat (name, val)
            elif code == 'd':
                dOut.writeVarDouble (name, val)
            else:
                assert (False)

        anyChange = True

    flags = flags[0:nread]
    pol = uvdat.getPol ()

    if not flags.any (): continue # skip all-flagged records

    if not util.polarizationIsInten (pol):
        # We'd need to break cross-pols into single pol vals
        # to look up into the autos table ...
        continue
    
    time = preamble[3]
    bl = util.decodeBaseline (preamble[4])
    data = data[0:nread]

    if not doneNPol:
        if nPol != saveNPol:
            dOut.writeVarInt ('npol', nPol)
            polsVaried = saveNPol != 0
            saveNPol = nPol
        doneNPol = True

    dIn.copyLineVars (dOut)

    # Hey! We actually have some data processing to do!

    if time != lastTime:
        if autos is not None:
            # Dump out previous accumulation of data.
            dump (dOut, autos, crosses)
            
        # Reset accumulators
        autos = {}
        crosses = {}
    elif anyChange:
        raise Exception ('File params changed in middle of a dump!')
        
    # Accumulate current dump.
    
    if bl[0] == bl[1]:
        if pol not in autos: autos[pol] = {}
        autos[pol][bl[0]] = (preamble.copy (), data.copy (), flags.copy ())
    else:
        if pol not in crosses: crosses[pol] = {}
        crosses[pol][bl] = (preamble.copy (), data.copy (), flags.copy ())

    lastTime = time
        
    # I don't understand what this does ...
    nPol -= 1

dump (dOut, autos, crosses)

if not polsVaried:
    # wrhdi (dOut, saveNPol)
    pass

# All done. Write history entry and quit.

dOut.openHistory ()
dOut.writeHistory (banner)
dOut.logInvocation ('FXCAL')
dOut.closeHistory ()
dOut.close ()

sys.exit (0)

