#! /bin/sh

set -e
set -x
libtoolize -c
aclocal -I .
automake -c --add-missing --foreign
autoconf
