#! /usr/bin/env python

import numpy as N
from mirtask import keys, util, uvdat
from uvutils import *

SECOND = 1.0 / 3600. / 24.

keys.keyword ('interval', 'd', 0.01)
keys.keyword ('cutoffs', 'd', None, 3)
keys.option ('rmshist')
keys.doUvdat ('dsl3x', True)

integData = {}
accData = {}

def cr (): return GrowingArray (N.double, 3)
allData = AccDict (cr, lambda ga, tup: ga.add (*tup))

seenants = set ()
seenpols = set ()

def flushInteg (time):
    global integData
    ants = sorted (seenants)

    for pol in seenpols:
        for i in xrange (0, len (ants)):
            ant3 = ants[i]
            for j in xrange (0, i):
                ant2 = ants[j]
                for k in xrange (0, j):
                    ant1 = ants[k]

                    flushOneInteg (time, pol, ant1, ant2, ant3)
    integData = {}

def flushOneInteg (time, pol, ant1, ant2, ant3):
    tup12 = integData.get (((ant1, ant2), pol))
    tup13 = integData.get (((ant1, ant3), pol))
    tup23 = integData.get (((ant2, ant3), pol))

    if tup12 is None or tup13 is None or tup23 is None:
        return

    (d12, f12, v12) =  tup12
    (d13, f13, v13) =  tup13
    (d23, f23, v23) =  tup23

    w = N.where (N.logical_and (f12, N.logical_and (f13, f23)))
    n = len (w[0])

    if n == 0: return
    
    c = (d12[w] * d23[w] * d13[w].conj ()).sum ()
    v = n * (v12 + v13 + v23)
    t = n * time
    
    accKey = (pol, ant1, ant2, ant3)
    if accKey not in accData:
        accData[accKey] = (t, n, c, v)
    else:
        (t0, n0, c0, v0) = accData[accKey]
        accData[accKey] = (t + t0, n + n0, c + c0, v + v0)
    
def flushAcc ():
    global accData
    ants = sorted (seenants)

    for pol in seenpols:
        for i in xrange (0, len (ants)):
            ant3 = ants[i]
            for j in xrange (0, i):
                ant2 = ants[j]
                for k in xrange (0, j):
                    ant1 = ants[k]

                    flushOneAcc (pol, ant1, ant2, ant3)
    accData = {}

def flushOneAcc (pol, ant1, ant2, ant3):
    key = (pol, ant1, ant2, ant3)
    tup = accData.get (key)
    if tup is None:
        return

    (time, n, c, v) = tup

    # note! not dividing by n since that doesn't affect phase.
    # Does affect amp though.
    ph = 180/N.pi * N.arctan2 (c.imag, c.real)

    #print pol, ant1, ant2, ant3, time/n, ph
    
    allData.accum (key, (time / n, ph, v / n))

# Prep args. Note our current args model can't support
# nocal-nopass-nopol options.

args = keys.process ()

interval = args.interval / 60. / 24.

if len (args.cutoffs) > 0:
    goodCutoff = args.cutoffs[0]
else:
    goodCutoff = 15.
if len (args.cutoffs) > 1:
    dubiousCutoff = args.cutoffs[1]
else:
    dubiousCutoff = 30.
if len (args.cutoffs) > 2:
    badCutoff = args.cutoffs[2]
else:
    badCutoff = 90.

print 'Using cutoffs: good < %lf deg, dubious > %lf deg, bad > %lf deg' \
      % (goodCutoff, dubiousCutoff, badCutoff)

# Let's go.

first = True
print 'Reading data ...'

for (inp, preamble, data, flags, nread) in uvdat.readAll ():
    data = data[0:nread].copy ()
    flags = flags[0:nread].copy ()

    time = preamble[3]
    bl = util.decodeBaseline (preamble[4])
    pol = uvdat.getPol ()
    var = uvdat.getVariance ()

    # Some first checks.
    
    if not util.polarizationIsInten (pol): continue
    if not flags.any (): continue
    
    seenpols.add (pol)
    seenants.add (bl[0])
    seenants.add (bl[1])
    
    if first:
        time0 = int (time - 0.5) + 0.5
        tmin = time - time0
        tmax = tmin
        tprev = tmin
        first = False

    t = time - time0

    if abs (t - tprev) > SECOND:
        flushInteg (tprev)
        tprev = t

    if (t - tmin) > interval or (tmax - t) > interval:
        flushAcc ()
        tmin = tmax = t

    # Store info for this vis
    
    tmin = min (tmin, t)
    tmax = max (tmax, t)
    integData[(bl, pol)] = (data, flags, var)

print ' ... Done.'

flushInteg (t)
flushAcc ()

blStats = {}
antStats = {}
shouldGood = set ()
maybeBad = set ()

def recordBL (pol, ant1, ant2, rms):
    key = (pol, ant1, ant2)
    sa = blStats.get (key)

    if sa is None:
        sa = StatsAccumulator ()
        blStats[key] = sa

    sa.add (rms)

def recordAnt (pol, ant1, rms):
    key = (pol, ant1)
    sa = antStats.get (key)
    
    if sa is None:
        sa = StatsAccumulator ()
        antStats[key] = sa

    sa.add (rms)

if args.rmshist:
    allrms = GrowingArray (N.double, 1)

for (key, ga) in allData.iteritems ():
    ga.doneAdding ()    
    (pol, ant1, ant2, ant3) = key
    phs = ga.col (1)
    rms = N.sqrt (N.mean (phs**2))

    if args.rmshist:
        allrms.add (rms)
    
    recordBL (pol, ant1, ant2, rms)
    recordBL (pol, ant1, ant3, rms)
    recordBL (pol, ant2, ant3, rms)
    recordAnt (pol, ant1, rms)
    recordAnt (pol, ant2, rms)
    recordAnt (pol, ant3, rms)

    if rms < goodCutoff:
        shouldGood.add ((ant1, ant2))
        shouldGood.add ((ant1, ant3))
        shouldGood.add ((ant2, ant3))
    elif rms > badCutoff:
        maybeBad.add ((ant1, ant2))
        maybeBad.add ((ant1, ant3))
        maybeBad.add ((ant2, ant3))

    if rms > dubiousCutoff:
        s = '%s-%d-%d-%d' % (util.polarizationName (pol), ant1, ant2, ant3)
        print '%20s: %10lg' % (s, rms)

print

#for (key, sa) in blStats.iteritems ():
#    (pol, ant1, ant2) = key
#    s = '%s-%d-%d' % (util.polarizationName (pol), ant1, ant2)
#    print '%20s: %10lg (%10lg, %5d)' % (s, sa.mean (), sa.std (), sa.num ())

#print

#for (key, sa) in antStats.iteritems ():
#    (pol, ant1) = key
#    s = '%s-%d' % (util.polarizationName (pol), ant1)
#    print '%20s: %10lg (%10lg, %5d)' % (s, sa.mean (), sa.std (), sa.num ())

if args.rmshist:
    import omega
    allrms.doneAdding ()
    print 'Showing histogram of RMS values ...'
    n = int (N.sqrt (len (allrms)))
    omega.quickHist (allrms.col (0), n).showBlocking ()

culprits = maybeBad.difference (shouldGood)
#print 'Should always be good:',', '.join ('%d-%d' % x for x in shouldGood)
print 'Sometimes bad and never good:', ', '.join ('%d-%d' % x for x in culprits)
print 'That\'s %d bad baselines and %d good ones' % (len (culprits), len (shouldGood))
nDub = 0
nOk = 0
explCounts = {}

for (key, ga) in allData.iteritems ():
    (pol, ant1, ant2, ant3) = key
    phs = ga.col (1)
    rms = N.sqrt (N.mean (phs**2))
    bls = [(ant1, ant2), (ant1, ant3), (ant2, ant3)]

    s = '%s-%d-%d-%d' % (util.polarizationName (pol), ant1, ant2, ant3)

    if rms < dubiousCutoff:
        nOk += 1
    else:
        nDub += 1
        expl = False
        
        for bl in bls:
            if bl in culprits:
                if bl not in explCounts: explCounts[(pol, bl)] = 1
                else: explCounts[(pol, bl)] += 1
                expl = True

        if not expl:
            print '%20s: NOT explained (rms = %g)' % (s, rms)

print

explInfo = explCounts.items ()

if len (explInfo) > 0:
    explInfo.sort (key = lambda x: x[1])

    for ((pol, bl), count) in explInfo:
        s = '%s-%d-%d' % (util.polarizationName (pol), bl[0], bl[1])
        print '%20s: shows up in %d dubious baselines' % (s, count)

    print

print '%d dubious triples, %d non-dubious triples (cutoff %lg)' % \
      (nDub, nOk, dubiousCutoff)
