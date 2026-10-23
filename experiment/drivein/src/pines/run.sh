#!/bin/bash
# Build + preview helper for the PINES thread, one lock acquisition.
# usage: run.sh "<python build cmd, run in src/pines>" "<harness query>|<outname>" ...
S=/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad
D=/home/claude/walkermotionpictures/experiment/drivein
build="$1"; shift
flock $S/heavy.lock bash -c "
cd $D/src/pines && $build 2>&1 | grep -vE 'INFO|Draco|MeshOptimizer|Vertex Color|tex image used|^\$'
cd $D
for spec in $(printf '%q ' "$@"); do
  q=\${spec%%|*}; o=\${spec##*|}
  timeout 280 python3 src/shot.py \"\$q\" $S/drivein_pines/\$o.png 900 1000
done
"
echo DONE
