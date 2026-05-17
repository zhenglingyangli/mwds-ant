#!/bin/bash
# Preflight and submit exp-9 on the cluster.
#
# Usage:
#   bash exp-9/run_on_hpc.sh              # preflight, smoke test, then ask before submit
#   bash exp-9/run_on_hpc.sh --no-submit  # only preflight + smoke + generate scripts
#   bash exp-9/run_on_hpc.sh --submit     # preflight + smoke + submit without prompt

set -euo pipefail

MODE="prompt"
if [ "${1:-}" = "--no-submit" ]; then
  MODE="no-submit"
elif [ "${1:-}" = "--submit" ]; then
  MODE="submit"
elif [ "${1:-}" != "" ]; then
  echo "Usage: bash exp-9/run_on_hpc.sh [--no-submit|--submit]"
  exit 2
fi

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$SCRIPT_DIR"

DATASETS=(T1 T2 UDG BHOSLIB DIMACS DIMACS10 NDR SNAP)
SMOKE_DATASETS=(T1 UDG BHOSLIB DIMACS)
SMOKE_CUTOFF=5
SMOKE_TIMEOUT=30

echo "=== exp-9 preflight ==="
echo "repo: $REPO_ROOT"
echo "exp : $SCRIPT_DIR"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1"
    exit 2
  fi
}

require_cmd python3
require_cmd find
require_cmd make
if [ "$MODE" != "no-submit" ]; then
  require_cmd sbatch
  require_cmd squeue
fi

echo
echo "=== 1) Validate manifest and selected lists ==="
python3 -m json.tool dataset_manifest.json >/tmp/exp9_dataset_manifest.checked.json

python3 - <<'PY'
import json
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "dataset_manifest.json").read_text())
datasets = ["T1", "T2", "UDG", "BHOSLIB", "DIMACS", "DIMACS10", "NDR", "SNAP"]

missing = []
for ds in datasets:
    path = manifest[ds]["hpc_path"]
    if path.startswith("TODO_CONFIRM"):
        missing.append(f"{ds}: path still unconfirmed ({path})")
    selected = root / "selected_instances" / f"{ds}.txt"
    names = [x.strip() for x in selected.read_text().splitlines() if x.strip()]
    if len(names) != 5:
        missing.append(f"{ds}: expected 5 selected instances, got {len(names)}")

if missing:
    print("ERROR: manifest/selection check failed:")
    for item in missing:
        print("  -", item)
    raise SystemExit(2)

print("manifest OK; selected instance lists all have 5 entries")
PY

echo
echo "=== 2) Check dataset directories and selected instance files ==="
python3 - <<'PY'
import json
import os
from pathlib import Path

root = Path.cwd()
manifest = json.loads((root / "dataset_manifest.json").read_text())
datasets = ["T1", "T2", "UDG", "BHOSLIB", "DIMACS", "DIMACS10", "NDR", "SNAP"]

failures = []
resolved = {}
for ds in datasets:
    base = Path(manifest[ds]["hpc_path"])
    if not base.is_dir():
        failures.append(f"{ds}: dataset directory does not exist: {base}")
        continue
    names = [x.strip() for x in (root / "selected_instances" / f"{ds}.txt").read_text().splitlines() if x.strip()]
    for name in names:
        matches = []
        # Use os.walk so NDR can be searched recursively from the MWDS2026 root.
        for cur, _dirs, files in os.walk(base):
            if name in files:
                matches.append(str(Path(cur) / name))
                break
        if not matches:
            failures.append(f"{ds}: selected instance not found under {base}: {name}")
        else:
            resolved[(ds, name)] = matches[0]

if failures:
    print("ERROR: dataset file check failed:")
    for item in failures:
        print("  -", item)
    raise SystemExit(2)

out = root / ".exp9_resolved_instances.tsv"
with out.open("w") as f:
    for (ds, name), path in sorted(resolved.items()):
        f.write(f"{ds}\t{name}\t{path}\n")

print(f"all selected instances found; wrote {out}")
PY

echo
echo "=== 3) Compile solvers ==="
make -C deep-v6/codes/Dual-Deep-v6
make -C fast-v19/codes/Dual-Fast-v19

DEEP_BIN="$SCRIPT_DIR/deep-v6/codes/Dual-Deep-v6/dual-deep-v6"
FAST_BIN="$SCRIPT_DIR/fast-v19/codes/Dual-Fast-v19/dual-fast-v19"

if [ ! -x "$DEEP_BIN" ]; then
  echo "ERROR: deep-v6 binary not found: $DEEP_BIN"
  exit 2
fi
if [ ! -x "$FAST_BIN" ]; then
  echo "ERROR: fast-v19 binary not found: $FAST_BIN"
  exit 2
fi

echo
echo "=== 4) Smoke test input formats ==="
python3 - <<'PY' >/tmp/exp9_smoke_instances.env
from pathlib import Path

root = Path.cwd()
wanted = ["T1", "UDG", "BHOSLIB", "DIMACS"]
resolved = {}
for line in (root / ".exp9_resolved_instances.tsv").read_text().splitlines():
    ds, name, path = line.split("\t")
    if ds in wanted and ds not in resolved:
        resolved[ds] = path
for ds in wanted:
    if ds not in resolved:
        raise SystemExit(f"missing smoke instance for {ds}")
    print(f"{ds}={resolved[ds]}")
PY

# shellcheck disable=SC1091
source /tmp/exp9_smoke_instances.env

run_smoke() {
  local solver_name="$1"
  local solver_bin="$2"
  local ds="$3"
  local inst="$4"
  echo "--- $solver_name / $ds / $(basename "$inst") ---"
  local out
  if ! out=$(timeout "${SMOKE_TIMEOUT}s" "$solver_bin" "$inst" "$SMOKE_CUTOFF" 1 90 2>&1); then
    echo "$out"
    echo "ERROR: smoke test failed or timed out for $solver_name on $ds"
    exit 2
  fi
  echo "$out" | grep -E ">>>|\\|V\\||maximum node weight|Warning" || true
  if ! echo "$out" | grep -q ">>> $(basename "$inst") "; then
    echo "ERROR: no final >>> summary from $solver_name on $ds"
    exit 2
  fi
  if echo "$out" | grep -q ">>> Warning: header edge_num"; then
    echo "ERROR: parser edge-count warning from $solver_name on $ds"
    exit 2
  fi
}

for ds in "${SMOKE_DATASETS[@]}"; do
  inst_var="${ds}"
  inst="${!inst_var}"
  run_smoke "deep-v6" "$DEEP_BIN" "$ds" "$inst"
  run_smoke "fast-v19" "$FAST_BIN" "$ds" "$inst"
done

echo
echo "=== 5) Generate SLURM scripts ==="
(
  cd deep-v6/jobs
  rm -f jobslurm-* submit_all.sh
  python3 generate_scripts.py
  n=$(ls jobslurm-* 2>/dev/null | wc -l)
  echo "deep-v6 scripts: $n"
  [ "$n" -eq 40 ] || { echo "ERROR: expected 40 deep-v6 scripts"; exit 2; }
)
(
  cd fast-v19/jobs
  rm -f jobslurm-* submit_all.sh
  python3 generate_scripts.py
  n=$(ls jobslurm-* 2>/dev/null | wc -l)
  echo "fast-v19 scripts: $n"
  [ "$n" -eq 40 ] || { echo "ERROR: expected 40 fast-v19 scripts"; exit 2; }
)

echo
echo "=== Preflight PASS ==="
echo "Generated 80 SLURM scripts total (40 deep-v6 + 40 fast-v19)."

if [ "$MODE" = "no-submit" ]; then
  echo "Mode --no-submit: stopping before submission."
  exit 0
fi

if [ "$MODE" = "prompt" ]; then
  echo
  echo "Type RUN to start full exp-9 submission now."
  read -r answer
  if [ "$answer" != "RUN" ]; then
    echo "Submission cancelled. You can later run:"
    echo "  cd $SCRIPT_DIR/deep-v6/jobs && nohup bash auto_submit.sh > auto_submit.log 2>&1 &"
    echo "  cd $SCRIPT_DIR/fast-v19/jobs && nohup bash auto_submit.sh > auto_submit.log 2>&1 &"
    exit 0
  fi
fi

echo
echo "=== 6) Submit jobs ==="
(
  cd deep-v6/jobs
  nohup bash auto_submit.sh > auto_submit.log 2>&1 &
  echo "deep-v6 auto_submit PID: $!"
)
(
  cd fast-v19/jobs
  nohup bash auto_submit.sh > auto_submit.log 2>&1 &
  echo "fast-v19 auto_submit PID: $!"
)

echo "Submission started."
echo "Monitor:"
echo "  squeue -u \$USER -h | wc -l"
echo "  tail -f $SCRIPT_DIR/deep-v6/jobs/auto_submit.log"
echo "  tail -f $SCRIPT_DIR/fast-v19/jobs/auto_submit.log"
