## Copyright 2009-2012 Peter Williams
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

mtpydir = $(pyexecdir)/mirtask

mtpy_PYTHON = \
  __init__.py \
  cliutil.py \
  emucal.py \
  keys.py \
  readgains.py \
  util.py \
  uvdat.py \
  _uvdat_compat_24.py \
  _uvdat_compat_default.py

lib_LTLIBRARIES = libmirtasksupport.la
mtpy_LTLIBRARIES = _miriad_c.la _miriad_f.la

AM_CPPFLAGS = -I$(NUMPY_INCLUDEDIR) $(MIR_CPPFLAGS) $(PYTHON_INCLUDES)
mod_ldflags = -module -avoid-version

libmirtasksupport_la_LDFLAGS =
libmirtasksupport_la_LIBADD = $(PYTHON_LIBS) $(MIR_LIBS)
libmirtasksupport_la_SOURCES = \
  fortranobject.c fortranobject.h \
  mirtasksupport.c mirtasksupport.h

_miriad_c_la_LDFLAGS = $(mod_ldflags) -export-symbols-regex init_miriad_c
_miriad_c_la_LIBADD = libmirtasksupport.la $(MIR_LIBS)
_miriad_c_la_SOURCES = _miriad_cmodule.c

_miriad_f_la_LDFLAGS = $(mod_ldflags) -export-symbols-regex init_miriad_f
_miriad_f_la_LIBADD = libmirtasksupport.la $(MIR_LIBS)
_miriad_f_la_SOURCES = _miriad_fmodule.c _miriad_f-f2pywrappers.f

# f2py doesn't specify what license(s) may be applied to the files
# it generates. These generated files are distributed, however, so
# they should have copyright notices applied. Manually munge in a
# statement saying that the status is unclear but that the license
# is speculatively GPLv3+.

EXTRA_DIST = f2py-copynotice.txt

_%module.c _%-f2pywrappers.f: %.fproto f2py-copynotice.txt
	$(F2PY) -m _$* $<
	mv _$*module.c _$*moduletmp.c ; \
	sed -e 's|%START|/*|' -e 's|%IN| *|' -e 's|%END|*/|' \
	  <f2py-copynotice.txt \
	  >_$*module.c ; \
	cat _$*moduletmp.c >>_$*module.c ; \
	rm -f _$*moduletmp.c
	mv _$*-f2pywrappers.f _$*-f2pywrapperstmp.f ; \
	sed -e 's|%START|c     |' -e 's|%IN|c    |' -e 's|%END|c     |' \
	  <f2py-copynotice.txt \
	  >_$*-f2pywrappers.f ; \
	cat _$*-f2pywrapperstmp.f >>_$*-f2pywrappers.f ; \
	rm -f _$*-f2pywrapperstmp.f
