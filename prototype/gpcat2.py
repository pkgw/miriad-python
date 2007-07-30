#!/usr/bin/python
#
# Print out gains information from a vis file. Based on gplist,
# but not constrained to CARMA, and doesn't support rewriting gains
# tables.

import sys, os
import mirtask
import mirtask.lowlevel as ll
import numpy as N

print 'GpCat2: Python'

# keys initialized by mirtask.__init__.
vis = ll.keya ('vis', ' ')
ll.keyfin ()

if vis == ' ':
    raise MiriadError ('An input file must be given')

ds = mirtask.DataSet (vis)
gr = mirtask.readgains.GainsReader (ds)
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
    
    print '%s:' % (ll.julday (time, 'H'), ),

    for ant in ants:
        print ' %8lf' % (abs (gains[ant * gr.nfeeds])),
    print

# All done.

del ds
