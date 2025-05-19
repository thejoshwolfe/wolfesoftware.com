#!/usr/bin/env bash

(cd blog && ./compile.py)
./check_sidebar.py || exit 1
nix-run -p cacert -p s3cmd -- s3cmd sync -P --no-preserve --add-header='Cache-Control: max-age=0, must-revalidate' blog/ s3://wolfesoftware.com/blog/
nix-run -p cacert -p s3cmd -- s3cmd sync -P --no-preserve --add-header='Cache-Control: max-age=0, must-revalidate' index.html s3://wolfesoftware.com/index.html
