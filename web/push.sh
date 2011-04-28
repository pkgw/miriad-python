#! /bin/sh

set -x
cp -p index.html style.css $HOME/public_html/miriad-python/
cd ../BUILD*/doc && make push
