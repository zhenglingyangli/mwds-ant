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
set +e
python3 ../analysis/end/check_results.py --result "$RESULT" --output "$OUTPUT" --strict
STRICT_STATUS=$?
set -e
python3 ../analysis/end/audit_stage1_failures.py --result "$RESULT" --output ../analysis/end/stage1_failure_audit.md
python3 ../analysis/end/validate_stage1_holdout.py --result "$RESULT" --output ../analysis/end/stage1_holdout_validation.md
python3 ../analysis/end/choose_learning_form.py --result "$RESULT" --output ../analysis/end/stage1_learning_form_decision.md
echo "Done. See $OUTPUT"
exit "$STRICT_STATUS"
