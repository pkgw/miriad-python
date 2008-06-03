#! /usr/bin/env python
"""A flagging script"""
#* multiflag - Apply complex flagging operations to UV data in one pass.
#& pkgw
#: calibration, uv analysis
#+
#  MULTIFLAG changes the flags embedded in visibility data. Unlike UVFLAG,
#  blah blah.
#-

print 'This script is UNFINISHED and EXPERIMENTAL!!!!'

import sys
from mirtask import uvdat, keys, util
import numpy as N

class Condition (object):
    def __init__ (self, isSubRecord):
        self.isSubRecord = isSubRecord

    def matchRecord (self, inp, uvw, time, bl):
        # This function works as an AND with to-flagness:
        # return True if you DO match this record.
        raise NotImplementedError ()

    def matchSubRecord (self, inp, uvw, time, bl, data, flags):
        # This function works as an OR with flags: set flags[x]
        # to 1 for all X that you do NOT match.
        raise NotImplementedError ()

class CAnt (Condition):
    __slots__ = ['isSubRecord', 'ants']
    
    def __init__ (self, paramstr):
        Condition.__init__ (self, False)
        self.ants = set (int (x) for x in paramstr.split (','))

    def matchRecord (self, inp, uvw, time, bl):
        return bl[0] in self.ants or bl[1] in self.ants

class CBaseline (Condition):
    __slots__ = ['isSubRecord', 'bls']
    
    def __init__ (self, paramstr):
        Condition.__init__ (self, False)

        def blParse (s):
            a1, a2 = s.split ('-')
            a1, a2 = int (a1), int (a2)
            if a1 > a2: return (a2, a1)
            return (a1, a2)
        
        self.bls = set (blParse (s) for s in paramstr.split (','))

    def matchRecord (self, inp, uvw, time, bl):
        return bl in self.bls

class CPol (Condition):
    __slots__ = ['isSubRecord', 'pols']
    
    def __init__ (self, paramstr):
        Condition.__init__ (self, False)

        self.pols = set (mirtask.util.polarizationNumber (s) for s in paramstr.split (','))

    def matchRecord (self, inp, uvw, time, bl):
        return uvdat.getPol () in self.pols

class CAuto (Condition):
    __slots__ = ['isSubRecord']

    def __init__ (self, paramstr):
        Condition.__init__ (self, False)
        assert (paramstr is None)

    def matchRecord (self, inp, uvw, time, bl):
        return bl[0] == bl[1]
    
class CCross (Condition):
    __slots__ = ['isSubRecord']

    def __init__ (self, paramstr):
        Condition.__init__ (self, False)
        assert (paramstr is None)

    def matchRecord (self, inp, uvw, time, bl):
        return bl[0] != bl[1]

def mergeChannels (chanlist):
    # Assume channel numbers here are all 0-indexed
    merged = []

    for bmin, bmax in chanlist:
        for i in xrange (0, len (merged)):
            mmin, mmax = merged[i]

            if mmax < bmin: continue
            
            if mmin > bmax:
                # We need to insert a new entry here
                merged.insert (i, (bmin, bmax))
                break

            newmin = min (mmin, bmin)
            newmax = max (mmax, bmax)
            merged[i] = (newmin, newmax)
            break
        else:
            merged.append ((bmin, bmax))

    return merged
    
class CChannel (Condition):
    __slots__ = ['isSubRecord', 'intervals']

    def __init__ (self, paramstr):
        Condition.__init__ (self, True)

        def chParse (x):
            n, s = x.split (',')
            n, s = int (n), int (s)
            s -= 1 # FORTRAN-style indices to C-style
            return (s, s+n)

        chinfo = mergeChannels (chParse (s) for s in paramstr.split (';'))
        iStart = 0
        self.intervals = intervals = []
        
        for start, end in chinfo:
            iEnd = start

            if iEnd > iStart: intervals.append ((iStart, iEnd))

            iStart = end

        intervals.append ((iStart, -1))
        
    def matchSubRecord (self, inp, uvw, time, bl, data, flags):
        for (start, end) in self.intervals:
            if end == -1: flags[start:] = 1
            else: flags[start:end] = 1

class CATAHalf (Condition):
    __slots__ = ['isSubRecord', 'half']

    def __init__ (self, paramstr):
        Condition.__init__ (self, False)
        self.half = int (paramstr)
        assert (self.half == 1 or self.half == 2)

    def matchRecord (self, inp, uvw, time, bl):
        freq = inp.getVarDouble ('freq')
        sfreq = inp.getVarDouble ('sfreq')

        if freq == sfreq: half = 2
        elif abs (freq - sfreq - 0.0524288) < 0.001: half = 1
        else: assert (False), 'ATA corr half unknown!'

        return half == self.half
    
conditions = {
    'ant': CAnt, 'bl': CBaseline, 'pol': CPol,
    'auto': CAuto, 'cross': CCross, 'chan': CChannel,
    'atahalf': CATAHalf
    }

class Line (object):
    __slots__ = ['rconds', 'srconds']
    
    def __init__ (self):
        self.rconds = []
        self.srconds = []

    def add (self, cond):
        if cond.isSubRecord:
            self.srconds.append (cond)
        else:
            self.rconds.append (cond)

    def anySubRecord (self):
        return len (self.srconds) > 0
    
    def matchRecord (self, inp, uvw, time, bl):
        for c in self.rconds:
            if not c.matchRecord (inp, uvw, time, bl):
                return False
        return True

    def matchSubRecord (self, inp, uvw, time, bl, data, flags):
        if not self.matchRecord (inp, uvw, time, bl):
            flags[:] = 1
            return

        #print 'srb', matched[0:10]
        for c in self.srconds:
            c.matchSubRecord (inp, uvw, time, bl, data, flags)
        #print 'sra', matched[0:10]

# OK, done with preliminaries.

banner = 'MULTIFLAG: UV data multiflagger'
print banner

keys.keyword ('spec', 'f', ' ', 128)
keys.doUvdat ('3', False)
opts = keys.process ()

if len (opts.spec) < 1:
    print >>sys.stderr, 'Error: must give at least one "spec" filename'
    sys.exit (1)

# Read in the conditions
#
# The basic format is line-oriented
# If an entry matches a line, it is flagged.
# An entry matches a line if it matches *all* of the conditions in the line
# A condition in a line just looks like "attr=match"
# Conditions are separated by spaces
# If there are multiple match values, a condition is matched if *any* of those
# values are matched
# So the overall logical flow is
#  flag if [match any line]
#  match line if [match every condition]
#  match condition if [match any value]
#
# E.g. ...
#
# ant=24 pol=xx
# bl=1-4 cross
# pol=xx chan=128,1

rLines = []
srLines = []

for fname in opts.spec:
    for l in file (fname, 'r'):
        bits = l.strip ().split ()

        if len (bits) < 1: continue
        if bits[0][0] == '#': continue

        thisLine = Line ()

        for b in bits:
            split = b.split ('=', 2)
            if len (split) == 1: cond, arg = split[0], None
            else: cond, arg = split

            thisLine.add (conditions[cond] (arg))

        if thisLine.anySubRecord (): srLines.append (thisLine)
        else: rLines.append (thisLine)

print 'Parsed %d condition lines from %d file(s).' % (len (rLines) + len (srLines),
                                                      len (opts.spec))

# Flag the input file

curInp = None
lineFlags = None

for inp, preamble, data, flags, nread in uvdat.readAll ():
    if inp is not curInp:
        if curInp is not None:
            print '   %d of %d (%.1f%%) are now completely flagged' % (nR, nSeen, 100. * nR / nSeen)
            print '   %d of %d (%.1f%%) are now partially flagged' % (nSR, nSeen, 100. * nSR / nSeen)
            
        curInp = inp
        inp.openHistory ()
        inp.writeHistory (banner)
        inp.logInvocation ('MULTIFLAG')
        inp.closeHistory ()

        nR = nSR = nSeen = 0

        print inp.name, '...'
        
    nSeen += 1
    data = data[0:nread]
    flags = flags[0:nread]

    uvw = preamble[0:3]
    time = preamble[3]
    bl = util.decodeBaseline (preamble[4])

    hit = False
    for line in rLines:
        if line.matchRecord (inp, uvw, time, bl):
            hit = True
            break

    if hit:
        nR += 1
        flags.fill (0)
    elif len (srLines) > 0:
        if lineFlags is None or lineFlags.shape != flags.shape:
            lineFlags = flags.copy ()

        for line in srLines:
            lineFlags.fill (0)
            line.matchSubRecord (inp, uvw, time, bl, data, lineFlags)
            flags &= lineFlags
            
        if nSeen % 4000 == 0: print 'fmf', flags[0:10]

        nUnflagged = flags.sum ()

        if nUnflagged == 0:
            nR += 1
        elif nUnflagged < flags.size:
            nSR += 1
        
    inp.rewriteFlags (flags)

print '   %d of %d (%.1f%%) are now completely flagged' % (nR, nSeen, 100. * nR / nSeen)
print '   %d of %d (%.1f%%) are now partially flagged' % (nSR, nSeen, 100. * nSR / nSeen)

# All done. Boogie.

sys.exit (0)
