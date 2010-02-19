## Copyright 2009, 2010 Peter Williams
##
## This file is part of miriad-python.
##
## Miriad-python is free software: you can redistribute it and/or
## modify it under the terms of the GNU General Public License as
## published by the Free Software Foundation, either version 3 of the
## License, or (at your option) any later version.
##
## Miriad-python is distributed in the hope that it will be useful, but
## WITHOUT ANY WARRANTY; without even the implied warranty of
## MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
## General Public License for more details.
##
## You should have received a copy of the GNU General Public License
## along with miriad-python.  If not, see <http://www.gnu.org/licenses/>.
##
## (This copyright notice is delimited with double hashes to prevent it
## from being confusingly included in Makefile.in by automake.)

mtpydir = $(pythondir)/mirtask
mtpyexecdir = $(pyexecdir)/mirtask

mtpy_PYTHON = \
  __init__.py \
  lowlevel.py \
  \
  base.py \
  keys.py \
  readgains.py \
  util.py \
  uvdat.py

lib_LTLIBRARIES = libmirtasksupport.la
mtpyexec_LTLIBRARIES = _uvio.la _mirgood.la #_mirugly.la

AM_CFLAGS = -Wall -g -O2 $(PYTHON_INCLUDES) -I$(NUMPY_INCLUDEDIR) $(MIR_CFLAGS) -I$(srcdir)
mod_ldflags = -module -avoid-version

libmirtasksupport_la_LDFLAGS =
libmirtasksupport_la_LIBADD = $(PYTHON_LIBS) $(MIR_LIBS)
libmirtasksupport_la_SOURCES = \
  fortranobject.c fortranobject.h \
  mirtasksupport.c mirtasksupport.h

_uvio_la_LDFLAGS = $(mod_ldflags) -export-symbols-regex init_uvio
_uvio_la_LIBADD = libmirtasksupport.la $(MIR_LIBS)
_uvio_la_SOURCES = _uviomodule.c

_mirgood_la_LDFLAGS = $(mod_ldflags) -export-symbols-regex init_mirgood
_mirgood_la_LIBADD = libmirtasksupport.la $(MIR_LIBS)
_mirgood_la_SOURCES = _mirgoodmodule.c _mirgood-f2pywrappers.f

#_mirugly_la_LDFLAGS = $(mod_ldflags) -export-symbols-regex init_mirugly
#_mirugly_la_LIBADD = libmirtasksupport.la
#_mirugly_la_SOURCES = _miruglymodule.c _mirugly-f2pywrappers.f

# f2py doesn't specify what license(s) may be applied to the files
# it generates. These generated files are distributed, however, so 
# they should have copyright notices applied. Manually munge in a
# statement saying that the status is unclear but that the license
# is speculatively GPLv3+.

_%module.c _%-f2pywrappers.f: %.fproto $(top_srcdir)/f2py-copynotice.txt
	$(F2PY) -m _$* $<
	mv _$*module.c _$*moduletmp.c ; \
	sed -e 's|%START|/*|' -e 's|%IN| *|' -e 's|%END|*/|' \
	  <$(top_srcdir)/f2py-copynotice.txt \
	  >_$*module.c ; \
	cat _$*moduletmp.c >>_$*module.c ; \
	rm -f _$*moduletmp.c
	mv _$*-f2pywrappers.f _$*-f2pywrapperstmp.f ; \
	sed -e 's|%START|c     |' -e 's|%IN|c    |' -e 's|%END|c     |' \
	  <$(top_srcdir)/f2py-copynotice.txt \
	  >_$*-f2pywrappers.f ; \
	cat _$*-f2pywrapperstmp.f >>_$*-f2pywrappers.f ; \
	rm -f _$*-f2pywrapperstmp.f
