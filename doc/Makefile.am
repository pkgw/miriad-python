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

dist_noinst_DATA = \
 data.txt \
 data-highlev.txt \
 data-lowlev.txt \
 data-util.txt \
 executing.txt \
 index.txt \
 intro.txt \
 pytasks.txt \
 pytasks-cliutil.txt \
 pytasks-keys.txt \
 pytasks-uvdat.txt

# Temp hack: make sure the 'static' directory gets created
EXTRA_DIST = static/.gitignore

SCANNEDPY = \
 $(top_srcdir)/mirexec.py \
 $(top_srcdir)/miriad.py \
 $(top_srcdir)/mirtask/__init__.py \
 $(top_srcdir)/mirtask/cliutil.py \
 $(top_srcdir)/mirtask/keys.py \
 $(top_srcdir)/mirtask/util.py \
 $(top_srcdir)/mirtask/uvdat.py

HTML_STAMP = sphinx-html.stamp

all-local: $(HTML_STAMP)

# Want to see something terrible? In order for the Sphinx autodoc module
# to work, it needs to be able to import our Python modules, so we need
# to futz with $PYTHONPATH to work with our uninstalled data. Furthermore,
# some of these modules import the native extension modules within the
# mirtask package. The needed shared libraries live within .libs directories,
# so Python won't find them. Right now, my solution is to do a mini
# "make install" into a $DESTDIR in our build tree, because by definition
# that will give us our modules in the correct directory hierarchy with
# some easy munging of $PYTHONPATH.

$(HTML_STAMP): $(dist_noinst_DATA) $(SCANNEDPY)
	eval `$(top_builddir)/libtool --config |$(GREP) ^shlibpath_var` && \
	rm -rf module_staging && \
	$(MKDIR_P) html doctrees module_staging && \
	dest=`cd module_staging && pwd` && \
	eval "$$shlibpath_var=$$dest$(libdir):\$$$$shlibpath_var ; export $$shlibpath_var" && \
	echo ================ Begin scratch doc installation && \
	(cd $(top_builddir) && $(MAKE) install SUBDIRS=". mirtask" DESTDIR=$$dest) && \
	echo ================ End scratch doc installation && \
	PYTHONPATH=$$dest$(pyexecdir):$$dest$(pythondir):$$PYTHONPATH \
	  $(SPHINXBUILD) -d doctrees -c . -b html $(srcdir) html && \
	rm -rf module_staging && \
	touch $@

clean-local:
	-rm -rf doctrees html
	-rm -f $(HTML_STAMP)

# Helper target to upload the docs to the website

websitehost = cfa0
websitedir = /data/wdocs/pwilliam/www-docs/miriad-python/docs

push: $(HTML_STAMP)
	ssh $(websitehost) rm -rf $(websitedir)/*
	tar cz -C html . |ssh $(websitehost) tar xz -C $(websitedir)

view: $(HTML_STAMP)
	firefox ./html/index.html &
