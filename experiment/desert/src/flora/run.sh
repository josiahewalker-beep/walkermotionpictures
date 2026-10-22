#!/bin/bash
# Build + preview helper for the FLORA thread. usage: run.sh "<python build cmd>" "<query>|<outname>" ...
# Everything runs under the shared CPU lock in one acquisition.
S=/tmp/claude-0/-home-claude/8b2a0eb3-2d3d-5e5c-92b3-95ba17d9a3e1/scratchpad
D=/home/claude/walkermotionpictures/experiment/desert
build="$1"; shift
flock $S/heavy.lock bash -c "
cd $D/src/flora && $build 2>&1 | grep -vE 'INFO|Draco|MeshOptimizer|^\$'
cd $D
for spec in $(printf '%q ' "$@"); do
  q=\${spec%%|*}; o=\${spec##*|}
  timeout 280 python3 src/shot.py \"\$q\" $S/flora/\$o.png 1200 800
done
"
echo DONE
