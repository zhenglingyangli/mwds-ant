#!/usr/bin/env python3
"""
Scan existing exp-2 results, identify missing/empty instances,
and generate SLURM scripts to re-run ONLY those gaps.

Strategy:
  1. For each (solver, dataset, seed), find all expected instances (540)
  2. Among existing .out files, identify: empty (0B), header-only, good
  3. Generate patch jobs for empty + header-only instances only
  4. For dual-fast duplicates: keep first-submitted, skip re-running

Usage:
    python3 generate_patch.py <result_root>
"""

import os
import re
import math
from pathlib import Path
from collections import defaultdict

WCLQ_ROOT = "/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq"

SOLVERS = [
    {"name": "dual-fast", "dir": "Dual-Fast",     "bin": "dual-fast"},
    {"name": "fast-v19",  "dir": "Dual-Fast-v19", "bin": "dual-fast-v19"},
]

DATASETS = {
    "T1": {"path": f"{WCLQ_ROOT}/T1_wclq", "n": 540},
    "T2": {"path": f"{WCLQ_ROOT}/T2_wclq", "n": 540},
}

SEEDS      = list(range(1, 11))
CUTOFF     = 3600
ALPHA      = 1
PARALLEL   = 10
GO_TIMEOUT = CUTOFF + 120
PATCH_CHUNK = 55

SLURM_PARTITION = "hfacnormal01"
SLURM_MEM       = "64G"

RE_SUMMARY = re.compile(r">>>\s+\S+\s+\|V\|")
RE_OPTIMAL = re.compile(r"====")
RE_ROUND   = re.compile(r"^\s*\d+\s+(-?\d+)\s+(-?\d+)")


def is_good_file(filepath):
    """Check if .out file has parseable results (rounds or summary)."""
    try:
        size = filepath.stat().st_size
        if size == 0:
            return False
        text = filepath.read_text(errors="replace")
        if RE_SUMMARY.search(text) or RE_OPTIMAL.search(text):
            return True
        for line in text.splitlines():
            if RE_ROUND.match(line):
                return True
        return False
    except Exception:
        return False


def scan_existing(result_root):
    """Build dict: (solver, dataset, seed, instance) -> (timestamp, is_good)"""
    existing = {}
    root = Path(result_root)
    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("result-"):
            continue

        ts_match = re.search(r"-(\d{14})$", entry.name)
        timestamp = ts_match.group(1) if ts_match else "99999999999999"

        seed_match = re.search(r"-c\d+-s(\d+)-\d{14}$", entry.name)
        if not seed_match:
            seed_match = re.search(r"-seed(\d+)-\d{14}$", entry.name)
        seed = int(seed_match.group(1)) if seed_match else 0

        dataset = "unknown"
        for ds in ["T1", "T2"]:
            if f"-{ds}-" in entry.name or f"-{ds}_" in entry.name:
                dataset = ds
                break

        solver = "unknown"
        for sv in ["fast-v19", "dual-fast"]:
            if sv in entry.name:
                solver = sv
                break

        for out_file in entry.glob("*.out"):
            inst = out_file.name.replace(".out", "")
            key = (solver, dataset, seed, inst)
            good = is_good_file(out_file)

            if key not in existing or timestamp < existing[key][0]:
                existing[key] = (timestamp, good)

    return existing


def get_all_instances(ds_path):
    """List all .wclq files in a dataset directory."""
    p = Path(ds_path)
    return sorted(f.name for f in p.glob("*.wclq"))


def main():
    import sys
    if len(sys.argv) < 2:
        print("Usage: python3 generate_patch.py <result_root>")
        sys.exit(1)

    result_root = sys.argv[1]
    print(f"Scanning {result_root} ...")
    existing = scan_existing(result_root)

    total_missing = 0
    patch_jobs = []

    for ds_name, ds_info in DATASETS.items():
        all_inst = get_all_instances(ds_info["path"])
        print(f"\n{ds_name}: {len(all_inst)} instances")

        for slv in SOLVERS:
            for seed in SEEDS:
                missing = []
                good_count = 0
                bad_count = 0

                for inst_file in all_inst:
                    inst = inst_file
                    key = (slv["name"], ds_name, seed, inst)
                    if key in existing and existing[key][1]:
                        good_count += 1
                    else:
                        bad_count += 1
                        missing.append(inst_file)

                if missing:
                    patch_jobs.append({
                        "solver": slv,
                        "dataset": ds_name,
                        "ds_path": ds_info["path"],
                        "seed": seed,
                        "missing": missing,
                    })
                    total_missing += len(missing)
                    print(f"  {slv['name']}/{ds_name}/seed{seed}: "
                          f"{good_count} good, {bad_count} missing")

    if total_missing == 0:
        print("\nNo missing instances! All data is complete.")
        return

    print(f"\nTotal missing: {total_missing} (solver, seed, instance) combos")

    script_count = 0
    all_scripts = []

    for job in patch_jobs:
        slv = job["solver"]
        ds_name = job["dataset"]
        seed = job["seed"]
        missing = job["missing"]
        solver_bin = f"../codes/{slv['dir']}/{slv['bin']}"

        n_chunks = math.ceil(len(missing) / PATCH_CHUNK)
        for c in range(n_chunks):
            chunk_insts = missing[c * PATCH_CHUNK : (c + 1) * PATCH_CHUNK]
            tag = f"patch-{slv['name']}-{ds_name}-s{seed}-p{c}"
            job_name = f"p_{ds_name[:2]}_s{seed}_p{c}"
            script_file = f"jobslurm-{tag}"

            namelist_file = f"namelist-{tag}.txt"
            with open(namelist_file, "w") as nf:
                nf.write("\n".join(chunk_insts) + "\n")

            content = f"""#!/bin/sh
#SBATCH --job-name={job_name}
#SBATCH --partition={SLURM_PARTITION}
#SBATCH --time=0-08:00:00
#SBATCH --output=slurm-%j.out
#SBATCH --mem={SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={PARALLEL}
echo "hostname = $(hostname), SLURM_JOBID = $SLURM_JOBID"
cd "$SLURM_SUBMIT_DIR"

python3 ./goSolver.py {PARALLEL} {GO_TIMEOUT} \\
    {solver_bin} "{job['ds_path']}" ./result \\
    --name_list "{namelist_file}" \\
    --suffix {tag} \\
    {CUTOFF} {seed} {ALPHA}

echo "=== DONE: {tag} ({len(chunk_insts)} instances) ==="
"""
            with open(script_file, "w") as f:
                f.write(content)
            os.chmod(script_file, 0o755)
            all_scripts.append(script_file)
            script_count += 1

    with open("submit_patch.sh", "w") as f:
        f.write("#!/bin/bash\n")
        f.write(f"# Patch run: {script_count} jobs for {total_missing} missing instances\n\n")
        for s in sorted(all_scripts):
            f.write(f"sbatch {s}\nsleep 0.5\n")
        f.write(f"\necho '=== {script_count} patch jobs submitted ==='\n")
    os.chmod("submit_patch.sh", 0o755)

    est_hours = total_missing * CUTOFF / PARALLEL / 3600
    print(f"\nGenerated: {script_count} SLURM scripts")
    print(f"Estimated: {est_hours:.0f} CPU-hours")
    print(f"Submit with: bash submit_patch.sh  (or use auto_submit.sh)")


if __name__ == "__main__":
    main()
