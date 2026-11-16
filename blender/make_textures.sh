#!/bin/bash
# Paints every part's label / poster / cover sheets into blender/parts/<part>/tex/ (needed before any build).
set -e
cd "$(dirname "$0")"
for p in shell counter shelves hifi nook lounge; do
  echo "== $p"; mkdir -p parts/$p/tex; python3 parts/$p/tex.py
done
