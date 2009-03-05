SUBDIRS = mirtask

if BUILD_DOCS
SUBDIRS += doc
endif

# Main modules ...

python_PYTHON = miriad.py mirexec.py numutils.py

bin_SCRIPTS = mirpyhelp.py mirpymodtask.py

# pkg-config

pcdir = $(libdir)/pkgconfig
pc_DATA = miriad-python.pc
