#!/usr/bin/env python3
"""
Generate SLURM job scripts for MWDS Dual-Bounds experiment (exp-1).

Experiment grid:
- Dual-Fast: 6 versions (baseline, v19, v28, Exp5, Exp6, Exp9)
- Dual-Deep: 2 versions (baseline, v6)
- Datasets:  T1 (50 instances), T2 (50 instances)
- Seeds:     1..5
- Cutoff:    300 s
- Each SLURM job = 1 solver × 1 dataset, iterating over all 5 seeds.
"""

import os
from pathlib import Path

# ============================================================
# Configuration  (edit here for different experiments)
# ============================================================

SOLVERS = [
    # --- Dual-Fast family ---
    {"name": "dual-fast",      "dir": "Dual-Fast",       "bin": "dual-fast",       "group": "fast"},
    {"name": "fast-v19",       "dir": "Dual-Fast-v19",   "bin": "dual-fast-v19",   "group": "fast"},
    {"name": "fast-v28",       "dir": "Dual-Fast-v28",   "bin": "dual-fast-v28",   "group": "fast"},
    {"name": "exp5-freqscore", "dir": "Exp5-FreqScore",  "bin": "exp5-freqscore",  "group": "fast"},
    {"name": "exp6-poolrelink","dir": "Exp6-PoolRelink",  "bin": "exp6-poolrelink", "group": "fast"},
    {"name": "exp9-freq-pool", "dir": "Exp9-Freq-Pool",  "bin": "exp9-freq-pool",  "group": "fast"},
    # --- Dual-Deep family ---
    {"name": "dual-deep",      "dir": "Dual-Deep",       "bin": "dual-deep",       "group": "deep"},
    {"name": "deep-v6",        "dir": "Dual-Deep-v6",    "bin": "dual-deep-v6",    "group": "deep"},
]

DATASETS = {
    "T1": "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq",
    "T2": "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T2_wclq",
}

SEEDS     = [1, 2, 3, 4, 5]
CUTOFF    = 300          # solver-level cutoff (seconds)
# alpha CLI arg: internal ALPHA = 1 + alpha/100. Paper/original all use 90 -> 1.90.
ALPHA     = 90
PARALLEL  = 10           # concurrent solver processes inside one job
GO_TIMEOUT = CUTOFF + 60 # goSolver process-level safety timeout

# ============================================================
# SLURM Template
# ============================================================

SLURM_HEADER = """#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition=hfacnormal01
#SBATCH --time=0-06:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --mem=8G
#SBATCH --nodes=1
#SBATCH --cpus-per-task={cpus}
echo "-----------------------------------------------------------"
echo "hostname                     =   $(hostname)"
echo "SLURM_JOB_NAME               =   $SLURM_JOB_NAME"
echo "SLURM_JOBID                  =   $SLURM_JOBID"
echo "SLURM_NODELIST               =   $SLURM_NODELIST"
echo "SLURM_CPUS_ON_NODE           =   $SLURM_CPUS_ON_NODE"
echo "-----------------------------------------------------------"

cd "$SLURM_SUBMIT_DIR"

{commands}

echo "=== ALL SEEDS DONE ==="
"""


def write_script(filepath, job_name, commands, cpus):
    content = SLURM_HEADER.format(
        job_name=job_name,
        cpus=cpus,
        commands=commands,
    )
    with open(filepath, "w") as f:
        f.write(content)
    os.chmod(filepath, 0o755)


def main():
    out_dir = Path(".")
    generated = []

    print("Generating SLURM scripts for MWDS exp-1 …")
    print(f"  Solvers:  {[s['name'] for s in SOLVERS]}")
    print(f"  Datasets: {list(DATASETS.keys())}")
    print(f"  Seeds:    {SEEDS}")
    print(f"  Cutoff:   {CUTOFF}s   Parallel: {PARALLEL}")
    print("-" * 70)

    for ds_name, ds_path in DATASETS.items():
        for slv in SOLVERS:
            solver_bin = f"../codes/{slv['dir']}/{slv['bin']}"
            suffix_base = f"{slv['name']}-{ds_name}"
            job_name = f"mwds_{suffix_base}"
            script_file = f"jobslurm-{suffix_base}"

            lines = []
            for seed in SEEDS:
                suffix = f"{suffix_base}-seed{seed}"
                cmd = (
                    f"echo '>>> seed={seed}'\n"
                    f"python3 ./goSolver.py {PARALLEL} {GO_TIMEOUT} "
                    f"{solver_bin} {ds_path} ./result "
                    f"--suffix {suffix} "
                    f"{CUTOFF} {seed} {ALPHA}"
                )
                lines.append(cmd)

            commands = "\n\n".join(lines)
            write_script(out_dir / script_file, job_name, commands, PARALLEL)
            generated.append(script_file)
            print(f"  {script_file}  ({slv['name']} × {ds_name} × {len(SEEDS)} seeds)")

    # ---- submit_all.sh ----
    with open(out_dir / "submit_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Batch submit: {len(generated)} SLURM jobs\n")
        f.write(f"# {len(SOLVERS)} solvers × {len(DATASETS)} datasets, {len(SEEDS)} seeds each\n\n")
        for ds_name in DATASETS:
            f.write(f"echo '=== {ds_name} ==='\n")
            for s in generated:
                if s.endswith(f"-{ds_name}"):
                    f.write(f"sbatch {s}\nsleep 1\n")
            f.write("\n")
    os.chmod(out_dir / "submit_all.sh", 0o755)

    print("-" * 70)
    print(f"Total: {len(generated)} SLURM scripts generated")
    print("Created: submit_all.sh")
    print(f"\nEstimated wall time per job: ~{len(SEEDS) * 50 * CUTOFF / PARALLEL / 60:.0f} min")


if __name__ == "__main__":
    main()
