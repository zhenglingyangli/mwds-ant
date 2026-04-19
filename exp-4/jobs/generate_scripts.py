#!/usr/bin/env python3
"""
Generate SLURM job scripts for MWDS Dual-Deep v6 vs baseline experiment (exp-4).

Matches the paper's setup: 3600s cutoff, 10 seeds.
Large datasets are split into chunks (~55 instances each) for efficient scheduling.
Each SLURM job = 1 chunk × 1 seed, using goSolver.py --name_list for instance selection.

Usage:
    # Full run (all 10 seeds):
    python3 generate_scripts.py

    # Stage 1: pilot run with only 2 seeds
    python3 generate_scripts.py --seeds 1,2

    # Stage 2: fill in the remaining 8 seeds (old result-* dirs are reused by sumup)
    python3 generate_scripts.py --seeds 3,4,5,6,7,8,9,10

    # Only T1 (skip T2)
    python3 generate_scripts.py --datasets T1
"""

import os
import math
import argparse
from pathlib import Path

# ============================================================
# Configuration (DO NOT change between incremental runs!)
# Any change invalidates cross-seed comparability.
# ============================================================

SOLVERS = [
    {"name": "dual-deep", "dir": "Dual-Deep",     "bin": "dual-deep"},
    {"name": "deep-v6",   "dir": "Dual-Deep-v6",  "bin": "dual-deep-v6"},
]

WCLQ_ROOT = "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq"

DATASETS = {
    "T1": {"path": f"{WCLQ_ROOT}/T1_wclq", "n": 540},
    "T2": {"path": f"{WCLQ_ROOT}/T2_wclq", "n": 540},
}

DEFAULT_SEEDS = [1, 2]                # 2 seeds (paper used 10; deliberate deviation for wall-time)
CUTOFF     = 3600                     # seconds (paper setting)
# alpha is the CLI arg (argv[4]); solver converts to internal ALPHA = 1 + alpha/100.
# Paper / all original run_goSolver.sh use alpha=90 -> internal ALPHA=1.90.
# DO NOT change to 1 (=> ALPHA=1.01) -- that silently makes the per-round
# expansion rate 1% instead of 90%, which is a totally different algorithm regime
# and will NOT reproduce the paper's baseline numbers.
ALPHA      = 90
PARALLEL   = 10
GO_TIMEOUT = CUTOFF + 120             # goSolver safety timeout
CHUNK_SIZE = 55                       # instances per SLURM job
CUTOFF_MEM = 16                       # per-instance memory cap in GB (matches paper's exp-1)

SLURM_PARTITION = "hfacnormal01"
SLURM_MEM       = "64G"                # SLURM job-level cap; PARALLEL*CUTOFF_MEM=160GB headroom
SLURM_TIME      = "0-08:00:00"

# ============================================================
# SLURM Template
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
echo "SLURM_NODELIST = $SLURM_NODELIST"
echo "-----------------------------------------------------------"

cd "$SLURM_SUBMIT_DIR"

"""

CHUNK_BLOCK = """
# --- Build name_list for chunk {chunk_id} of {dataset} ---
DATASET_DIR="{ds_path}"
CHUNK_ID={chunk_id}
CHUNK_SIZE={chunk_size}

ALL_FILES=($(ls "$DATASET_DIR"/*.wclq 2>/dev/null | sort | xargs -n1 basename))
TOTAL=${{#ALL_FILES[@]}}
START=$((CHUNK_ID * CHUNK_SIZE))
END=$(( (CHUNK_ID + 1) * CHUNK_SIZE ))
if [ $END -gt $TOTAL ]; then END=$TOTAL; fi
if [ $START -ge $TOTAL ]; then
    echo "Chunk $CHUNK_ID is beyond dataset size ($TOTAL). Exiting."
    exit 0
fi

NAMELIST="namelist-{tag}.txt"
printf '%s\\n' "${{ALL_FILES[@]:START:END-START}}" > "$NAMELIST"
N_INST=$((END - START))
echo "Chunk $CHUNK_ID: instances $((START+1))..$END / $TOTAL ($N_INST instances)"

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
    """Parse comma-separated seeds: '1,2' -> [1, 2]; '3-5' -> [3,4,5]"""
    seeds = []
    for part in s.split(","):
        part = part.strip()
        if "-" in part:
            a, b = part.split("-")
            seeds.extend(range(int(a), int(b) + 1))
        else:
            seeds.append(int(part))
    return sorted(set(seeds))


def parse_datasets(s):
    names = [x.strip() for x in s.split(",") if x.strip()]
    for n in names:
        if n not in DATASETS:
            raise SystemExit(f"Unknown dataset: {n}. Available: {list(DATASETS.keys())}")
    return names


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--seeds", type=parse_seeds, default=DEFAULT_SEEDS,
                    help="Seeds to generate scripts for (e.g. '1,2' or '3-10'). Default: 1..10")
    ap.add_argument("--datasets", type=parse_datasets, default=list(DATASETS.keys()),
                    help=f"Datasets to include (comma-separated). Default: all ({list(DATASETS.keys())})")
    ap.add_argument("--solvers", type=lambda s: [x.strip() for x in s.split(",")],
                    default=[s["name"] for s in SOLVERS],
                    help=f"Solvers to include. Default: all ({[s['name'] for s in SOLVERS]})")
    args = ap.parse_args()

    seeds = args.seeds
    active_solvers = [s for s in SOLVERS if s["name"] in args.solvers]
    if not active_solvers:
        raise SystemExit(f"No solvers matched. Known: {[s['name'] for s in SOLVERS]}")

    out_dir = Path(".")
    generated = []
    job_infos = []

    print("Generating SLURM scripts for MWDS exp-4 (Dual-Deep v6 vs baseline)")
    print(f"  Solvers:  {[s['name'] for s in active_solvers]}")
    print(f"  Datasets: {args.datasets}")
    print(f"  Seeds:    {seeds}  (={len(seeds)} seeds)")
    print(f"  Cutoff:   {CUTOFF}s   Chunk size: {CHUNK_SIZE}   Parallel: {PARALLEL}")
    print("-" * 70)

    total_hours = 0

    for ds_name in args.datasets:
        ds_info = DATASETS[ds_name]
        ds_path = ds_info["path"]
        n_inst = ds_info["n"]
        if n_inst <= 0:
            print(f"  {ds_name}: SKIPPED (n=0, fill in instance count first)")
            continue
        n_chunks = math.ceil(n_inst / CHUNK_SIZE)

        for slv in active_solvers:
            solver_bin = f"../codes/{slv['dir']}/{slv['bin']}"

            for seed in seeds:
                for chunk_id in range(n_chunks):
                    actual_size = min(CHUNK_SIZE, n_inst - chunk_id * CHUNK_SIZE)
                    tag = f"{slv['name']}-{ds_name}-c{chunk_id}-s{seed}"
                    job_name = f"d_{ds_name[:2]}_c{chunk_id}_s{seed}"
                    script_file = f"jobslurm-{tag}"

                    chunk_cmd = CHUNK_BLOCK.format(
                        chunk_id=chunk_id,
                        dataset=ds_name,
                        ds_path=ds_path,
                        chunk_size=CHUNK_SIZE,
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

                    filepath = out_dir / script_file
                    with open(filepath, "w") as f:
                        f.write(content)
                    os.chmod(filepath, 0o755)
                    generated.append(script_file)

                    est_h = actual_size * CUTOFF / PARALLEL / 3600
                    total_hours += est_h
                    job_infos.append((ds_name, slv['name'], seed, chunk_id, actual_size, est_h))

        ds_jobs = n_chunks * len(seeds) * len(active_solvers)
        ds_hours = n_inst * len(seeds) * CUTOFF / PARALLEL / 3600
        print(f"  {ds_name}: {n_chunks} chunks × {len(seeds)} seeds × {len(active_solvers)} solvers "
              f"= {ds_jobs} jobs  (~{ds_hours:.0f} CPU-hours, ~{n_inst * CUTOFF / PARALLEL / 3600:.1f}h per seed)")

    # Write submit_all.sh that submits every generated script
    with open(out_dir / "submit_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Submits {len(generated)} jobs. WARNING: cluster limit is 200 concurrent jobs.\n")
        f.write("# For full run, use auto_submit.sh instead (batched submission).\n\n")
        for s in sorted(generated):
            f.write(f"sbatch {s}\nsleep 0.5\n")
        f.write(f"\necho '=== {len(generated)} jobs submitted ==='\n")
    os.chmod(out_dir / "submit_all.sh", 0o755)

    print("-" * 70)
    print(f"Total: {len(generated)} SLURM scripts")
    print(f"Estimated CPU-hours: {total_hours:.0f}")
    print(f"Max wall time per job: ~{CHUNK_SIZE * CUTOFF / PARALLEL / 3600:.1f}h")
    print(f"Submit: bash submit_all.sh  (or nohup bash auto_submit.sh > auto_submit.log 2>&1 &)")


if __name__ == "__main__":
    main()
