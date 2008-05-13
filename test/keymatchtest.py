#!/usr/bin/python

import mirtask
import mirtask.lowlevel as ll
import mirtask._mirgood as mg
from numstd import *

ll.keyini (['mytask', 'mykey=fo,ba,bim'])
res = ll.keymatch ('mykey', ['foo', 'bar', 'bim', 'bap'], 5)

print res

