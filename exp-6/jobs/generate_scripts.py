#!/usr/bin/env python3
"""
Generate SLURM job scripts for MWDS exp-6: alpha=90 selection rerun.

Purpose: re-verify at the paper's alpha=90 which modified version actually
wins. exp-1 / exp-3 selected v19 / v6 under the wrong alpha=1 regime, where
the modifications' ALPHA-dependent multipliers make cross-version rankings
unreliable.

Config: 9 solvers × 90 T1 instances (every 6th, sorted) × 2 seeds, 30s cutoff.
Produces 9 × 1 chunk × 2 seeds = 18 jobs (very light, ~1.4 CPU-hours).

Usage:
    python3 generate_scripts.py                       # default: 2 seeds, T1 half
    python3 generate_scripts.py --seeds 1,2,3         # override seeds
    python3 generate_scripts.py --solvers fast-v19,fast-v28  # subset of versions
"""

import os
import math
import argparse
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

WCLQ_ROOT = "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq"

# All 9 contenders. "name" is the tag used in result dir / slurm job names.
# "dir" is the source-code directory (relative to the MWDS-Ant repo root).
# "bin" is the compiled binary filename.
SOLVERS = [
    # Fast family (6). bin names are what `make` produces in each dir.
    {"name": "dual-fast",       "family": "fast", "dir": "exp-1/codes/Dual-Fast",       "bin": "dual-fast"},
    {"name": "fast-v19",        "family": "fast", "dir": "exp-1/codes/Dual-Fast-v19",   "bin": "dual-fast-v19"},
    {"name": "fast-v28",        "family": "fast", "dir": "exp-1/codes/Dual-Fast-v28",   "bin": "dual-fast-v28"},
    {"name": "fast-freqscore",  "family": "fast", "dir": "exp-1/codes/Exp5-FreqScore",  "bin": "exp5-freqscore"},
    {"name": "fast-poolrelink", "family": "fast", "dir": "exp-1/codes/Exp6-PoolRelink", "bin": "exp6-poolrelink"},
    {"name": "fast-pool",       "family": "fast", "dir": "exp-1/codes/Exp9-Freq-Pool",  "bin": "exp9-freq-pool"},
    # Deep family (3)
    {"name": "dual-deep",       "family": "deep", "dir": "exp-1/codes/Dual-Deep",       "bin": "dual-deep"},
    {"name": "deep-v6",         "family": "deep", "dir": "exp-1/codes/Dual-Deep-v6",    "bin": "dual-deep-v6"},
    {"name": "deep-v10",        "family": "deep", "dir": "exp-3/codes/Dual-Deep-v10",   "bin": "dual-deep-v10"},
]

DATASETS = {
    # Only T1 (1/6 subsample) in exp-6; exp-4/5 cover full T1+T2 with the winner.
    "T1": {"path": f"{WCLQ_ROOT}/T1_wclq", "n_full": 540},
}

DEFAULT_SEEDS = [1, 2]
CUTOFF      = 30                      # seconds -- T1 at alpha=90 plateaus well before 30s
ALPHA       = 90                      # <-- the whole point of exp-6
PARALLEL    = 10                      # concurrent instances within a single SLURM job
GO_TIMEOUT  = CUTOFF + 60
CHUNK_SIZE  = 90                      # single chunk per (solver, seed)
CUTOFF_MEM  = 16                      # GB per-instance

SUBSET_STEP = 6                       # take every 6th sorted filename -> 90 of 540

SLURM_PARTITION = "hfacnormal01"
SLURM_MEM       = "64G"
SLURM_TIME      = "0-00:30:00"        # 30s*90/10 = 4.5min worst per job; 30min plenty

# ============================================================
# Templates
# ============================================================

SLURM_HEADER = """#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --time={time}
#SBATCH --output=slurm-%j.out
#SBATCH --mem={mem}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={cpus}
echo "-----------------------------------------------------------"
echo "hostname       = $(hostname)"
echo "SLURM_JOBID    = $SLURM_JOBID"
echo "-----------------------------------------------------------"

cd "$SLURM_SUBMIT_DIR"

"""

CHUNK_BLOCK = """
# --- Build filtered name_list: every {subset_step}-th sorted instance, chunk {chunk_id} ---
DATASET_DIR="{ds_path}"
CHUNK_ID={chunk_id}
CHUNK_SIZE={chunk_size}
SUBSET_STEP={subset_step}

# Take every SUBSET_STEP-th file (indices 0,6,12,... -> 90 of 540 for T1)
SUBSET_FILES=($(ls "$DATASET_DIR"/*.wclq 2>/dev/null | sort | xargs -n1 basename \\
    | awk -v step=$SUBSET_STEP 'NR % step == 1'))
TOTAL=${{#SUBSET_FILES[@]}}

START=$((CHUNK_ID * CHUNK_SIZE))
END=$(( (CHUNK_ID + 1) * CHUNK_SIZE ))
if [ $END -gt $TOTAL ]; then END=$TOTAL; fi
if [ $START -ge $TOTAL ]; then
    echo "Chunk $CHUNK_ID is beyond subset size ($TOTAL). Exiting."
    exit 0
fi

NAMELIST="namelist-{tag}.txt"
printf '%s\\n' "${{SUBSET_FILES[@]:START:END-START}}" > "$NAMELIST"
N_INST=$((END - START))
echo "Chunk $CHUNK_ID: instances $((START+1))..$END / $TOTAL subset-size ($N_INST instances, from 540-full)"

python3 ./goSolver.py {parallel} {go_timeout} \\
    {solver_bin} "$DATASET_DIR" ./result \\
    --cutoff_mem {cutoff_mem} \\
    --name_list "$NAMELIST" \\
    --suffix {suffix} \\
    {cutoff} {seed} {alpha}

rm -f "$NAMELIST"
echo "=== DONE: {suffix} ==="
"""


def parse_seeds(s):
    seeds = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))
    return sorted(set(seeds))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=parse_seeds, default=DEFAULT_SEEDS,
                    help="Seeds (e.g. '1,2'). Default: 1,2")
    ap.add_argument("--solvers", type=lambda s: [x.strip() for x in s.split(",")],
                    default=[s["name"] for s in SOLVERS],
                    help="Solver names to include (comma-separated). Default: all 9")
    ap.add_argument("--families", type=lambda s: [x.strip() for x in s.split(",")],
                    default=None,
                    help="Only include these families ('fast' and/or 'deep'). Default: both")
    args = ap.parse_args()

    active = [s for s in SOLVERS if s["name"] in args.solvers]
    if args.families:
        active = [s for s in active if s["family"] in args.families]
    if not active:
        raise SystemExit(f"No solvers matched. Known: {[s['name'] for s in SOLVERS]}")

    n_subset = math.ceil(DATASETS["T1"]["n_full"] / SUBSET_STEP)
    n_chunks = math.ceil(n_subset / CHUNK_SIZE)

    print("=" * 70)
    print(f"exp-6: alpha=90 selection rerun")
    print(f"  Solvers ({len(active)}): {[s['name'] for s in active]}")
    print(f"  Dataset : T1 (every {SUBSET_STEP}-nd of 540 sorted = {n_subset} instances)")
    print(f"  Seeds   : {args.seeds}")
    print(f"  Cutoff  : {CUTOFF}s    Alpha: {ALPHA} (ALPHA=1.{ALPHA:02d})    "
          f"Mem cap: {CUTOFF_MEM}GB/inst")
    print(f"  Chunks  : {n_chunks}  ({CHUNK_SIZE} inst / chunk)")
    print("=" * 70)

    generated = []
    total_hours = 0

    ds_name = "T1"
    ds_info = DATASETS[ds_name]
    ds_path = ds_info["path"]

    for slv in active:
        solver_bin = f"../../{slv['dir']}/{slv['bin']}"

        for seed in args.seeds:
            for chunk_id in range(n_chunks):
                actual_size = min(CHUNK_SIZE, n_subset - chunk_id * CHUNK_SIZE)
                tag = f"{slv['name']}-{ds_name}-c{chunk_id}-s{seed}"
                job_name = f"s6_{slv['name']}_s{seed}"
                script_file = f"jobslurm-{tag}"

                chunk_cmd = CHUNK_BLOCK.format(
                    chunk_id=chunk_id,
                    ds_path=ds_path,
                    chunk_size=CHUNK_SIZE,
                    subset_step=SUBSET_STEP,
                    tag=tag,
                    parallel=PARALLEL,
                    go_timeout=GO_TIMEOUT,
                    solver_bin=solver_bin,
                    suffix=tag,
                    cutoff=CUTOFF,
                    seed=seed,
                    alpha=ALPHA,
                    cutoff_mem=CUTOFF_MEM,
                )

                content = SLURM_HEADER.format(
                    job_name=job_name,
                    partition=SLURM_PARTITION,
                    time=SLURM_TIME,
                    mem=SLURM_MEM,
                    cpus=PARALLEL,
                ) + chunk_cmd

                with open(script_file, "w") as f:
                    f.write(content)
                os.chmod(script_file, 0o755)
                generated.append(script_file)

                total_hours += actual_size * CUTOFF / PARALLEL / 3600

    with open("submit_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# exp-6: {len(generated)} jobs (< 200 cluster limit, submit directly)\n\n")
        for s in sorted(generated):
            f.write(f"sbatch {s}\nsleep 0.5\n")
        f.write(f"\necho '=== {len(generated)} jobs submitted ==='\n")
    os.chmod("submit_all.sh", 0o755)

    print(f"Generated : {len(generated)} SLURM scripts")
    print(f"CPU-hours : {total_hours:.1f}")
    print(f"Max job walltime: {CHUNK_SIZE * CUTOFF / PARALLEL / 60:.0f} min")
    print(f"Submit : bash submit_all.sh")


if __name__ == "__main__":
    main()
