#! /usr/bin/env python

import numpy as N
from mirtask import keys, util, uvdat
from numutils import *
import sys

banner = 'CLOSANAL (Python): attempt to diagnose bad baselines based on phase triple closures.'
print banner

SECOND = 1.0 / 3600. / 24.

keys.keyword ('interval', 'd', 0.01)
keys.keyword ('cutoffs', 'd', None, 3)
keys.keyword ('numemp', 'i', 10)
keys.option ('rmshist')
keys.doUvdat ('dsl3x', True)

integData = {}
accData = {}

def cr (): return GrowingArray (N.double, 3)
allData = AccDict (cr, lambda ga, tup: ga.add (*tup))

seenants = set ()
seenpols = set ()

def blfmt (pol, ant1, ant2):
    return '%s-%d-%d' % (util.polarizationName (pol), ant1, ant2)

def tripfmt (pol, ant1, ant2, ant3):
    return '%s-%d-%d-%d' % (util.polarizationName (pol), ant1, ant2, ant3)

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

print 'Using cutoffs: good < %g deg, dubious > %g deg, bad > %g deg' \
      % (goodCutoff, dubiousCutoff, badCutoff)
print 'Averaging interval: %g minutes' % (args.interval)

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

print ' ... done.'

flushInteg (t)
flushAcc ()

#blStats = AccDict (StatsAccumulator, lambda sa, rms: sa.add (rms))
#antStats = AccDict (StatsAccumulator, lambda sa, rms: sa.add (rms))
shouldGood = set ()
maybeBad = {}

if args.rmshist:
    allrms = GrowingArray (N.double, 1)

anyDubious = False

def addBad (pol, ant1, ant2):
    key = (pol, ant1, ant2)

    if key in maybeBad:
        maybeBad[key] += 1
    else:
        maybeBad[key] = 1

nGood = 0
nBad = 0
nDubious = 0
nTotal = 0

for (key, ga) in allData.iteritems ():
    ga.doneAdding ()    
    (pol, ant1, ant2, ant3) = key
    phs = ga.col (1)
    rms = N.sqrt (N.mean (phs**2))

    if args.rmshist:
        allrms.add (rms)

    nTotal += 1
    
    #blStats.accum ((pol, ant1, ant2), rms)
    #blStats.accum ((pol, ant1, ant3), rms)
    #blStats.accum ((pol, ant2, ant3), rms)
    #antStats.accum ((pol, ant1), rms)
    #antStats.accum ((pol, ant2), rms)
    #antStats.accum ((pol, ant3), rms)

    if rms < goodCutoff:
        shouldGood.add ((pol, ant1, ant2))
        shouldGood.add ((pol, ant1, ant3))
        shouldGood.add ((pol, ant2, ant3))
        nGood += 1
    elif rms > badCutoff:
        addBad (pol, ant1, ant2)
        addBad (pol, ant1, ant3)
        addBad (pol, ant2, ant3)
        nBad += 1

    if rms > dubiousCutoff:
        if nDubious == 0:
            print
            print 'Triples with dubious phase closure values:'
        print '%20s: %10g' % (tripfmt (pol, ant1, ant2, ant3), rms)
        nDubious += 1

print
print 'Out of %d triples, found' % nTotal
print '%20d good' % nGood
print '%20d dubious' % (nDubious - nBad)
print '%20d bad' % nBad
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

theoCulprits = set (maybeBad.iterkeys ()).difference (shouldGood)
#print 'Should always be good:',', '.join ('%d-%d' % x for x in shouldGood)

allEmpCulprits = sorted (maybeBad.iteritems (), key=lambda x: x[1], reverse=True)
empCulprits = []

for i in xrange (0, len (allEmpCulprits)):
    if allEmpCulprits[i][0] not in theoCulprits:
        empCulprits.append (allEmpCulprits[i])

    if len (empCulprits) >= args.numemp: break

if len (theoCulprits) == 0:
    print 'No theoretical culprit baselines detected. If there are clearly bad closure triples, try:'
    print '  * Raising the integration interval'
    print '  * Lowering the "good" cutoff'
    print '  * Raising the "dubious" cutoff'
    print '  * Lowering the "bad" cutoff'
    print '  * Examining spectra for RFI or other problems'
else:
    print ('There are %d theoretical culprit baselines, which are in ' + \
          'some bad triples and no good ones:') % len (theoCulprits)
    for x in theoCulprits: print '%20s' % blfmt (*x)

if len (empCulprits) > 0:
    print
    print ('Here are the top %d empirical culprit baselines not listed ' + \
          'above, ranked by the number of bad triples they appear in:') % len (empCulprits)
    for x in empCulprits: print '%20s: %d' % (blfmt (*x[0]), x[1])

#print
#print 'There are %d baselines that are at least sometimes in a good triple.' % len (shouldGood)

nDub = 0
nOk = 0
explCounts = {}
unexpls = []

for (key, ga) in allData.iteritems ():
    (pol, ant1, ant2, ant3) = key
    phs = ga.col (1)
    rms = N.sqrt (N.mean (phs**2))
    bls = [(ant1, ant2), (ant1, ant3), (ant2, ant3)]

    if rms < dubiousCutoff:
        nOk += 1
    else:
        nDub += 1
        expl = False
        
        for bl in bls:
            if bl in theoCulprits:
                if bl not in explCounts: explCounts[(pol, bl)] = 1
                else: explCounts[(pol, bl)] += 1
                expl = True

        if not expl: unexpls.append ((key, rms))

if len (unexpls) > 0:
    print
    print 'Unexplained dubious triples - these do not involve a theoretical culprit baseline:'
    for trip, rms in sorted (unexpls, key=lambda x: x[1], reverse=True):
        print '%20s: rms = %g' % (tripfmt (*trip), rms)

print

explInfo = explCounts.items ()

if len (explInfo) > 0:
    explInfo.sort (key = lambda x: x[1])

    for ((pol, bl), count) in explInfo:
        print '%20s: shows up in %d dubious baselines' % (blfmt (pol, bl[0], bl[1]), count)

    print

print '%d dubious triples, %d without a theoretical culprit' % (nDub, len (unexpls))
print '%d non-dubious triples (cutoff %g)' % (nOk, dubiousCutoff)
