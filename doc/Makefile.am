dist_noinst_DATA = \
 data.txt \
 data-highlev.txt \
 data-lowlev.txt \
 executing.txt \
 index.txt \
 intro.txt \
 pytasks.txt

# Temp hack: make sure the 'static' directory gets created
EXTRA_DIST = static/.gitignore

SCANNEDPY = \
 $(top_srcdir)/miriad.py

BUILD = PYTHONPATH=$(top_srcdir):$$PYTHONPATH $(SPHINXBUILD) -d doctrees -c .

HTML_STAMP = sphinx-html.stamp

all-local: $(HTML_STAMP)

$(HTML_STAMP): $(dist_noinst_DATA) $(SCANNEDPY)
	$(MKDIR_P) html doctrees
	$(BUILD) -b html $(srcdir) html
	touch $@

clean-local:
	-rm -rf doctrees html
	-rm -f $(HTML_STAMP)
