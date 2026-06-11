#!/usr/bin/env bash
# Unpack balanced40 package after pulling split chunks from GitHub.
#
# Usage on local machine:
#   cd /home/ylzl/1-MWDS/WMDS26
#   bash exp-8/unpack_balanced40_local.sh
#
# Optional target override:
#   BAL40_TARGET=/some/path bash exp-8/unpack_balanced40_local.sh

set -euo pipefail

EXP8="$(cd "$(dirname "$0")" && pwd)"
PKG="$EXP8/balanced40_package"
TARGET="${BAL40_TARGET:-/home/ylzl/2-MWDS/2-2-codes/2-2-8-balanced40}"
DATA="$TARGET/data"

echo "============================================================"
echo "Unpack balanced40 data"
echo "  package: $PKG"
echo "  target : $TARGET"
echo "============================================================"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing command: $1" >&2
    exit 2
  }
}

require_cmd sha256sum
require_cmd tar
require_cmd python3

if [ ! -d "$PKG" ]; then
  echo "ERROR: package directory not found: $PKG" >&2
  exit 2
fi

first_part="$(ls "$PKG"/balanced40_data_*.tar.gz.part-000 2>/dev/null | sort | tail -n 1 || true)"
if [ -z "$first_part" ]; then
  echo "ERROR: no split package found under $PKG" >&2
  echo "Expected files like balanced40_data_YYYYmmdd_HHMMSS.tar.gz.part-000" >&2
  exit 2
fi

base="${first_part%.part-000}"
archive="$base"

echo "Using package base: $(basename "$base")"

if [ -f "$base.parts.sha256" ]; then
  echo "Checking part checksums..."
  (cd "$PKG" && sha256sum -c "$(basename "$base.parts.sha256")")
fi

echo "Merging split parts..."
cat "$base".part-* > "$archive"

if [ -f "$archive.sha256" ]; then
  echo "Checking archive checksum..."
  (cd "$PKG" && sha256sum -c "$(basename "$archive.sha256")")
fi

mkdir -p "$TARGET"
echo "Extracting to $TARGET"
tar -C "$TARGET" -xzf "$archive"

echo
echo "Running local check..."
if [ -f "$TARGET/scripts/check_local.py" ]; then
  python3 "$TARGET/scripts/check_local.py"
else
  count="$(find "$DATA" -type f | wc -l)"
  echo "present files under $DATA: $count"
fi

