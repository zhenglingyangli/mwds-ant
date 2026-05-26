#!/bin/bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
STAGE1_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$SCRIPT_DIR"

TMP_ROOT="$SCRIPT_DIR/.smoke_tmp"
TMP_RESULT="$TMP_ROOT/result/vfixture"
rm -rf "$TMP_ROOT" jobslurm-* submit_all.sh
mkdir -p "$TMP_RESULT"
cp "$SCRIPT_DIR"/fixtures/*.csv "$TMP_RESULT"/

if [ -z "${PATH_MODE:-}" ]; then
  PATH_MODE=local
  if [ -d "/public/home/acs4vb4pqv/benchmarks/MWDS2026/T1_wclq" ]; then
    PATH_MODE=hpc
  fi
fi

python3 "$STAGE1_ROOT/analysis/end/check_results.py" \
  --result "$TMP_ROOT/result" \
  --output "$TMP_ROOT/smoke_strict_check_report.md" \
  --strict

python3 -m py_compile \
  "$STAGE1_ROOT/jobs/goSolver_stage1.py" \
  "$STAGE1_ROOT/jobs/generate_scripts.py" \
  "$STAGE1_ROOT/analysis/end/check_results.py"

if [ "${BUILD_CODE:-1}" = "1" ]; then
  make -C "$STAGE1_ROOT/code/deep/v005" >/dev/null
  make -C "$STAGE1_ROOT/code/fast/v005" >/dev/null
  test -x "$STAGE1_ROOT/code/deep/v005/dual-deep-v6"
  test -x "$STAGE1_ROOT/code/fast/v005/dual-fast-v19"
fi

mkdir -p "$TMP_ROOT/jobs"
cd "$TMP_ROOT/jobs"
python3 "$STAGE1_ROOT/jobs/generate_scripts.py" \
  --candidates v005 \
  --datasets T1 \
  --seeds 1 \
  --reps 1 \
  --cutoff 2 \
  --workers 20 \
  --path-mode "$PATH_MODE" \
  --candidate-root-base "$STAGE1_ROOT"

test -x jobslurm-v005
test -x submit_all.sh

if [ "${RUN_REAL_SOLVER:-1}" = "1" ]; then
  python3 "$STAGE1_ROOT/jobs/goSolver_stage1.py" \
    --candidate v005 \
    --candidate-root-base "$STAGE1_ROOT" \
    --datasets T1 \
    --seeds 1 \
    --reps 1 \
    --cutoff 2 \
    --workers 20 \
    --path-mode "$PATH_MODE" \
    --output-dir "$TMP_ROOT/real/v005"
  python3 - "$TMP_ROOT/real/v005/layer_a_runs.csv" <<'PY'
import csv
import sys

rows = list(csv.DictReader(open(sys.argv[1], newline="")))
if not rows:
    raise SystemExit("real smoke produced no rows")
bad = [r for r in rows if str(r.get("parse_ok")).lower() != "true" or r.get("exit_code") not in {"0", "0.0"}]
if bad:
    raise SystemExit(f"real smoke parse/exit failures: {len(bad)}")
print(f"[stage1-real-smoke] rows={len(rows)} parse_ok=all")
PY
fi

cd "$SCRIPT_DIR"
rm -rf "$TMP_ROOT" jobslurm-* submit_all.sh

echo "[stage1-smoke] ok"
