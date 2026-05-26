#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RESULT=${RESULT:-result}
OUTPUT=${OUTPUT:-../analysis/end/strict_check_report.md}

if [ ! -d "$RESULT" ]; then
  echo "ERROR: $RESULT does not exist. Generate and run Stage-1 jobs first."
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
python3 ../analysis/end/check_results.py --result "$RESULT" --output "$OUTPUT" --strict
echo "Done. See $OUTPUT"
