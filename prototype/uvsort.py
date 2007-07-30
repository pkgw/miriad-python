#!/usr/bin/python

import pymirread
import numpy as N
m = pymirread._mirgood
u = pymirread._uvio

MAXCHAN = 4096
CHUNKSIZE = 32768

sortedtime = N.zeros (CHUNKSIZE, dtype=N.double)
npertime = N.zeros (CHUNKSIZE, dtype=N.int)

m.output ('UvSort: python bastardization')
# keys initialized by pymirread.__init__.
uvflags = 'bxdlr3'
m.uvdatinp ('vis', uvflags)

out = u.keya ('out', ' ')
u.keyfin ()

if out == ' ':
    pymirread.bug ('f', 'Output file must be specified')

nrec = 0

m.output ('First pass: reading timestamps and sorting')

(status, tin) = m.uvdatopn ()
if not status:
    pymirread.bug ('f', 'Cannot open input file')

preamble = N.zeros (5, dtype=N.double)
data = N.zeros (MAXCHAN, dtype=N.complex64)
flags = N.zeros (MAXCHAN, dtype=N.int32)

nread = m.uvdatrd (preamble, data, flags, MAXCHAN)

while nread > 0:
    nrec += 1

    if nrec >= sortedtime.size: sortedtime.resize (sortedtime.size + CHUNKSIZE)

    sortedtime[nrec - 1] = preamble[3]
    nread = m.uvdatrd (preamble, data, flags, MAXCHAN)

m.uvdatcls ()
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

m.output ('% 12d unique UV timestamps, %d UV records' % (nuniq, nrec))
m.output ('Second pass: copying data')

pymirread.initKeys ()
m.uvdatinp ('vis', uvflags)
out = u.keya ('out', ' ')
u.keyfin ()

(status, tin) = m.uvdatopn ()
if not status:
    pymirread.bug ('f', 'Cannot open input file')

ltype = pymirread.uvdatgta ('ltype')
m.varinit (tin, ltype)
vupd = u.uvvarini (tin)
u.uvvarset (vupd, 'dra')
u.uvvarset (vupd, 'ddec')
u.uvvarset (vupd, 'source')
u.uvvarset (vupd, 'on')

tout = u.uvopen (out, 'new')
u.uvset (tout, 'preamble', 'uvw/time/baseline', 0, 0., 0., 0.,)
u.hdcopy (tin, tout, 'history')
u.hisopen (tout, 'append')
u.hiswrite (tout, 'UVSORT: python bastardization')
pymirread.hisinput (tout, 'UVSORT')
u.hisclose (tout)

m.varonit (tin, tout, ltype)

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

    nread = m.uvdatrd (preamble, data, flags, MAXCHAN)

    while nread > 0 and isrec < nuniq:
        irec += 1
        
        if preamble[3] > sortedtime[isrec]:
            futureskipped = True
        elif preamble[3] == sortedtime[isrec]:
            m.uvdatgti ('npol', npol)
            u.uvputvri (tout, 'npol', npol)
            m.uvdatgti ('pol', pol)
            u.uvputvri (tout, 'pol', pol)
            m.varcopy (tin, tout)
            m.uvdatgtr ('jyperk', jyperk)
            u.uvputvrr (tout, 'jyperk', jyperk)
            u.uvwrite (tout, preamble, data, flags, nread)

            written += 1
            nthistime += 1

            if not futureskipped and nthistime == npertime[isrec]:
                isrec += 1
                nthistime = 0

            if 1. * written / nrec >= nextprog:
                print '% 12d of % 6d UV records written' % (written, nrec)
                nextprog += 0.1

        nread = m.uvdatrd (preamble, data, flags, MAXCHAN)
    
    if nthistime != npertime[isrec]:
        pymirread.bug ('f', 'Algorithm bug (1) (nthis %d, nper[%d] %d)' % \
                       (nthistime, isrec, npertime[isrec]))

    nrewind += 1
    u.uvrewind (tin)
    isrec += 1

if isrec < nuniq: pymirread.bug ('f', 'Algorithm bug (2)')
if written != nrec:pymirread.bug ('f', 'Algorithm bug (3)')

print 'Done sorting. Had to rewind %d times.' % nrewind
m.uvdatcls ()
u.uvclose (tout)
