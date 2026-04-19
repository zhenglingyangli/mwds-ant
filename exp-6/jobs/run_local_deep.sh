#!/bin/bash
# =============================================================================
# Local quick test: deep-v6 vs deep-v10 at 300s, same 90 T1 subset as exp-6.
#
# Purpose: exp-6 (30s, 2 seeds, alpha=90) showed v10 beats v6 by +7 net wins
# on 90 instances -- noise-level signal. Rerun with 300s cutoff at alpha=90 to
# see if the v10 > v6 ranking holds when each instance is given enough time.
#
# Config:
#   2 solvers (deep-v6, deep-v10)
#   90 T1 instances (every 6th sorted -- identical to exp-6 subset)
#   1 seed
#   300s cutoff
#   10 parallel workers within a single invocation
#   --> ~1.5h wall time
#
# Usage:
#   cd WMDS26/exp-6/jobs
#   bash run_local_deep.sh
# =============================================================================

set -e

# -------- Config --------
DATASET_DIR="/home/ylzl/Ant-QO/Supplementary Material 1379/Supplementary Material 1379/Datasets/T1_wclq"
CUTOFF=300
ALPHA=90
PARALLEL=10
GO_TIMEOUT=$((CUTOFF + 60))
CUTOFF_MEM=16
SUBSET_STEP=6
SEED=1

SOLVERS=("deep-v6" "deep-v10")
declare -A DIRS=(
    [deep-v6]="exp-1/codes/Dual-Deep-v6"
    [deep-v10]="exp-3/codes/Dual-Deep-v10"
)
declare -A BINS=(
    [deep-v6]="dual-deep-v6"
    [deep-v10]="dual-deep-v10"
)

REPO_ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
JOBS_DIR="$(cd "$(dirname "$0")" && pwd)"
RESULT_DIR="$JOBS_DIR/result_local_deep"
NAMELIST_FILE="$JOBS_DIR/namelist-local-deep.txt"

mkdir -p "$RESULT_DIR"

# -------- Sanity --------
if [ ! -d "$DATASET_DIR" ]; then
    echo "ERROR: dataset dir not found: $DATASET_DIR" >&2
    exit 1
fi
if [ ! -f "$JOBS_DIR/goSolver.py" ]; then
    echo "ERROR: goSolver.py missing from $JOBS_DIR" >&2
    exit 1
fi

# -------- Build every-6th subset namelist (should pick same 90 graphs as exp-6,
# since both dataset dirs contain same 540 (V, E, i) combos and share sort order) --
ls "$DATASET_DIR"/*.wclq 2>/dev/null | sort | xargs -n1 basename \
    | awk -v step="$SUBSET_STEP" 'NR % step == 1' > "$NAMELIST_FILE"
N_INST=$(wc -l < "$NAMELIST_FILE")
echo "Subset: $N_INST instances from $DATASET_DIR"

# -------- Compile if missing --------
echo "=== Compiling missing binaries ==="
for s in "${SOLVERS[@]}"; do
    d="${DIRS[$s]}"; b="${BINS[$s]}"
    bin_path="$REPO_ROOT/$d/$b"
    if [ ! -x "$bin_path" ]; then
        echo "  -> make in $d"
        (cd "$REPO_ROOT/$d" && make) || { echo "FAILED to build $s" >&2; exit 1; }
    else
        echo "  -> $s already built"
    fi
done

# -------- Pre-flight --------
N_JOBS=${#SOLVERS[@]}
WALL_PER_JOB=$(( (N_INST * CUTOFF + PARALLEL - 1) / PARALLEL ))
WALL_TOTAL=$(( WALL_PER_JOB * N_JOBS ))
echo "======================================================================"
echo "Local deep comparison"
echo "  solvers   : ${SOLVERS[*]}"
echo "  seed      : $SEED   cutoff: ${CUTOFF}s   alpha: $ALPHA"
echo "  instances : $N_INST   parallel: $PARALLEL"
echo "  jobs      : $N_JOBS (sequential)"
echo "  wall est  : per-job ~$((WALL_PER_JOB / 60)) min, total ~$((WALL_TOTAL / 60)) min"
echo "  output    : $RESULT_DIR"
echo "======================================================================"
echo "Starting in 5s... (Ctrl+C to abort)"
sleep 5

# -------- Run --------
START=$(date +%s)
JOB_IDX=0
for s in "${SOLVERS[@]}"; do
    d="${DIRS[$s]}"; b="${BINS[$s]}"
    bin_path="$REPO_ROOT/$d/$b"
    JOB_IDX=$((JOB_IDX + 1))
    SUFFIX="${s}-T1-c0-s${SEED}"
    echo ""
    echo ">>> [$JOB_IDX/$N_JOBS] $s  seed=$SEED  ($(date +%T))"
    cd "$JOBS_DIR"
    python3 ./goSolver.py "$PARALLEL" "$GO_TIMEOUT" \
        "$bin_path" "$DATASET_DIR" "$RESULT_DIR" \
        --cutoff_mem "$CUTOFF_MEM" \
        --name_list "$NAMELIST_FILE" \
        --suffix "$SUFFIX" \
        "$CUTOFF" "$SEED" "$ALPHA"
done
ELAPSED=$(($(date +%s) - START))
echo ""
echo "=== ALL DONE: $JOB_IDX jobs in $((ELAPSED / 60))m $((ELAPSED % 60))s ==="
echo ""
echo "Next: run sumup"
echo "  cd $JOBS_DIR/../sumup"
echo "  python3 sumup.py ../jobs/result_local_deep --output_dir ../analysis_local_deep"
