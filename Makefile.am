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

SUBDIRS = mirtask examples

if BUILD_DOCS
SUBDIRS += doc
endif

ACLOCAL_AMFLAGS = -I build-aux

# Main modules ...

python_PYTHON = miriad.py mirexec.py

dist_bin_SCRIPTS = mirpyhelp.py mirpymodtask

# pkg-config

pcdir = $(libdir)/pkgconfig
pc_DATA = miriad-python.pc

# Distributing. The 'snapshot' target makes a distribution with the
# day's date and the HEAD Git commit munged into the version number,
# then copies it to my website directory. (If the working tree is
# dirty, "_d" is appended to the version. The logic for this is copied
# from git.git/GIT-VERSION-GEN with little understanding.) We have to
# hack a little bit to get the custom version number reflected in the
# configure script, not just the tar directory name.

DISTCHECK_CONFIGURE_FLAGS = @MIR_DISTCHECK_CONFARG@
EXTRA_DIST = LICENSE README.md

snapshot:
	export GIT_WORK_TREE=$(top_srcdir) && \
	git update-index -q --refresh && \
	gitref=$$(git show-ref -h --hash=6 |head -n1) && \
	[ -z "$$(git diff-index --name-only HEAD --)" ] || gitref="$${gitref}_d" ; \
	effver="$(VERSION).$$(date +%Y%m%d).$$gitref" && \
	base="$(PACKAGE)-$$effver" && \
	$(MAKE) distdir distdir=$$base && \
	sed -e "s/^AC_INIT(\[$(PACKAGE)\], \[$(VERSION)\])/AC_INIT(\[$(PACKAGE)\], \[$$effver\])/" \
	  $(top_srcdir)/configure.ac >$$base/configure.ac && \
	(cd $$base && $(AUTOCONF)) && \
	tardir=$$base && $(am__tar) |GZIP=$(GZIP_ENV) gzip -c >$$base.tar.gz && \
	cp -p $$base.tar.gz $(HOME)/public_html/miriad-python/ && \
	$(MAKE) snapshot-remove-helper distdir=$$base

snapshot-remove-helper:
	$(am__remove_distdir)
