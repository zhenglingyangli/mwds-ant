#!/usr/bin/env python3
"""Generate SLURM scripts for exp10 Layer-A fair DBS vs Ant-Q runs.

This generator intentionally creates solver-only jobs.  External LP/MILP
certificates are not applied here and must be reported as separate Layer B/C
post-processing.
"""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path


DATASETS = ["T1", "T2", "UDG", "BHOSLIB", "DIMACS", "DIMACS10", "NDR", "SNAP"]
DEFAULT_SEEDS = [1, 2, 3, 4, 5]

DEFAULT_CUTOFF = 3600
ALPHA = 90
PARALLEL = 5
CUTOFF_MEM = 16

SLURM_PARTITION = "hfacnormal01"
SLURM_MEM = "64G"
SLURM_TIME = "0-04:00:00"

EXP_ROOT = Path(__file__).resolve().parents[1]
MANIFEST = EXP_ROOT / "dataset_manifest.json"
SELECTED_DIR = EXP_ROOT / "selected_instances"

SOLVER_FAMILIES = {
    "deep": {
        "dbs": {
            "solver_name": "deep-dbs",
            "solver_path": "../../exp-4/codes/Dual-Deep/dual-deep",
        },
        "antq": {
            "solver_name": "deep-antq",
            "solver_path": "../../exp-4/codes/Dual-Deep-v6/dual-deep-v6",
        },
    },
    "fast": {
        "dbs": {
            "solver_name": "fast-dbs",
            "solver_path": "../../exp-2/codes/Dual-Fast/dual-fast",
        },
        "antq": {
            "solver_name": "fast-antq",
            "solver_path": "../../exp-2/codes/Dual-Fast-v19/dual-fast-v19",
        },
    },
}


def parse_csv(text: str) -> list[str]:
    return [x.strip() for x in text.split(",") if x.strip()]


def parse_seeds(text: str) -> list[int]:
    values: list[int] = []
    for item in parse_csv(text):
        if "-" in item:
            start, end = item.split("-", 1)
            values.extend(range(int(start), int(end) + 1))
        else:
            values.append(int(item))
    return sorted(set(values))


def load_dataset_paths(path_mode: str, datasets: list[str]) -> dict[str, str]:
    payload = json.loads(MANIFEST.read_text())
    out: dict[str, str] = {}
    for dataset in datasets:
        if dataset not in payload:
            raise SystemExit(f"Unknown dataset {dataset}; known={sorted(payload)}")
        selected = SELECTED_DIR / f"{dataset}.txt"
        if not selected.exists():
            raise SystemExit(f"Missing selected instance list: {selected}")
        lines = [line for line in selected.read_text().splitlines() if line.strip()]
        if len(lines) != 5:
            raise SystemExit(f"{selected} must contain exactly 5 instances; got {len(lines)}")
        key = "hpc_path" if path_mode == "hpc" else "local_path"
        value = payload[dataset].get(key)
        if not value:
            raise SystemExit(f"No {key} configured for {dataset}")
        out[dataset] = str(value)
    return out


def cleanup_old_scripts() -> None:
    for path in Path(".").glob("jobslurm-*"):
        path.unlink()
    for path in [Path("submit_all.sh"), Path(".submitted_jobs")]:
        if path.exists():
            path.unlink()


def slurm_script(
    *,
    solver_family: str,
    method: str,
    solver_name: str,
    solver_path: str,
    dataset: str,
    dataset_path: str,
    seed: int,
    rep: int,
    cutoff: int,
    go_timeout: int,
) -> str:
    actual_seed = seed + rep * 100
    suffix = f"{solver_name}-{dataset}-s{seed}-r{rep + 1}"
    job_name = f"e10_{solver_family[:1]}{method[:1]}_{dataset[:2]}_s{seed}_r{rep + 1}"
    return f"""#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition={SLURM_PARTITION}
#SBATCH --time={SLURM_TIME}
#SBATCH --output=slurm-%j.out
#SBATCH --mem={SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={PARALLEL}
echo "-----------------------------------------------------------"
echo "hostname       = $(hostname)"
echo "SLURM_JOBID    = $SLURM_JOBID"
echo "SLURM_NODELIST = $SLURM_NODELIST"
echo "-----------------------------------------------------------"
cd "$SLURM_SUBMIT_DIR"

DATASET_DIR="{dataset_path}"
NAMELIST="../selected_instances/{dataset}.txt"
if [ ! -d "$DATASET_DIR" ]; then
    echo "ERROR: dataset path does not exist: $DATASET_DIR"
    exit 2
fi
if [ ! -f "$NAMELIST" ]; then
    echo "ERROR: selected list does not exist: $NAMELIST"
    exit 2
fi

python3 ../../exp-4/jobs/goSolver.py {PARALLEL} {go_timeout} \\
    {solver_path} "$DATASET_DIR" ./result \\
    --cutoff_mem {CUTOFF_MEM} \\
    --name_list "$NAMELIST" \\
    --suffix {suffix} \\
    {cutoff} {actual_seed} {ALPHA}

echo "=== DONE: {suffix} ==="
"""


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--datasets", default=",".join(DATASETS))
    parser.add_argument("--seeds", default=",".join(str(x) for x in DEFAULT_SEEDS))
    parser.add_argument("--solver-families", default="deep,fast")
    parser.add_argument("--methods", default="dbs,antq")
    parser.add_argument("--k", type=int, default=2, help="Independent calls per method")
    parser.add_argument("--cutoff", type=int, default=DEFAULT_CUTOFF)
    parser.add_argument("--path-mode", choices=["hpc", "local"], default="hpc")
    parser.add_argument("--keep-old", action="store_true", help="Do not delete existing jobslurm-* files first")
    args = parser.parse_args()

    datasets = parse_csv(args.datasets)
    seeds = parse_seeds(args.seeds)
    families = parse_csv(args.solver_families)
    methods = parse_csv(args.methods)
    if args.k < 1:
        raise SystemExit("--k must be >= 1")
    for family in families:
        if family not in SOLVER_FAMILIES:
            raise SystemExit(f"Unknown solver family {family}; known={sorted(SOLVER_FAMILIES)}")
    for method in methods:
        if method not in {"dbs", "antq"}:
            raise SystemExit("Only methods dbs,antq are implemented. Guarded Ant-Q is intentionally not implemented yet.")

    if not args.keep_old:
        cleanup_old_scripts()

    dataset_paths = load_dataset_paths(args.path_mode, datasets)
    go_timeout = args.cutoff + 120
    generated: list[str] = []

    for dataset in datasets:
        for family in families:
            for method in methods:
                cfg = SOLVER_FAMILIES[family][method]
                for seed in seeds:
                    for rep in range(args.k):
                        script_name = f"jobslurm-{cfg['solver_name']}-{dataset}-s{seed}-r{rep + 1}"
                        Path(script_name).write_text(
                            slurm_script(
                                solver_family=family,
                                method=method,
                                solver_name=cfg["solver_name"],
                                solver_path=cfg["solver_path"],
                                dataset=dataset,
                                dataset_path=dataset_paths[dataset],
                                seed=seed,
                                rep=rep,
                                cutoff=args.cutoff,
                                go_timeout=go_timeout,
                            )
                        )
                        os.chmod(script_name, 0o755)
                        generated.append(script_name)

    with Path("submit_all.sh").open("w") as handle:
        handle.write("#!/bin/bash\nset -euo pipefail\n")
        handle.write(f"# Generated by exp10/jobs/generate_scripts.py; jobs={len(generated)}\n")
        for script in sorted(generated):
            handle.write(f"sbatch {script}\nsleep 0.5\n")
        handle.write(f"echo '=== {len(generated)} exp10 jobs submitted ==='\n")
    os.chmod("submit_all.sh", 0o755)

    solver_calls = len(datasets) * 5 * len(seeds) * len(families) * len(methods) * args.k
    worst_core_hours = solver_calls * args.cutoff / 3600
    local_10_core_hours = worst_core_hours / 10
    print(f"Generated jobs: {len(generated)}")
    print(f"Solver calls:   {solver_calls}")
    print(f"Worst-case core-hours: {worst_core_hours:.1f}")
    print(f"Worst-case 10-core wall time: {local_10_core_hours:.1f} h")
    print("Submit with: nohup bash auto_submit.sh > auto_submit.log 2>&1 &")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

