#!/usr/bin/env bash

nix-run -p cacert -p s3cmd -- ./build.py "$@"
