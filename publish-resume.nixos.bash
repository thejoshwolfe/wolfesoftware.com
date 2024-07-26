#!/usr/bin/env bash

if [ resume/index.html -nt resume/Josh_Wolfe_resume.pdf ]; then
    echo 'ERROR: it looks like you forgot to update Josh_Wolfe_resume.pdf' >&2; exit 1
fi
exit 0
nix-run -p cacert -p s3cmd -- s3cmd sync -P --no-preserve --add-header='Cache-Control: max-age=0, must-revalidate' resume/ s3://wolfesoftware.com/resume/
