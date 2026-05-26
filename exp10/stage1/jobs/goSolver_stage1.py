#!/usr/bin/env python3
"""Run one exp10 Stage-1 candidate screen.

This script only executes solver calls and writes per-candidate result CSVs.
Use `generate_scripts.py` to create SLURM jobs, and use
`../sumup/run_sumup.sh` for strict gates after jobs finish.
"""

from __future__ import annotations

import argparse
import csv
import json
import os
import re
import subprocess
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Any


STAGE1_ROOT = Path(__file__).resolve().parents[1]
EXP10_ROOT = STAGE1_ROOT.parent
DEFAULT_CANDIDATES = STAGE1_ROOT / "jobs" / "candidates.json"
DEFAULT_MANIFEST = EXP10_ROOT / "dataset_manifest.json"
DEFAULT_SELECTED = EXP10_ROOT / "selected_instances"

SUMMARY_RE = re.compile(
    r">>>\s+(?P<instance>\S+)\s+\|V\|\s+(?P<V>\d+)\s+\|E\|\s+(?P<E>\d+)\s+"
    r"\(#LB\s+(?P<first_lb_time>[-\d.]+)\s+(?P<first_lb>\d+)\s+--->\s+"
    r"(?P<best_lb>\d+)\s+(?:(?P<gap_out>[-\d.]+)\s+|====\s+)"
    r"(?P<best_ub>\d+)\s+<---\s+(?P<first_ub>\d+)"
)
ROUND_RE = re.compile(r"^\s*\d+\s+[-\d]+\s+[-\d]+\s+[-\d]+", re.MULTILINE)


def csv_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def parse_ints(text: str) -> list[int]:
    out: list[int] = []
    for item in csv_list(text):
        if "-" in item:
            lo, hi = item.split("-", 1)
            out.extend(range(int(lo), int(hi) + 1))
        else:
            out.append(int(item))
    return sorted(set(out))


def load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text())


def candidate_path(base: Path, cfg: dict[str, str], key: str) -> Path:
    return base / cfg["relative_root"] / cfg[key]


def possible_instance_names(family: str, name: str) -> list[str]:
    names = [name]
    if family == "T1" and name.startswith("T1_"):
        names.append("Problem.dat_" + name.removeprefix("T1_"))
    if family == "T2" and name.startswith("T2_"):
        names.append("Problem.dat_" + name.removeprefix("T2_"))
    if family == "UDG" and name.startswith("UDG_"):
        parts = name.removesuffix(".wclq").split("_")
        if len(parts) == 4:
            n, density_code, seed = parts[1], parts[2], parts[3]
            variant = {"150": "A", "200": "B"}.get(density_code)
            if variant:
                names.append(f"UDG_{n}_{variant}_{seed}.wclq")
    return names


def resolve_instance(root: Path, family: str, name: str, allow_recursive: bool) -> Path | None:
    for candidate_name in possible_instance_names(family, name):
        direct = root / candidate_name
        if direct.exists():
            return direct
    if allow_recursive:
        wanted = set(possible_instance_names(family, name))
        for path in root.rglob("*"):
            if path.is_file() and path.name in wanted:
                return path
    return None


def load_instances(
    *,
    manifest_path: Path,
    selected_root: Path,
    datasets: list[str],
    path_mode: str,
    allow_recursive: bool,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    manifest = load_json(manifest_path)
    available: list[dict[str, str]] = []
    missing: list[dict[str, str]] = []
    key = "hpc_path" if path_mode == "hpc" else "local_path"

    for dataset in datasets:
        if dataset not in manifest:
            raise SystemExit(f"Unknown dataset {dataset}; known={sorted(manifest)}")
        root_value = manifest[dataset].get(key)
        if not root_value:
            missing.append({"family": dataset, "rank": "", "instance": "*", "path": "", "reason": f"missing {key}"})
            continue
        selected_file = selected_root / f"{dataset}.txt"
        if not selected_file.exists():
            raise SystemExit(f"Missing selected instance file: {selected_file}")
        root = Path(str(root_value))
        for rank, raw in enumerate(selected_file.read_text().splitlines(), start=1):
            name = raw.strip()
            if not name:
                continue
            path = resolve_instance(root, dataset, name, allow_recursive)
            row = {"family": dataset, "rank": str(rank), "instance": name, "path": "" if path is None else str(path)}
            if path is None:
                row["reason"] = f"not found under {root}"
                missing.append(row)
            else:
                available.append(row)
    return available, missing


def parse_output(text: str) -> dict[str, Any]:
    summary = SUMMARY_RE.search(text)
    if not summary:
        return {"parse_ok": False, "n_rounds": len(ROUND_RE.findall(text))}

    first_lb = int(summary.group("first_lb"))
    best_lb = int(summary.group("best_lb"))
    first_ub = int(summary.group("first_ub"))
    best_ub = int(summary.group("best_ub"))
    absolute_gap = max(0, best_ub - best_lb)
    return {
        "parse_ok": True,
        "V": int(summary.group("V")),
        "E": int(summary.group("E")),
        "first_lb": first_lb,
        "best_lb": best_lb,
        "lb_gain": best_lb - first_lb,
        "first_ub": first_ub,
        "verified_ub": best_ub,
        "ub_gain": first_ub - best_ub,
        "absolute_gap": absolute_gap,
        "relative_gap": (absolute_gap / best_lb) if best_lb else "",
        "solver_certified_opt": int(absolute_gap == 0),
        "n_rounds": len(ROUND_RE.findall(text)),
    }


def run_one(job: dict[str, Any]) -> dict[str, Any]:
    env = os.environ.copy()
    env["MWDS_AQ_MODE"] = job["mode_family"]
    env["DUMP_BEST_SOL"] = "1"
    cmd = [
        str(job["binary"]),
        str(job["instance_path"]),
        str(job["cutoff"]),
        str(job["actual_seed"]),
        str(job["alpha"]),
        str(job["k_ants"]),
        str(job["rho"]),
        str(job["q0"]),
        str(job["beta"]),
    ]
    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, env=env)
    output_path = Path(job["output_path"])
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(proc.stdout)
    return {
        "candidate": job["candidate"],
        "controller_label": job["controller_label"],
        "family": job["family"],
        "instance": job["instance"],
        "solver": job["solver"],
        "logical_seed": job["logical_seed"],
        "actual_seed": job["actual_seed"],
        "rep": job["rep"],
        "mode": job["mode"],
        "cutoff": job["cutoff"],
        "alpha": job["alpha"],
        "exit_code": proc.returncode,
        "raw_output": str(output_path),
        **parse_output(proc.stdout),
    }


def combine(rows: list[dict[str, Any]]) -> dict[str, Any] | None:
    valid = [row for row in rows if row.get("parse_ok") is True]
    if not valid:
        return None
    best_lb = max(int(row["best_lb"]) for row in valid)
    best_ub = min(int(row["verified_ub"]) for row in valid)
    gap = max(0, best_ub - best_lb)
    return {"best_lb": best_lb, "verified_ub": best_ub, "absolute_gap": gap, "solver_certified_opt": int(gap == 0)}


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def summarize(results: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    grouped: dict[tuple[str, str, str, str, int], list[dict[str, Any]]] = {}
    for row in results:
        key = (str(row["candidate"]), str(row["family"]), str(row["instance"]), str(row["solver"]), int(row["logical_seed"]))
        grouped.setdefault(key, []).append(row)

    fair_rows: list[dict[str, Any]] = []
    for (candidate, family, instance, solver, seed), group in sorted(grouped.items()):
        dbs = combine([row for row in group if str(row["mode"]).startswith("dbs_")])
        controller = combine([row for row in group if str(row["mode"]).startswith("controller_")])
        if dbs is None or controller is None:
            continue
        fair_rows.append(
            {
                "candidate": candidate,
                "family": family,
                "instance": instance,
                "solver": solver,
                "seed": seed,
                "dbs_best_lb": dbs["best_lb"],
                "dbs_verified_ub": dbs["verified_ub"],
                "dbs_gap": dbs["absolute_gap"],
                "dbs_solver_opt": dbs["solver_certified_opt"],
                "controller_best_lb": controller["best_lb"],
                "controller_verified_ub": controller["verified_ub"],
                "controller_gap": controller["absolute_gap"],
                "controller_solver_opt": controller["solver_certified_opt"],
                "delta_lb_controller_minus_dbs": int(controller["best_lb"]) - int(dbs["best_lb"]),
                "delta_ub_controller_minus_dbs": int(controller["verified_ub"]) - int(dbs["verified_ub"]),
                "delta_gap_controller_minus_dbs": int(controller["absolute_gap"]) - int(dbs["absolute_gap"]),
                "delta_opt_controller_minus_dbs": int(controller["solver_certified_opt"]) - int(dbs["solver_certified_opt"]),
            }
        )

    aggregate_rows: list[dict[str, Any]] = []
    by_family_rows: list[dict[str, Any]] = []
    for keys, target in [(("candidate", "solver"), aggregate_rows), (("candidate", "solver", "family"), by_family_rows)]:
        group_keys = sorted({tuple(row[key] for key in keys) for row in fair_rows})
        for group_key in group_keys:
            subset = [row for row in fair_rows if tuple(row[key] for key in keys) == group_key]
            lb_deltas = [int(row["delta_lb_controller_minus_dbs"]) for row in subset]
            ub_deltas = [int(row["delta_ub_controller_minus_dbs"]) for row in subset]
            gap_deltas = [int(row["delta_gap_controller_minus_dbs"]) for row in subset]
            opt_deltas = [int(row["delta_opt_controller_minus_dbs"]) for row in subset]
            out = dict(zip(keys, group_key, strict=True))
            out.update(
                {
                    "rows": len(subset),
                    "lb_wins": sum(delta > 0 for delta in lb_deltas),
                    "lb_ties": sum(delta == 0 for delta in lb_deltas),
                    "lb_losses": sum(delta < 0 for delta in lb_deltas),
                    "total_delta_lb": sum(lb_deltas),
                    "ub_wins": sum(delta < 0 for delta in ub_deltas),
                    "ub_ties": sum(delta == 0 for delta in ub_deltas),
                    "ub_losses": sum(delta > 0 for delta in ub_deltas),
                    "total_delta_ub": sum(ub_deltas),
                    "max_ub_regression": max(ub_deltas) if ub_deltas else 0,
                    "gap_wins": sum(delta < 0 for delta in gap_deltas),
                    "gap_ties": sum(delta == 0 for delta in gap_deltas),
                    "gap_losses": sum(delta > 0 for delta in gap_deltas),
                    "total_delta_gap": sum(gap_deltas),
                    "total_delta_opt": sum(opt_deltas),
                }
            )
            target.append(out)
    return fair_rows, aggregate_rows, by_family_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidate", required=True)
    parser.add_argument("--candidate-root-base", type=Path, required=True)
    parser.add_argument("--candidate-config", type=Path, default=DEFAULT_CANDIDATES)
    parser.add_argument("--dataset-manifest", type=Path, default=DEFAULT_MANIFEST)
    parser.add_argument("--selected-root", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--datasets", default="T1,T2,UDG,BHOSLIB,DIMACS,DIMACS10,NDR,SNAP")
    parser.add_argument("--path-mode", choices=["hpc", "local"], default="hpc")
    parser.add_argument("--allow-recursive-resolve", action="store_true")
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--cutoff", type=int, default=20)
    parser.add_argument("--alpha", type=int, default=90)
    parser.add_argument("--workers", type=int, default=5)
    parser.add_argument("--k-ants", type=int, default=5)
    parser.add_argument("--rho", type=float, default=0.05)
    parser.add_argument("--q0", type=float, default=0.90)
    parser.add_argument("--deep-beta", type=float, default=3.0)
    parser.add_argument("--fast-beta", type=float, default=3.5)
    args = parser.parse_args()

    configs = load_json(args.candidate_config)
    if args.candidate not in configs:
        raise SystemExit(f"Unknown candidate {args.candidate}; known={sorted(configs)}")
    cfg = configs[args.candidate]
    deep_binary = candidate_path(args.candidate_root_base, cfg, "deep_binary")
    fast_binary = candidate_path(args.candidate_root_base, cfg, "fast_binary")
    for binary in [deep_binary, fast_binary]:
        if not binary.exists():
            raise SystemExit(f"Missing binary: {binary}")

    available, missing = load_instances(
        manifest_path=args.dataset_manifest,
        selected_root=args.selected_root,
        datasets=csv_list(args.datasets),
        path_mode=args.path_mode,
        allow_recursive=args.allow_recursive_resolve,
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "available_instances.csv", available, ["family", "rank", "instance", "path"])
    write_csv(args.output_dir / "missing_instances.csv", missing, ["family", "rank", "instance", "path", "reason"])

    seeds = parse_ints(args.seeds)
    raw_dir = args.output_dir / "raw"
    jobs: list[dict[str, Any]] = []
    for inst in available:
        for solver, binary, beta in [("deep-v6", deep_binary, args.deep_beta), ("fast-v19", fast_binary, args.fast_beta)]:
            for logical_seed in seeds:
                for rep in range(1, args.reps + 1):
                    actual_seed = logical_seed + (rep - 1) * 100
                    for mode_family, mode_prefix in [("dbs", "dbs"), ("guarded", "controller")]:
                        mode = f"{mode_prefix}_rep{rep}"
                        jobs.append(
                            {
                                **inst,
                                "candidate": args.candidate,
                                "controller_label": cfg.get("label", args.candidate),
                                "solver": solver,
                                "binary": binary,
                                "logical_seed": logical_seed,
                                "actual_seed": actual_seed,
                                "rep": rep,
                                "mode_family": mode_family,
                                "mode": mode,
                                "instance_path": inst["path"],
                                "cutoff": args.cutoff,
                                "alpha": args.alpha,
                                "k_ants": args.k_ants,
                                "rho": args.rho,
                                "q0": args.q0,
                                "beta": beta,
                                "output_path": raw_dir / f"{args.candidate}__{inst['family']}__{inst['instance']}__{solver}__{mode}__s{actual_seed}.out",
                            }
                        )

    results: list[dict[str, Any]] = []
    with ThreadPoolExecutor(max_workers=args.workers) as executor:
        for future in as_completed([executor.submit(run_one, job) for job in jobs]):
            row = future.result()
            results.append(row)
            print(row, flush=True)

    run_fields = [
        "candidate", "controller_label", "family", "instance", "solver", "logical_seed", "actual_seed",
        "rep", "mode", "cutoff", "alpha", "exit_code", "parse_ok", "V", "E", "first_lb", "best_lb",
        "lb_gain", "first_ub", "verified_ub", "ub_gain", "absolute_gap", "relative_gap",
        "solver_certified_opt", "n_rounds", "raw_output",
    ]
    write_csv(args.output_dir / "layer_a_runs.csv", results, run_fields)
    fair_rows, aggregate_rows, by_family_rows = summarize(results)
    write_csv(args.output_dir / "layer_a_fair_summary.csv", fair_rows, list(fair_rows[0].keys()) if fair_rows else ["candidate"])
    write_csv(args.output_dir / "layer_a_fair_aggregate.csv", aggregate_rows, list(aggregate_rows[0].keys()) if aggregate_rows else ["candidate"])
    write_csv(args.output_dir / "layer_a_fair_aggregate_by_family.csv", by_family_rows, list(by_family_rows[0].keys()) if by_family_rows else ["candidate"])

    manifest = {
        "candidate": args.candidate,
        "controller_label": cfg.get("label", args.candidate),
        "datasets": csv_list(args.datasets),
        "seeds": seeds,
        "reps": args.reps,
        "cutoff": args.cutoff,
        "alpha": args.alpha,
        "jobs": len(jobs),
        "available_instances": len(available),
        "missing_instances": len(missing),
        "deep_binary": str(deep_binary),
        "fast_binary": str(fast_binary),
        "external_certificates_applied": False,
        "known_opt_used": False,
    }
    (args.output_dir / "artifact_manifest.json").write_text(json.dumps(manifest, indent=2, sort_keys=True))
    print(json.dumps(manifest, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
