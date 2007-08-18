#!/usr/bin/python

import mirtask
import mirtask.lowlevel as ll
from numstd import *

ll.keyini (['mytask', 'options=foo,bar,bam,bob'])

a = numpy.chararray ((3,8))
o = ['foo', 'bar', 'baz']

for i in range (0, len (o)):
    s = o[i]
    
    for j in range (0, len (s)):
        a[i,j] = s[j]

a2 = ['foo    ', 'bar    ', 'baz    ', 'bam    ', 'bob    ', 'bazzaa2']
print ll.options ('options', a2)

