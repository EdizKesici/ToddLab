#!/usr/bin/env bash
# Sync the backend distribution payload (<repo>/data/dist) into the frontend copy (frontend/data/dist).
# Usage: scripts/sync-data.sh [SOURCE_DIR]   (default: ../data/dist, the backend at the repo root)
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$(cd "${1:-$SCRIPT_DIR/../../data/dist}" && pwd)"
DST="$SCRIPT_DIR/../data/dist"

# Refuse to wipe the destination unless the source looks like a real payload.
for f in catalog.json entities.json todd_corpus.json; do
  [ -f "$SRC/$f" ] || { echo "Source $SRC is missing $f, aborting (nothing changed)." >&2; exit 1; }
done

rm -rf "$DST"
mkdir -p "$DST"
# Copy the CONTENTS of SRC (cp -r SRC DST would nest when DST already exists).
cp -r "$SRC"/. "$DST"/
echo "Synced $SRC -> $(cd "$DST" && pwd)"
