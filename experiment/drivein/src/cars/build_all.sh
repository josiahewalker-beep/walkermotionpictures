#!/bin/sh
# Rebuild all drive-in cars (run under the shared lock). ~20-40 s each on 2 cores.
cd "$(dirname "$0")"
for c in hero wagon sedan_a suv sedan_b; do python3 $c.py || exit 1; done
python3 speaker_post.py
