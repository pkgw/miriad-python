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

dist_noinst_DATA = \
 data.txt \
 data-highlev.txt \
 data-lowlev.txt \
 executing.txt \
 index.txt \
 intro.txt \
 pytasks.txt \
 pytasks-keys.txt \
 pytasks-uvdat.txt

# Temp hack: make sure the 'static' directory gets created
EXTRA_DIST = static/.gitignore

SCANNEDPY = \
 $(top_srcdir)/miriad.py

BUILD = eval `$(top_builddir)/libtool --config |$(GREP) objdir=` ; PYTHONPATH=$(top_srcdir):$(top_builddir)/mirtask/$$objdir:$$PYTHONPATH $(SPHINXBUILD) -d doctrees -c .

HTML_STAMP = sphinx-html.stamp

all-local: $(HTML_STAMP)

$(HTML_STAMP): $(dist_noinst_DATA) $(SCANNEDPY)
	$(MKDIR_P) html doctrees
	$(BUILD) -b html $(srcdir) html
	touch $@

clean-local:
	-rm -rf doctrees html
	-rm -f $(HTML_STAMP)

# Helper target to upload the docs to the website

websitedir = $(HOME)/public_html/miriad-python/docs

push: $(HTML_STAMP)
	rm -rf $(websitedir)/*
	cp -a html/* $(websitedir)
