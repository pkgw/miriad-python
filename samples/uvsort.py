#!/usr/bin/python

import sys
import miriad
from mirtask import keys, uvdat, lowlevel as ll
import numpy as N

MAXCHAN = 4096
CHUNKSIZE = 32768

print 'UvSort: python bastardization'

keys.doUvdat ('bxdlr3', True)
keys.keyword ('out', 'f', ' ')
args = keys.process ()

if args.out == ' ':
    print >>sys.stderr, 'Output file must be specified'
    sys.exit (1)

print 'First pass: reading timestamps and sorting'

nrec = 0
sortedtime = N.zeros (CHUNKSIZE, dtype=N.double)
npertime = N.zeros (CHUNKSIZE, dtype=N.int)

ds = uvdat.singleInputSet ()

for (preamble, data, flags, nread) in uvdat.readData ():
    nrec += 1

    if nrec >= sortedtime.size: sortedtime.resize (sortedtime.size + CHUNKSIZE)

    sortedtime[nrec - 1] = preamble[3]

del ds

sortedtime.resize (nrec)
sortedtime.sort ()

nuniq = 0
Tprev = 0.0

for i in xrange (0, nrec):
    if sortedtime[i] != Tprev:
        Tprev = sortedtime[i]
        sortedtime[nuniq] = Tprev
        nuniq += 1

    npertime[nuniq - 1] += 1

print '% 12d unique UV timestamps, %d UV records' % (nuniq, nrec)
print 'Second pass: copying data'

args = keys.process ()

din = uvdat.singleInputSet ()
ltype = uvdat.getLinetype ()
din.initVarsAsInput (ltype)

tracker = din.makeVarTracker ()
tracker.track ('dra', 'ddec', 'source', 'on')

dout = miriad.VisData (args.out).open ('w')
dout.setPreambleType ('uvw', 'time', 'baseline')
dout.initVarsAsOutput (din, ltype)

din.copyHeader (dout, 'history')
dout.openHistory ()
dout.writeHistory ('UVSORT: python bastardization')
dout.logInvocation ('UVSORT')
dout.closeHistory ()

isrec = 0
written = 0
nrewind = 0
nextprog = 0.1

npol = N.zeros (1, dtype=N.int32)
pol = N.zeros (1, dtype=N.int32)
jyperk = N.zeros (1, dtype=N.float32)

while isrec < nuniq:
    futureskipped = False
    nthistime = 0
    irec = 0

    nread = ll.uvdatrd (preamble, data, flags, MAXCHAN)

    while nread > 0 and isrec < nuniq:
        irec += 1
        
        if preamble[3] > sortedtime[isrec]:
            futureskipped = True
        elif preamble[3] == sortedtime[isrec]:
            dout.writeVarInt ('npol', uvdat.getNPol ())
            dout.writeVarInt ('pol', uvdat.getPol ())
            dout.writeVarFloat ('jyperk', uvdat.getJyPerK ())
            din.copyLineVars (dout)
            dout.write (preamble, data, flags, nread)

            written += 1
            nthistime += 1

            if not futureskipped and nthistime == npertime[isrec]:
                isrec += 1
                nthistime = 0

            if 1. * written / nrec >= nextprog:
                print '% 12d of % 6d UV records written' % (written, nrec)
                nextprog += 0.1

        nread = ll.uvdatrd (preamble, data, flags, MAXCHAN)
    
    if nthistime != npertime[isrec]:
        raise MiriadError ('Algorithm bug (1) (nthis %d, nper[%d] %d)' % \
                       (nthistime, isrec, npertime[isrec]))

    nrewind += 1
    din.rewind ()
    isrec += 1

if isrec < nuniq: raise MiriadError ('Algorithm bug (2)')
if written != nrec: raise MiriadError ('Algorithm bug (3)')

print 'Done sorting. Had to rewind %d times.' % nrewind
del din, dout

