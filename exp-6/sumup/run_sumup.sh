#!/bin/bash
# exp-6 selection analysis: run the dedicated multi-solver sumup.
#
# Usage:
#   cd exp-6/sumup
#   bash run_sumup.sh

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

RESULT=../jobs/result
OUTPUT=./analysis

if [ ! -d "$RESULT" ]; then
    echo "ERROR: $RESULT not found; run jobs first."
    exit 1
fi

mkdir -p "$OUTPUT"
echo "$(date): Running exp-6 sumup on $RESULT -> $OUTPUT"
python3 sumup.py "$RESULT" --output_dir "$OUTPUT"
echo
echo "=== Selection report: $OUTPUT/selection_report.md ==="
echo "Check sections '3. Ranking per Family' and '4. Selection Recommendation'."
