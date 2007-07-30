mtpydir = $(pythondir)/mirtask
mtpyexecdir = $(pyexecdir)/mirtask

mtpy_PYTHON = \
  __init__.py \
  lowlevel.py \
  \
  base.py \
  readgains.py

lib_LTLIBRARIES = libmirtasksupport.la
mtpyexec_LTLIBRARIES = _uvio.la _mirgood.la _mirugly.la

AM_CFLAGS = $(PYTHON_INCLUDES) -I$(NUMPY_INCLUDEDIR) $(MIR_CFLAGS) -I$(srcdir)
AM_LDFLAGS = -module -avoid-version
gen_libadd = $(PYTHON_LIBS) $(MIR_LIBS)

libmirtasksupport_la_LDFLAGS =
libmirtasksupport_la_LIBADD = $(PYTHON_LIBS) $(MIR_LIBS)
libmirtasksupport_la_SOURCES = \
  fortranobject.c fortranobject.h \
  mirtasksupport.c mirtasksupport.h

_uvio_la_LDFLAGS = $(AM_LDFLAGS) -export-symbols-regex init_uvio
_uvio_la_LIBADD = libmirtasksupport.la
_uvio_la_SOURCES = _uviomodule.c

_mirgood_la_LDFLAGS = $(AM_LDFLAGS) -export-symbols-regex init_mirgood
_mirgood_la_LIBADD = libmirtasksupport.la
_mirgood_la_SOURCES = _mirgoodmodule.c _mirgood-f2pywrappers.f

_mirugly_la_LDFLAGS = $(AM_LDFLAGS) -export-symbols-regex init_mirugly
_mirugly_la_LIBADD = libmirtasksupport.la
_mirugly_la_SOURCES = _miruglymodule.c _mirugly-f2pywrappers.f

_%module.c _%-f2pywrappers.f: %.fproto
	$(F2PY) -m _$* $<
