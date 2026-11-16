#!/bin/bash
# Full rebuild of the 3D assets:  assemble -> bake every atlas -> denoise + textures -> ../site/bar.glb + scene.json
# usage: blender/bake_all.sh [--test]     (--test = quick low-resolution bake, ~2 minutes)
set -e
cd "$(dirname "$0")"
export BAR_THREADS=${BAR_THREADS:-$(python3 -c "import os;print(os.cpu_count())")}
python3 barkit/run.py assemble | grep -E "PART|ATLAS|ASSEMBLED"
ATS=$(python3 -c "import json;print(' '.join(json.load(open('out/assemble.json'))['atlases']))")
for a in $ATS; do python3 barkit/run.py bake $a $1 | grep -E "BAKED"; done
python3 barkit/run.py post | grep POST
python3 barkit/run.py export | grep -E "GLB|EXPORTED"
