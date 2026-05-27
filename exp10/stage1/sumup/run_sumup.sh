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
if python3 - "$RESULT" <<'PY'
import csv
import sys
from pathlib import Path

root = Path(sys.argv[1])
dirs = [root] if (root / "layer_a_runs.csv").exists() else [p for p in root.iterdir() if p.is_dir()]
for path in dirs:
    runs = path / "layer_a_runs.csv"
    if not runs.exists():
        continue
    with runs.open(newline="") as handle:
        for row in csv.DictReader(handle):
            if row.get("arm"):
                raise SystemExit(0)
raise SystemExit(1)
PY
then
  echo "Detected randomized arm logging result; skipping paired strict gate."
  STRICT_STATUS=0
  python3 ../analysis/end/analyze_randomized_arms.py --result "$RESULT" --output ../analysis/end/stage1_randomized_arm_analysis.md
else
  set +e
  python3 ../analysis/end/check_results.py --result "$RESULT" --output "$OUTPUT" --strict
  STRICT_STATUS=$?
  set -e
  python3 ../analysis/end/audit_stage1_failures.py --result "$RESULT" --output ../analysis/end/stage1_failure_audit.md
  python3 ../analysis/end/validate_stage1_holdout.py --result "$RESULT" --output ../analysis/end/stage1_holdout_validation.md
fi
python3 ../analysis/end/choose_learning_form.py --result "$RESULT" --output ../analysis/end/stage1_learning_form_decision.md
echo "Done. See $OUTPUT"
exit "$STRICT_STATUS"
