#! /bin/sh

dest="cfa0:/data/wdocs/pwilliam/www-docs/miriad-python/"
set -x
scp -p index.html style.css $dest
cd ../BUILD*/doc && make push
