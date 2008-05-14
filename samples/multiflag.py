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
from mirtask import uvdat, keys
import numpy as N

banner = 'MULTIFLAG: UV data multiflagger'
print banner

keys.keyword ('spec', 'f', ' ', 128)
keys.doUvdat ('b3', False)
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

spec = []

for fname in opts.spec:
    for l in file (fname, 'r'):
        bits = l.strip ().split ()

        if len (bits) < 1: continue
        if bits[0][0] == '#': continue

        thisLine = []

        for b in bits:
            split = b.split ('=', 2)
            if len (split) == 1: cond, arg = split[0], None
            else: cond, arg = split

            if cond == 'ant':
                # FIXME: try / raise
                ants = arg.split (',')
                ants = tuple (int (x) for x in ants)
                thisLine.append ((cond, ) + ants)
            elif cond == 'bl':
                bls = arg.split (',')
                l = (cond, )
                for blname in bls:
                    ants = blname.split ('-')
                    assert (len (ants) == 2)
                    l += tuple (int (x) for x in ants)
                thisLine.append (l)
            elif cond == 'pol':
                pols = arg.split (',')
                pols = tuple (mirtask.util.polarizationNumber (x) for x in pols)
                thisLine.append ((cond, ) + pols)
            elif cond == 'auto':
                assert (arg is None)
                thisLine.append ((cond, ))
            elif cond == 'cross':
                assert (arg is None)
                thisLine.append ((cond, ))
            elif cond == 'chan':
                chspec = arg.split (',')
                assert (len (chspec) == 2)
                num, start = (int (x) for x in chspec)
                start -= 1 # Go from FORTRAN-style offsets to C-style
                thisLine.append ((cond, num, start))
            else: raise Exception ('Unknown condition "%s" in "%s".' % (cond, fname))

        spec.append (thisLine)

print 'Parsed %d condition lines from %d file(s).' % (len (spec), len (opts.spec))

# FIXME: post-process to simplify logic.

# Flag the input file

inp = uvdat.singleInputSet ()

inp.openHistory ()
inp.writeHistory (banner)
inp.logInvocation ('MULTIFLAG')
inp.closeHistory ()

for preamble, data, flags, nread in uvdat.readData ():
    data = data[0:nread]
    flags = flags[0:nread]

    uvw = preamble[0:3]
    time = preamble[3]
    bl = mirtask.util.decodeBaseline (preamble[4])

    for line in spec:
        matched = N.ones_like (flags)

        for params in line:
            cond, args = params[0], params[1:]
            
            if cond == 'ant':
                hit = False
                for ant in args:
                    hit = hit or (bl[0] == arg or bl[1] == arg)
                matched = N.logical_and (matched, hit)
            elif cond == 'bl':
                hit = False
                for bl in args:
                    hit = hit or (bl == arg)
                matched = N.logical_and (matched, hit)
            elif cond == 'pol':
                hit = False
                thisPol = uvdat.getPol ()
                for pol in args:
                    hit = hit or (pol == thisPol)
                matched = N.logical_and (matched, hit)
            elif cond == 'auto':
                matched = N.logical_and (matched, bl[0] == bl[1])
            elif cond == 'cross':
                matched = N.logical_and (matched, bl[0] != bl[1])
            elif cond == 'chan':
                num, start = args
                matched[:start] = 0
                matched[start + num:] = 0
            else: assert (False)
    
        w = N.where (matched)
        #print 'Flagging:', len (w[0])
        flags[w] = 0
    
    inp.rewriteFlags (flags)

# All done. Write history entry and quit.

sys.exit (0)

