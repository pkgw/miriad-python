noinst_DATA = \
 index.txt

SCANNEDPY = \
 $(top_srcdir)/miriad.py

BUILD = PYTHONPATH=$(top_srcdir):$$PYTHONPATH $(SPHINXBUILD) -d doctrees -c .

HTML_STAMP = sphinx-html.stamp

all-local: $(HTML_STAMP)

$(HTML_STAMP): $(noinst_DATA) $(SCANNEDPY)
	$(MKDIR_P) html doctrees
	$(BUILD) -b html $(srcdir) html
	touch $@

clean-local:
	-rm -rf doctrees html
	-rm -f $(HTML_STAMP)
