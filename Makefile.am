## Copyright 2009 Peter Williams
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

SUBDIRS = mirtask

if BUILD_DOCS
SUBDIRS += doc
endif

# Main modules ...

python_PYTHON = miriad.py mirexec.py numutils.py

dist_bin_SCRIPTS = mirpyhelp.py mirpymodtask.py

# pkg-config

pcdir = $(libdir)/pkgconfig
pc_DATA = miriad-python.pc

# Distributing

DISTCHECK_CONFIGURE_FLAGS = @MIR_DISTCHECK_CONFARG@
EXTRA_DIST = LICENSE LICENSE.GPLv3 LICENSE.LGPLv21 f2py-copynotice.txt
