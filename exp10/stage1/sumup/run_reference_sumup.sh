#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SELECTED_RESULT=${SELECTED_RESULT:-result/v006}
REFERENCE_RESULT=${REFERENCE_RESULT:-reference_result}
OUTPUT=${OUTPUT:-../analysis/end/reference_check_report.md}

if [ ! -d "$SELECTED_RESULT" ]; then
  echo "ERROR: $SELECTED_RESULT does not exist. Run or copy the selected v006 result first."
  exit 1
fi

if [ ! -d "$REFERENCE_RESULT" ]; then
  echo "ERROR: $REFERENCE_RESULT does not exist. Run the Stage-1 reference jobs first."
  exit 1
fi

mkdir -p "$(dirname "$OUTPUT")"
python3 ../analysis/end/check_reference_results.py \
  --selected-result "$SELECTED_RESULT" \
  --reference-result "$REFERENCE_RESULT" \
  --output "$OUTPUT" \
  --strict
echo "Done. See $OUTPUT"
