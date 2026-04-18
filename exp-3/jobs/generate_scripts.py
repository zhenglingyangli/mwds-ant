#!/usr/bin/env python3
"""
Generate SLURM job scripts for MWDS Dual-Deep v10 experiment (exp-3).

Matches exp-1 Dual-Deep configuration:
- Cutoff: 300s
- Seeds: 1, 2  (same as exp-1 actual runs)
- Datasets: T1 (171 instances), T2 (141 instances)
  — same instance subset as exp-1's v6 results
- Alpha: 1
- Parallel: 10

Uses --name_list to restrict to the exact instances v6 ran in exp-1.
"""

import os
from pathlib import Path

# ============================================================
# Configuration  (matches exp-1 actual runs)
# ============================================================

SOLVERS = [
    {"name": "deep-v10", "dir": "Dual-Deep-v10", "bin": "dual-deep-v10"},
]

WCLQ_ROOT = "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq"

DATASETS = {
    "T1": {"path": f"{WCLQ_ROOT}/T1_wclq", "namelist": "namelist-T1.txt", "n": 171},
    "T2": {"path": f"{WCLQ_ROOT}/T2_wclq", "namelist": "namelist-T2.txt", "n": 141},
}

SEEDS     = [1, 2]
CUTOFF    = 300
# Paper/original all use alpha=90 (internal ALPHA=1.90). NOT 1.
ALPHA     = 90
PARALLEL  = 10
GO_TIMEOUT = CUTOFF + 60

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

    print("Generating SLURM scripts for MWDS exp-3 (Dual-Deep-v10) …")
    print(f"  Solvers:  {[s['name'] for s in SOLVERS]}")
    print(f"  Datasets: {list(DATASETS.keys())}")
    print(f"  Seeds:    {SEEDS}")
    print(f"  Cutoff:   {CUTOFF}s   Parallel: {PARALLEL}")
    print("-" * 70)

    for ds_name, ds_info in DATASETS.items():
        ds_path = ds_info["path"]
        namelist = ds_info["namelist"]
        n_inst = ds_info["n"]

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
                    f"--name_list ./{namelist} "
                    f"--suffix {suffix} "
                    f"{CUTOFF} {seed} {ALPHA}"
                )
                lines.append(cmd)

            commands = "\n\n".join(lines)
            write_script(out_dir / script_file, job_name, commands, PARALLEL)
            generated.append(script_file)
            print(f"  {script_file}  ({slv['name']} × {ds_name} × {n_inst} inst × {len(SEEDS)} seeds)")

    # ---- submit_all.sh ----
    with open(out_dir / "submit_all.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Batch submit: {len(generated)} SLURM jobs\n")
        f.write(f"# {len(SOLVERS)} solver × {len(DATASETS)} datasets, {len(SEEDS)} seeds each\n")
        f.write(f"# Instance subsets match exp-1 v6 runs\n\n")
        for ds_name in DATASETS:
            f.write(f"echo '=== {ds_name} ==='\n")
            for s in generated:
                if s.endswith(f"-{ds_name}"):
                    f.write(f"sbatch {s}\nsleep 1\n")
            f.write("\n")
    os.chmod(out_dir / "submit_all.sh", 0o755)

    total_inst = sum(d["n"] for d in DATASETS.values())
    print("-" * 70)
    print(f"Total: {len(generated)} SLURM scripts generated")
    print(f"Instances: {total_inst} ({'+'.join(str(d['n']) for d in DATASETS.values())})")
    print(f"Estimated wall time per job: ~{total_inst * CUTOFF / PARALLEL / 60:.0f} min")
    print("Created: submit_all.sh")


if __name__ == "__main__":
    main()
