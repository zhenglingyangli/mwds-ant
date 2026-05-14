#!/bin/bash
# Submit small diagnostic jobs for exp-8 timeout-only outputs.
#
# Usage on the cluster:
#   bash exp-8/diagnose_timeout_capture.sh          # generate + submit diagnostics
#   bash exp-8/diagnose_timeout_capture.sh --check  # classify diagnostic outputs
#
# Optional overrides:
#   DIAG_SOLVER_CUTOFF=780 DIAG_GO_TIMEOUT=900 bash exp-8/diagnose_timeout_capture.sh

set -euo pipefail

MODE="${1:-submit}"
if [ "$MODE" = "--check" ]; then
  MODE="check"
elif [ "$MODE" != "submit" ]; then
  echo "Usage: bash exp-8/diagnose_timeout_capture.sh [--check]"
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

DIAG_ROOT="$SCRIPT_DIR/diagnostics/timeout_capture"
JOB_DIR="$DIAG_ROOT/jobs"
RESULT_ROOT="$DIAG_ROOT/result"
NAME_DIR="$DIAG_ROOT/namelists"

DIAG_SOLVER_CUTOFF="${DIAG_SOLVER_CUTOFF:-780}"
DIAG_GO_TIMEOUT="${DIAG_GO_TIMEOUT:-900}"
SLURM_PARTITION="${SLURM_PARTITION:-hfacnormal01}"
SLURM_MEM="${SLURM_MEM:-64G}"
SLURM_TIME="${SLURM_TIME:-0-00:20:00}"

mkdir -p "$JOB_DIR" "$RESULT_ROOT" "$NAME_DIR"

check_mode() {
  python3 - <<'PY'
import re
from pathlib import Path

root = Path("diagnostics/timeout_capture/result")
files = sorted(root.glob("**/*.out"))
if not files:
    print("No diagnostic .out files found yet.")
    raise SystemExit(1)

round_re = re.compile(r"^\s*\d+\s+-?\d+\s+-?\d+\s+-?\d+\s+[\d.]+")

summary = {"summary": 0, "round_only": 0, "banner_only": 0, "timeout_only": 0, "other": 0}
print(f"diagnostic files: {len(files)}")
for p in files:
    text = p.read_text(errors="replace")
    lines = text.splitlines()
    has_summary = "|V|" in text and "#LB" in text and "#UB" in text
    has_round = any(round_re.match(line) for line in lines)
    has_banner = any(token in text for token in (">>IBM", "[v6]", "[v19]", "#Rd", "First Gap"))
    has_timeout = "Status TIMEOUT" in text or "out_of_time" in text

    if has_summary:
        kind = "summary"
    elif has_round:
        kind = "round_only"
    elif has_banner:
        kind = "banner_only"
    elif has_timeout:
        kind = "timeout_only"
    else:
        kind = "other"
    summary[kind] += 1

    print(f"\n[{kind}] {p}")
    print(f"  lines={len(lines)} bytes={p.stat().st_size}")
    if lines:
        print(f"  first: {lines[0][:180]}")
        print(f"  last : {lines[-1][:180]}")

print("\nsummary:")
for key in ("summary", "round_only", "banner_only", "timeout_only", "other"):
    print(f"  {key}: {summary[key]}")

if summary["timeout_only"]:
    print("\nInterpretation:")
    print("  timeout_only means goSolver killed the process before any useful solver stdout was captured.")
    print("  If these jobs used the current goSolver.py with stdbuf, the instance likely does not emit an LB trace within the diagnostic window.")
else:
    print("\nInterpretation:")
    print("  Solver stdout is being captured. Full patch reruns should preserve LB traces when the solver prints them before timeout.")
PY
}

if [ "$MODE" = "check" ]; then
  check_mode
  exit 0
fi

echo "=== exp-8 timeout capture diagnostics ==="
echo "exp root          : $SCRIPT_DIR"
echo "diagnostic root   : $DIAG_ROOT"
echo "solver cutoff     : $DIAG_SOLVER_CUTOFF"
echo "goSolver timeout  : $DIAG_GO_TIMEOUT"

if ! grep -q "stdbuf" deep-v6/jobs/goSolver.py || ! grep -q "stdbuf" fast-v19/jobs/goSolver.py; then
  echo "ERROR: goSolver.py does not contain the stdbuf line-buffering fix. Pull latest main first."
  exit 2
fi

python3 -m json.tool dataset_manifest.json >/tmp/exp8_diag_manifest.json

make -C deep-v6/codes/Dual-Deep-v6
make -C fast-v19/codes/Dual-Fast-v19

cat > "$NAME_DIR/deep-dimacs10.txt" <<'EOF'
eu-2005.clq
EOF
cat > "$NAME_DIR/deep-ndr.txt" <<'EOF'
tech-ip.clq
EOF
cat > "$NAME_DIR/fast-dimacs10.txt" <<'EOF'
in-2004.clq
EOF
cat > "$NAME_DIR/fast-ndr.txt" <<'EOF'
inf-roadNet-CA.clq
EOF

write_job() {
  local job_name="$1"
  local work_dir="$2"
  local solver="$3"
  local data_dir="$4"
  local result_dir="$5"
  local name_list="$6"
  local suffix="$7"
  local seed="$8"
  local script="$JOB_DIR/jobslurm-$job_name"

  cat > "$script" <<EOF
#!/bin/sh
#SBATCH --job-name=$job_name
#SBATCH --partition=$SLURM_PARTITION
#SBATCH --time=$SLURM_TIME
#SBATCH --output=$JOB_DIR/slurm-%j-$job_name.out
#SBATCH --mem=$SLURM_MEM
#SBATCH --nodes=1
#SBATCH --cpus-per-task=1
set -e
cd "$work_dir"
python3 ./goSolver.py 1 $DIAG_GO_TIMEOUT \\
  "$solver" "$data_dir" "$result_dir" \\
  --cutoff_mem 16 \\
  --name_list "$name_list" \\
  --suffix "$suffix" \\
  $DIAG_SOLVER_CUTOFF $seed 90
EOF
  chmod +x "$script"
  echo "$script"
}

DEEP_BIN="$SCRIPT_DIR/deep-v6/codes/Dual-Deep-v6/dual-deep-v6"
FAST_BIN="$SCRIPT_DIR/fast-v19/codes/Dual-Fast-v19/dual-fast-v19"
DIMACS10_DIR="/public/home/acs4vb4pqv/benchmarks/MWDS2026/DIMACS10"
NDR_ROOT="/public/home/acs4vb4pqv/benchmarks/MWDS2026"

scripts=()
scripts+=("$(write_job diag-deep-dimacs10 "$SCRIPT_DIR/deep-v6/jobs" "$DEEP_BIN" "$DIMACS10_DIR" "$RESULT_ROOT/deep-v6" "$NAME_DIR/deep-dimacs10.txt" diag-deep-dimacs10-s2 2)")
scripts+=("$(write_job diag-deep-ndr "$SCRIPT_DIR/deep-v6/jobs" "$DEEP_BIN" "$NDR_ROOT" "$RESULT_ROOT/deep-v6" "$NAME_DIR/deep-ndr.txt" diag-deep-ndr-s1 1)")
scripts+=("$(write_job diag-fast-dimacs10 "$SCRIPT_DIR/fast-v19/jobs" "$FAST_BIN" "$DIMACS10_DIR" "$RESULT_ROOT/fast-v19" "$NAME_DIR/fast-dimacs10.txt" diag-fast-dimacs10-s1 1)")
scripts+=("$(write_job diag-fast-ndr "$SCRIPT_DIR/fast-v19/jobs" "$FAST_BIN" "$NDR_ROOT" "$RESULT_ROOT/fast-v19" "$NAME_DIR/fast-ndr.txt" diag-fast-ndr-s1 1)")

echo
echo "Submitting ${#scripts[@]} diagnostic jobs..."
for script in "${scripts[@]}"; do
  sbatch "$script"
  sleep 0.5
done

echo
echo "After these jobs finish, run:"
echo "  cd $SCRIPT_DIR"
echo "  bash diagnose_timeout_capture.sh --check"
