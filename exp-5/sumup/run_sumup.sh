#!/bin/bash
# exp-5 analysis reuses exp-2's sumup.py (dual-fast vs fast-v19 is exactly the
# comparison it was built for). Only the input data (result/) differs.
#
# Usage:
#   cd exp-5/sumup
#   bash run_sumup.sh                 # analysis/ is created here
#   # or in the background for big result sets:
#   nohup bash run_sumup.sh > sumup_run.log 2>&1 &

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

SUMUP=../../exp-2/sumup/sumup.py
RESULT=../jobs/result
OUTPUT=./analysis

if [ ! -f "$SUMUP" ]; then
    echo "ERROR: $SUMUP not found. Did you git pull the full repo?"
    exit 1
fi
if [ ! -d "$RESULT" ]; then
    echo "ERROR: $RESULT does not exist. Generate & run jobs first."
    exit 1
fi

mkdir -p "$OUTPUT"
echo "$(date): Running $SUMUP on $RESULT -> $OUTPUT"
python3 "$SUMUP" "$RESULT" --output_dir "$OUTPUT"
echo "$(date): Done. See $OUTPUT/exp2_report.md (and CSVs)."
