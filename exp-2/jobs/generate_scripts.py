#!/usr/bin/env python3
"""
Generate SLURM job scripts for MWDS Dual-Fast v19 full experiment (exp-2).

Matches the paper's setup: 3600s cutoff, 10 seeds.
Large datasets are split into chunks (~55 instances each) for efficient scheduling.
Each SLURM job = 1 chunk × 1 seed, using goSolver.py --name_list for instance selection.
"""

import os
import math
from pathlib import Path

# ============================================================
# Configuration
# ============================================================

SOLVERS = [
    {"name": "dual-fast", "dir": "Dual-Fast",     "bin": "dual-fast"},
    {"name": "fast-v19",  "dir": "Dual-Fast-v19", "bin": "dual-fast-v19"},
]

WCLQ_ROOT = "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq"

DATASETS = {
    "T1": {"path": f"{WCLQ_ROOT}/T1_wclq", "n": 540},
    "T2": {"path": f"{WCLQ_ROOT}/T2_wclq", "n": 540},
}

SEEDS      = list(range(1, 11))      # 10 seeds: 1..10
CUTOFF     = 3600                     # seconds (paper setting)
ALPHA      = 1
PARALLEL   = 10
GO_TIMEOUT = CUTOFF + 120            # goSolver safety timeout
CHUNK_SIZE = 55                       # instances per SLURM job

SLURM_PARTITION = "hfacnormal01"
SLURM_MEM       = "64G"

# ============================================================
# SLURM Template
# ============================================================

SLURM_HEADER = """#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition={partition}
#SBATCH --time=0-08:00:00
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

# Template for runtime chunk creation via name_list
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
    --name_list "$NAMELIST" \\
    --suffix {suffix} \\
    {cutoff} {seed} {alpha}

rm -f "$NAMELIST"
echo "=== DONE: {suffix} ==="
"""


def main():
    out_dir = Path(".")
    generated = []
    job_infos = []

    print("Generating SLURM scripts for MWDS exp-2 (full v19 experiment)")
    print(f"  Solvers:  {[s['name'] for s in SOLVERS]}")
    print(f"  Datasets: {list(DATASETS.keys())}")
    print(f"  Seeds:    {SEEDS}")
    print(f"  Cutoff:   {CUTOFF}s   Chunk size: {CHUNK_SIZE}")
    print("-" * 70)

    total_hours = 0

    for ds_name, ds_info in DATASETS.items():
        ds_path = ds_info["path"]
        n_inst = ds_info["n"]
        if n_inst <= 0:
            print(f"  {ds_name}: SKIPPED (n=0, fill in instance count first)")
            continue
        n_chunks = math.ceil(n_inst / CHUNK_SIZE)

        for slv in SOLVERS:
            solver_bin = f"../codes/{slv['dir']}/{slv['bin']}"

            for seed in SEEDS:
                for chunk_id in range(n_chunks):
                    actual_size = min(CHUNK_SIZE, n_inst - chunk_id * CHUNK_SIZE)
                    tag = f"{slv['name']}-{ds_name}-c{chunk_id}-s{seed}"
                    job_name = f"m_{ds_name[:2]}_c{chunk_id}_s{seed}"
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
                    )

                    content = SLURM_HEADER.format(
                        job_name=job_name,
                        partition=SLURM_PARTITION,
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

        ds_jobs = n_chunks * len(SEEDS) * len(SOLVERS)
        ds_hours = n_inst * len(SEEDS) * CUTOFF / PARALLEL / 3600
        print(f"  {ds_name}: {n_chunks} chunks × {len(SEEDS)} seeds = {ds_jobs} jobs "
              f"(~{ds_hours:.0f} CPU-hours, ~{n_inst * CUTOFF / PARALLEL / 3600:.1f}h per seed)")

    # ---- submit_all.sh ----
    with open(out_dir / "submit_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# exp-2: {len(generated)} SLURM jobs\n")
        f.write(f"# {len(SOLVERS)} solver × {len(DATASETS)} datasets × {len(SEEDS)} seeds × chunks\n")
        f.write(f"# Estimated total: {total_hours:.0f} CPU-hours\n\n")

        for ds_name in DATASETS:
            f.write(f"echo '=== {ds_name} ==='\n")
            ds_scripts = [s for s in generated if f"-{ds_name}-" in s]
            for s in sorted(ds_scripts):
                f.write(f"sbatch {s}\nsleep 0.5\n")
            f.write(f"echo '  {len(ds_scripts)} jobs submitted for {ds_name}'\n\n")

        f.write(f"echo '=== Total: {len(generated)} jobs submitted ==='\n")
    os.chmod(out_dir / "submit_all.sh", 0o755)

    print("-" * 70)
    print(f"Total: {len(generated)} SLURM scripts")
    print(f"Estimated CPU-hours: {total_hours:.0f}")
    print(f"Max wall time per job: ~{CHUNK_SIZE * CUTOFF / PARALLEL / 3600:.1f}h")
    print(f"\nCreated: submit_all.sh")
    print(f"\nTip: To submit a subset, e.g. only T1:")
    print(f"  for f in jobslurm-fast-v19-T1-*; do sbatch $f; sleep 0.5; done")


if __name__ == "__main__":
    main()
