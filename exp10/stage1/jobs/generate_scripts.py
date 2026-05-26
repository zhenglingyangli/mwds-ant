#!/usr/bin/env python3
"""Generate SLURM scripts for exp10 Stage-1 candidate screens."""

from __future__ import annotations

import argparse
import os
from pathlib import Path


DEFAULT_CANDIDATE_ROOT_BASE = Path("..")
SLURM_PARTITION = "hfacnormal01"
SLURM_MEM = "64G"


def csv_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def job_script(
    *,
    candidate: str,
    datasets: str,
    seeds: str,
    reps: int,
    cutoff: int,
    workers: int,
    path_mode: str,
    candidate_root_base: Path,
    allow_recursive_resolve: bool,
) -> str:
    output_dir = Path("../sumup/result") / candidate
    recursive_flag = " \\\n  --allow-recursive-resolve" if allow_recursive_resolve else ""
    wall_minutes = max(30, int(cutoff * reps * 5 / 60) + 20)
    hours = wall_minutes // 60
    minutes = wall_minutes % 60
    slurm_time = f"0-{hours:02d}:{minutes:02d}:00"
    return f"""#!/bin/sh
#SBATCH --job-name=e10s1_{candidate}
#SBATCH --partition={SLURM_PARTITION}
#SBATCH --time={slurm_time}
#SBATCH --output=slurm-%j.out
#SBATCH --mem={SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={workers}

set -eu

echo "-----------------------------------------------------------"
echo "hostname       = $(hostname)"
echo "SLURM_JOBID    = $SLURM_JOBID"
echo "candidate      = {candidate}"
echo "datasets       = {datasets}"
echo "seeds          = {seeds}"
echo "cutoff         = {cutoff}"
echo "-----------------------------------------------------------"

cd "$SLURM_SUBMIT_DIR"

python3 ./goSolver_stage1.py \\
  --candidate {candidate} \\
  --candidate-config ./candidates.json \\
  --candidate-root-base "{candidate_root_base}" \\
  --datasets "{datasets}" \\
  --seeds "{seeds}" \\
  --reps {reps} \\
  --cutoff {cutoff} \\
  --workers {workers} \\
  --path-mode {path_mode} \\
  --output-dir "{output_dir}"{recursive_flag}

echo "=== DONE stage1 candidate {candidate} ==="
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", default="v005,v006,v007,v009")
    parser.add_argument("--datasets", default="T1,T2,UDG,BHOSLIB,DIMACS,DIMACS10,NDR,SNAP")
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--cutoff", type=int, default=20)
    parser.add_argument("--workers", type=int, default=20)
    parser.add_argument("--path-mode", choices=["hpc", "local"], default="hpc")
    parser.add_argument("--candidate-root-base", type=Path, default=DEFAULT_CANDIDATE_ROOT_BASE)
    parser.add_argument("--allow-recursive-resolve", action="store_true")
    parser.add_argument("--keep-old", action="store_true")
    args = parser.parse_args()

    if not args.keep_old:
        for old in Path(".").glob("jobslurm-*"):
            old.unlink()
        for old in [Path("submit_all.sh")]:
            if old.exists():
                old.unlink()

    generated: list[Path] = []
    for candidate in csv_list(args.candidates):
        path = Path(f"jobslurm-{candidate}")
        path.write_text(
            job_script(
                candidate=candidate,
                datasets=args.datasets,
                seeds=args.seeds,
                reps=args.reps,
                cutoff=args.cutoff,
                workers=args.workers,
                path_mode=args.path_mode,
                candidate_root_base=args.candidate_root_base,
                allow_recursive_resolve=args.allow_recursive_resolve,
            )
        )
        os.chmod(path, 0o755)
        generated.append(path)

    with Path("submit_all.sh").open("w") as handle:
        handle.write("#!/bin/bash\nset -euo pipefail\n")
        for path in generated:
            handle.write(f"sbatch {path}\nsleep 1\n")
        handle.write(f"echo 'submitted {len(generated)} stage1 jobs'\n")
    os.chmod("submit_all.sh", 0o755)

    print(f"Generated jobs: {len(generated)}")
    print("Submit with: bash auto_submit.sh")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
