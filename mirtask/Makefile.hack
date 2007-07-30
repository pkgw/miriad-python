MIR = /l/pkwill/opt/miriad-x86_64-Linux-suse10.1
mirlib = $(MIR)/lib
mirinc= $(MIR)/include/miriad-c
CFLAGS = -g -O2 -Wall -pthread -fno-strict-aliasing -D_FORTIFY_SOURCE=2
MIRFLAGS = -I$(mirinc)

all: _uvio.so _mirgood.so _mirugly.so

NUMPY = /l/pkwill/opt/x86_64-Linux-suse10.1/lib64/python2.4/site-packages/numpy
PYFLAGS = -I/usr/include/python2.4 -I$(NUMPY)/f2py/src -I$(NUMPY)/core/include

.SECONDARY:

_uvio.so: _uviomodule.o
	gcc $(CFLAGS) $(PYFLAGS) -shared -fPIC -o $@ $^ \
	  -Wl,-soname -Wl,_uvio.so -Wl,--rpath -Wl,`pwd` \
	  -L$(mirlib) -lmir_uvio -Wl,--rpath -Wl,$(mirlib)

# f2py --g3-numpy doesn't seem to work?

%.so: %module.o %-f2pywrappers.o fortranobject.o _uvio.so
	gcc $(CFLAGS) $(PYFLAGS) -shared -fPIC -o $@ $^ \
	  -Wl,-soname -Wl,$*.so -Wl,--rpath -Wl,`pwd` \
	  -L$(mirlib) -lmir -lmir_uvio -lmir_linpack -lpgplot -Wl,--rpath -Wl,$(mirlib)

%.o: %.c
	gcc $(CFLAGS) $(PYFLAGS) $(MIRFLAGS) -fPIC -DPIC -o $@ -c $<

%-f2pywrappers.o: %-f2pywrappers.f
	gfortran $(CFLAGS) -fPIC -DPIC -o $@ -c $<

_%module.c _%-f2pywrappers.f: %.fproto
	f2py -m _$* $*.fproto >&make-$*-wrappers.log

# Generate the fproto

VPATH = /l/pkwill/cvs/cosmic/miriad/BUILD/src/subs

fproto:
	-mv miriad.fproto miriad.fproto.bak
	f2py -h miriad.fproto `cat inputs.list |grep -v '^#'` >&make-fproto.log

# commented-out or erroring things
#
# nllsqu failed because of a variable named 'function'
# lsqfit failed because f2py wasn't able to guess the prototype of
#   the function argument FCN, because it is only passed to other
#   routines.
# model failed for the same reason, with 'header' and 'calget' functions.
# ari failed for the same reason, with 'paction'.
#
# nswc: lmdiff has problem with 'fcn'
# win: winshow, 'func'
# bsrch: binsrcha, some 'keys' dimensions problem

FAILS = lsqfit model nllsqu ari calsubs

failmods: $(patsubst %,_%.so,$(FAILS))
failprotos: $(FAILS:=.fproto)

%.failproto: %.f
	-mv $@ $@.bak
	f2py -h $@ $< >&make-$*-fproto.log

mynllsqu.fproto:
	f2py -h $@ mynllsqu.f >&make-mynllsqu-fproto.log

lsqfit.fproto: lsqfit.failproto
	-ln -s $< $@

model.fproto: model.failproto
	-ln -s $< $@

nllsqu.fproto: nllsqu.failproto
	-ln -s $< $@

ari.fproto: ari.failproto
	-ln -s $< $@

calsubs.fproto: calsubs.failproto
	-ln -s $< $@

