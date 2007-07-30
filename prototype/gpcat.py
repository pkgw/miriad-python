#!/usr/bin/python
#
# Print out gains information from a vis file. Based on gplist,
# but not constrained to CARMA, and doesn't support rewriting gains
# tables.

import sys, os
import pymirread
import numpy as N
m = pymirread._mirgood
u = pymirread._uvio

print 'GpCat: Python'
# keys initialized by pymirread.__init__.
vis = u.keya ('vis', ' ')
u.keyfin ()

if vis == ' ':
    raise MiriadError ('An input file must be given')

def iocheck (iostat):
    # Temporary. Should have a higher-level layer that takes care of this stuff.
    if iostat != 0:
        raise MiriadError ('IO error with file "%s": %s' % (vis, os.strerror (iostat)))
    
(tvis, iostat) = u.hopen (vis, 'old')
iocheck (iostat)

if not u.hexists (tvis, 'gains'):
    raise MiriadError ('Input "%s" doesn\'t have a gains table!' % vis)

ngains = u.rdhdi (tvis, 'ngains', 0)
nfeeds = u.rdhdi (tvis, 'nfeeds', 1)
ntau = u.rdhdi (tvis, 'ntau', 0)

if nfeeds < 1 or nfeeds > 2 or \
   ngains % (nfeeds + ntau) != 0 or \
   ntau > 1 or ntau < 0:
    raise MiriadError ('Bad number of gains or feeds in "%s"' % vis)

if nfeeds != 1: raise MiriadError ('PKGW exception: not sure what to do about multifeeds')

nants = ngains / (nfeeds + ntau)

print 'Found gain entries for %d antennas.' % nants

# Main bit (ReplGain in gplist.for)

(tgains, iostat) = u.haccess (tvis, 'gains', 'read')
iocheck (iostat)

ngains = nants * (nfeeds + ntau)
nsols = (u.hsize (tgains) - 8) / (8 * ngains + 8)
offset = 8
pnt = 0

time = N.ndarray (nsols, dtype=N.double)
gains = N.ndarray (nsols * ngains, dtype=N.complex64)

for i in xrange (0, nsols):
    iocheck (u.hreadd (tgains, time[i:], offset, 8))
    offset += 8

    iocheck (u.hreadc (tgains, gains[pnt:], offset, 8 * ngains))
    pnt += ngains
    offset += 8 * ngains

iocheck (u.hdaccess (tgains))

# New: which ants have non-zero gains? Print 'em.

ants = []

for i in xrange (0, nants):
    if abs (gains[i*nfeeds]) > 0: ants.append (i)

# Header row - the blanks offset the time prefix
print 'Printing gain amplitudes only.'
print '                   ', 
for ant in ants:
    print ' Ant %4d' % (ant + 1, ),
print

# Data
for i in xrange (0, nsols):
    print '%s:' % (pymirread.julday (time[i], 'H'), ),

    for ant in ants:
        print ' %8lf' % (abs (gains[i * ngains + ant * nfeeds])),
    print

# All done.

u.hclose (tvis)
