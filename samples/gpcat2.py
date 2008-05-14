#!/usr/bin/python
#
# Print out gains information from a vis file. Based on gplist,
# but not constrained to CARMA, and doesn't support rewriting gains
# tables.

import sys, os
import miriad
from mirtask import keys, readgains
from mirtask.util import jdToFull
import numpy as N

banner = 'GPCAT2: Python take on gpcat that doesn\'t crash'
print banner

keys.keyword ('vis', 'f', ' ')
opts = keys.process ()

if opts.vis == ' ':
    print >>sys.stderr, 'An input file must be given'
    sys.exit (1)

ds = miriad.Data (opts.vis).open ('r')
gr = readgains.GainsReader (ds)
gr.prep ()

print 'Found gain entries for %d antennas.' % (gr.nants)
print 'Printing gain amplitudes only.'

first = True

for (time, gains) in gr.readSeq ():
    if first:
        # Figure out which ants are present

        ants = []
        
        for i in xrange (0, gr.nants):
            if abs (gains[i * gr.nfeeds]) > 0: ants.append (i)

        # Now print a header row - the blanks offset the time prefix

        print '                   ', 
        for ant in ants:
            print ' Ant %4d' % (ant + 1, ),
        print

        first = False

    # Now print the data
    
    print jdToFull (time) + ':', 

    for ant in ants:
        print ' %8.7lg' % (abs (gains[ant * gr.nfeeds])),
    print

# All done.

del ds
