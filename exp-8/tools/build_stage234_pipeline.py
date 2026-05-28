#!/usr/bin/env python3
"""Build an exp-8 cumulative Stage2/3/4 certification workspace.

This tool is intentionally conservative. It never treats historical appendix
values or solver CSV values as verified certificates. It creates the canonical
exp-8 Layer-A table, records which historical baseline fields are comparable,
audits whether raw outputs contain verifiable UB solution dumps, and emits
Stage2/3/4 cumulative tables. Rows are only changed when a verified artifact is
provided through an input CSV.
"""

from __future__ import annotations

import csv
import json
import re
from collections import defaultdict
from pathlib import Path
from typing import Iterable


EXP8_ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = EXP8_ROOT / "stage234"
DEEP_CSV = EXP8_ROOT / "deep-v6" / "sumup" / "analysis" / "exp8_deep_lb_results.csv"
FAST_CSV = EXP8_ROOT / "fast-v19" / "sumup" / "analysis" / "exp8_v19_lb_results.csv"
BASELINE_INDEX = EXP8_ROOT / "baseline_index.csv"
SELECTED_SUMMARY = EXP8_ROOT / "selected_instances_summary.csv"
DATASET_MANIFEST = EXP8_ROOT / "dataset_manifest.json"

BEST_SOLUTION_RE = re.compile(r"\[BestSolution\]\s+size=\d+\s+cost=\d+\s+vertices=")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def intish(value: str | int | float | None, default: int = 0) -> int:
    if value in (None, ""):
        return default
    return int(float(value))


def floatish(value: str | int | float | None, default: float = 0.0) -> float:
    if value in (None, ""):
        return default
    return float(value)


def fmt_num(value: float | int) -> str:
    value_f = float(value)
    if value_f.is_integer():
        return str(int(value_f))
    return f"{value_f:.12g}"


def read_selected() -> dict[tuple[str, str], dict[str, str]]:
    manifest = json.loads(DATASET_MANIFEST.read_text())
    summary = {
        (row["dataset"], row["instance"]): row
        for row in read_csv(SELECTED_SUMMARY)
    }
    out: dict[tuple[str, str], dict[str, str]] = {}
    for selected_file in sorted((EXP8_ROOT / "selected_instances").glob("*.txt")):
        dataset = selected_file.stem
        info = manifest[dataset]
        names = [line.strip() for line in selected_file.read_text().splitlines() if line.strip()]
        for name in names:
            local_base = info.get("local_path") or ""
            local_path = str(Path(local_base) / name) if local_base else ""
            hpc_path = str(Path(info["hpc_path"]) / name)
            if dataset == "NDR":
                hpc_path = str(Path(info["hpc_path"]) / "**" / name)
            row = dict(summary.get((dataset, name), {}))
            row.update(
                {
                    "dataset": dataset,
                    "instance": name,
                    "format": info.get("format", ""),
                    "extension": info.get("extension", ""),
                    "local_instance_path": local_path,
                    "local_instance_exists": str(bool(local_path and Path(local_path).exists())),
                    "hpc_instance_path": hpc_path,
                }
            )
            out[(dataset, name)] = row
    return out


def read_instance_stats() -> dict[tuple[str, str], dict[str, str]]:
    stats: dict[tuple[str, str], dict[str, str]] = {}
    for path in [DEEP_CSV, FAST_CSV]:
        for row in read_csv(path):
            key = (row["dataset"], row["instance"])
            if key not in stats:
                stats[key] = {"V": row.get("V", ""), "E": row.get("E", "")}
            else:
                if not stats[key].get("V") and row.get("V"):
                    stats[key]["V"] = row["V"]
                if not stats[key].get("E") and row.get("E"):
                    stats[key]["E"] = row["E"]
    return stats


def build_base_rows(selected: dict[tuple[str, str], dict[str, str]]) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for solver, family, path in [
        ("deep-v6", "deep", DEEP_CSV),
        ("fast-v19", "fast", FAST_CSV),
    ]:
        for row in read_csv(path):
            key = (row["dataset"], row["instance"])
            info = selected.get(key, {})
            best_lb = intish(row["best_lb"])
            best_ub = intish(row["best_ub"])
            gap = best_ub - best_lb
            rows.append(
                {
                    "dataset": row["dataset"],
                    "instance": row["instance"],
                    "solver_family": family,
                    "solver": solver,
                    "seed": row["seed"],
                    "V": row.get("V", ""),
                    "E": row.get("E", ""),
                    "first_lb": row.get("first_lb", ""),
                    "best_lb": best_lb,
                    "first_ub": row.get("first_ub", ""),
                    "best_ub": best_ub,
                    "reported_gap": row.get("gap", ""),
                    "absolute_gap": gap,
                    "status": row.get("status", ""),
                    "n_rounds": row.get("n_rounds", ""),
                    "timestamp": row.get("timestamp", ""),
                    "lb_gain": row.get("lb_gain", ""),
                    "instance_format": info.get("format", ""),
                    "local_instance_path": info.get("local_instance_path", ""),
                    "local_instance_exists": info.get("local_instance_exists", "False"),
                    "hpc_instance_path": info.get("hpc_instance_path", ""),
                    "pipeline_base_lb": best_lb,
                    "pipeline_base_ub": best_ub,
                    "pipeline_best_lb": best_lb,
                    "pipeline_best_ub": best_ub,
                    "pipeline_delta_lb": 0,
                    "pipeline_delta_ub": 0,
                    "pipeline_base_absolute_gap": gap,
                    "pipeline_absolute_gap": gap,
                    "pipeline_delta_absolute_gap": 0,
                    "pipeline_certified_opt": int(gap == 0),
                    "pipeline_new_certified_opt": 0,
                    "stage2_lb_applied": 0,
                    "stage3_ub_applied": 0,
                    "stage4_exact_applied": 0,
                }
            )
    return rows


def build_baseline_comparator(base_rows: list[dict[str, object]]) -> list[dict[str, object]]:
    baseline = {
        (row["dataset"], row["family"], row["baseline_solver"], row["instance"]): row
        for row in read_csv(BASELINE_INDEX)
    }
    solvers_by_family = {
        "deep": ["dualdeep", "deepOpt"],
        "fast": ["dualcc2v3", "cc2v3"],
    }
    instance_rows = {
        (str(row["dataset"]), str(row["instance"]), str(row["solver_family"]), str(row["solver"])): row
        for row in base_rows
    }
    out: list[dict[str, object]] = []
    for (dataset, instance, family, solver), row in sorted(instance_rows.items()):
        for baseline_solver in solvers_by_family[family]:
            b = baseline.get((dataset, family, baseline_solver, instance))
            if not b:
                comparable = "missing"
                reason = "no historical row"
                delta_lb = delta_gap = ""
                wtl_lb = wtl_gap = "n/a"
            else:
                has_lb = b.get("has_lb_summary") == "1"
                has_gap = b.get("final_gap_mean") not in ("", None)
                comparable = "reliable_lb" if has_lb else ("gap_only" if has_gap else "not_comparable")
                reason = (
                    "explicit summary LB"
                    if has_lb
                    else ("appendix final_gap_mean only" if has_gap else "simple appendix value is not LB/UB")
                )
                if has_lb:
                    baseline_lb = floatish(b.get("best_lb_max"))
                    delta_lb = floatish(row["pipeline_best_lb"]) - baseline_lb
                    wtl_lb = "win" if delta_lb > 0 else ("loss" if delta_lb < 0 else "tie")
                else:
                    delta_lb = ""
                    wtl_lb = "n/a"
                if has_gap:
                    baseline_gap = floatish(b.get("final_gap_mean"))
                    delta_gap = floatish(row["pipeline_absolute_gap"]) - baseline_gap
                    wtl_gap = "win" if delta_gap < 0 else ("loss" if delta_gap > 0 else "tie")
                else:
                    delta_gap = ""
                    wtl_gap = "n/a"
            out.append(
                {
                    "dataset": dataset,
                    "instance": instance,
                    "solver": solver,
                    "solver_family": family,
                    "baseline_solver": baseline_solver,
                    "comparability": comparable,
                    "reason": reason,
                    "our_best_lb": row["pipeline_best_lb"],
                    "our_best_ub": row["pipeline_best_ub"],
                    "our_absolute_gap": row["pipeline_absolute_gap"],
                    "baseline_best_lb_max": b.get("best_lb_max", "") if b else "",
                    "baseline_best_ub_min": b.get("best_ub_min", "") if b else "",
                    "baseline_final_gap_mean": b.get("final_gap_mean", "") if b else "",
                    "delta_lb_vs_baseline": fmt_num(delta_lb) if delta_lb != "" else "",
                    "delta_gap_vs_baseline": fmt_num(delta_gap) if delta_gap != "" else "",
                    "lb_wtl": wtl_lb,
                    "gap_wtl": wtl_gap,
                }
            )
    return out


def audit_raw_dumps() -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for solver_dir in ["deep-v6", "fast-v19"]:
        for path in sorted((EXP8_ROOT / solver_dir / "jobs" / "result").glob("**/*.out")):
            text = path.read_text(errors="ignore")
            rows.append(
                {
                    "solver_dir": solver_dir,
                    "raw_output": str(path.relative_to(EXP8_ROOT)),
                    "has_best_solution_dump": int(bool(BEST_SOLUTION_RE.search(text))),
                    "has_summary_line": int(">>>" in text),
                }
            )
    return rows


def write_certificate_plan(
    selected: dict[tuple[str, str], dict[str, str]],
    instance_stats: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, object]]:
    rows: list[dict[str, object]] = []
    for (dataset, instance), info in sorted(selected.items()):
        stats = instance_stats.get((dataset, instance), {})
        V = intish(info.get("V") or stats.get("V") or 0)
        E = intish(info.get("E") or stats.get("E") or 0)
        local_exists = info.get("local_instance_exists") == "True"
        if not local_exists:
            action = "needs_hpc_or_local_instance"
        elif V and V <= 1200 and E and E <= 50000:
            action = "eligible_full_lp_dual"
        elif V and V <= 5000:
            action = "consider_restricted_or_time_limited_lp"
        else:
            action = "skip_size_for_initial_pass"
        rows.append(
            {
                "dataset": dataset,
                "instance": instance,
                "V": V or "",
                "E": E or "",
                "local_instance_path": info.get("local_instance_path", ""),
                "local_instance_exists": info.get("local_instance_exists", "False"),
                "hpc_instance_path": info.get("hpc_instance_path", ""),
                "stage2_action": action,
                "certificate_path": "",
                "verified_floor": "",
                "applied": 0,
            }
        )
    return rows


def clone_rows(rows: Iterable[dict[str, object]]) -> list[dict[str, object]]:
    return [dict(row) for row in rows]


def exact_closure_plan(
    rows: list[dict[str, object]],
    selected: dict[tuple[str, str], dict[str, str]],
    instance_stats: dict[tuple[str, str], dict[str, str]],
) -> list[dict[str, object]]:
    best_by_instance: dict[tuple[str, str], int] = {}
    for row in rows:
        key = (str(row["dataset"]), str(row["instance"]))
        gap = intish(row["pipeline_absolute_gap"])
        best_by_instance[key] = min(gap, best_by_instance.get(key, gap))
    out: list[dict[str, object]] = []
    for (dataset, instance), gap in sorted(best_by_instance.items(), key=lambda item: (item[1], item[0])):
        info = selected.get((dataset, instance), {})
        stats = instance_stats.get((dataset, instance), {})
        V = intish(info.get("V") or stats.get("V") or 0)
        E = intish(info.get("E") or stats.get("E") or 0)
        local_exists = info.get("local_instance_exists") == "True"
        if gap == 0:
            action = "already_closed_by_solver"
        elif not local_exists:
            action = "needs_instance_file"
        elif V and V <= 1200 and E and E <= 50000:
            action = "try_full_milp_opt_certificate"
        elif gap <= 10:
            action = "try_bounded_cost_or_restricted_infeas"
        else:
            action = "defer_large_gap_or_large_instance"
        out.append(
            {
                "dataset": dataset,
                "instance": instance,
                "best_current_gap": gap,
                "V": V or "",
                "E": E or "",
                "local_instance_exists": info.get("local_instance_exists", "False"),
                "stage4_action": action,
                "certificate_path": "",
                "verified_opt": "",
                "applied": 0,
            }
        )
    return out


def summarise(rows: list[dict[str, object]], version: str) -> dict[str, object]:
    certified = sum(intish(row["pipeline_certified_opt"]) for row in rows)
    new_certified = sum(intish(row["pipeline_new_certified_opt"]) for row in rows)
    delta_lb = sum(intish(row["pipeline_delta_lb"]) for row in rows)
    delta_ub = sum(intish(row["pipeline_delta_ub"]) for row in rows)
    delta_gap = sum(intish(row["pipeline_delta_absolute_gap"]) for row in rows)
    lb_gt_ub = sum(1 for row in rows if intish(row["pipeline_best_lb"]) > intish(row["pipeline_best_ub"]))
    return {
        "version": version,
        "rows": len(rows),
        "certified_total": certified,
        "new_certified_total": new_certified,
        "open_rows": len(rows) - certified,
        "lb_gt_ub_rows": lb_gt_ub,
        "total_delta_lb": delta_lb,
        "total_delta_ub": delta_ub,
        "total_delta_gap": delta_gap,
    }


def family_summary(rows: list[dict[str, object]]) -> list[dict[str, object]]:
    grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
    for row in rows:
        grouped[str(row["dataset"])].append(row)
    out: list[dict[str, object]] = []
    for dataset, items in sorted(grouped.items()):
        summary = summarise(items, dataset)
        summary["family"] = dataset
        del summary["version"]
        out.append(summary)
    return out


def count_by(rows: list[dict[str, object]], key: str) -> dict[str, int]:
    counts: dict[str, int] = defaultdict(int)
    for row in rows:
        counts[str(row.get(key, ""))] += 1
    return dict(sorted(counts.items()))


def write_report(
    version_rows: list[dict[str, object]],
    baseline_rows: list[dict[str, object]],
    stage2_plan: list[dict[str, object]],
    raw_audit: list[dict[str, object]],
    stage4_plan: list[dict[str, object]],
) -> None:
    dump_count = sum(intish(row["has_best_solution_dump"]) for row in raw_audit)
    raw_count = len(raw_audit)
    baseline_counts = count_by(baseline_rows, "comparability")
    stage2_counts = count_by(stage2_plan, "stage2_action")
    stage4_counts = count_by(stage4_plan, "stage4_action")

    def bullet_counts(counts: dict[str, int]) -> str:
        return "\n".join(f"- `{key}`: {value}" for key, value in counts.items()) or "- none"

    report = f"""# exp-8 Stage234 Cumulative Pipeline

This report is scoped to `WMDS26/exp-8`. It does not reuse the numeric
v071/v082/v084 results from `MWDS26.2`; those covered a different pressure
suite.

## Version Summary

| version | rows | certified | new certified | open | delta LB | delta UB | delta gap | LB>UB |
|---|---:|---:|---:|---:|---:|---:|---:|---:|
"""
    for row in version_rows:
        report += (
            f"| {row['version']} | {row['rows']} | {row['certified_total']} | "
            f"{row['new_certified_total']} | {row['open_rows']} | {row['total_delta_lb']} | "
            f"{row['total_delta_ub']} | {row['total_delta_gap']} | {row['lb_gt_ub_rows']} |\n"
        )
    report += f"""
## Stage Status

- `+ACO` base table has been materialized from the exp-8 deep/fast CSVs.
- `+verified LB certificate` is planned per instance, but no new exp-8
  certificate artifact was applied by this build.
- `+verified UB portfolio` is blocked for existing raw outputs because
  `{dump_count}` of `{raw_count}` raw output files contain a `[BestSolution]`
  vertex dump.
- `+exact closure` is planned only for rows with small gap and available
  instance files; no new exp-8 exact certificate was applied by this build.

## Baseline Comparability

{bullet_counts(baseline_counts)}

Rows marked `not_comparable` are mostly appendix simple-value rows and are not
used as LB/UB/certified-opt evidence.

## Stage2 Plan Counts

{bullet_counts(stage2_counts)}

## Stage4 Plan Counts

{bullet_counts(stage4_counts)}

## Files

- `exp8_pipeline_base.csv`
- `baseline_comparator.csv`
- `stage2_certificate_plan.csv`
- `stage2_lb_certified.csv`
- `raw_dump_audit.csv`
- `stage3_ub_portfolio_plan.csv`
- `stage3_ub_verified.csv`
- `stage4_exact_closure_plan.csv`
- `stage4_exact_closed.csv`
- `version_summary.csv`
- `family_summary.csv`

## Interpretation Boundary

The current exp-8 artifacts support a strict setup, but not yet a completed
Stage3/Stage4 application. Any future LB/UB/OPT improvement must be backed by
new exp-8-specific certificate or verified solution artifacts.

## Next Execution Boundary

To turn planned Stage2/3/4 rows into applied rows, run the certificate tools on
the exp-8 instance files on HPC or copy the instance files locally, then rebuild
this workspace after adding verified artifact manifests. Do not apply UB or OPT
updates from numeric CSV values alone.
"""
    (OUT_DIR / "REPORT.md").write_text(report)


def main() -> int:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    selected = read_selected()
    instance_stats = read_instance_stats()
    base_rows = build_base_rows(selected)
    base_fields = list(base_rows[0].keys())
    write_csv(OUT_DIR / "exp8_pipeline_base.csv", base_rows, base_fields)

    baseline_rows = build_baseline_comparator(base_rows)
    write_csv(OUT_DIR / "baseline_comparator.csv", baseline_rows, list(baseline_rows[0].keys()))

    stage2_plan = write_certificate_plan(selected, instance_stats)
    write_csv(OUT_DIR / "stage2_certificate_plan.csv", stage2_plan, list(stage2_plan[0].keys()))

    stage2_rows = clone_rows(base_rows)
    write_csv(OUT_DIR / "stage2_lb_certified.csv", stage2_rows, base_fields)

    raw_audit = audit_raw_dumps()
    write_csv(OUT_DIR / "raw_dump_audit.csv", raw_audit, list(raw_audit[0].keys()) if raw_audit else ["solver_dir", "raw_output", "has_best_solution_dump", "has_summary_line"])

    stage3_plan = [
        {
            "dataset": dataset,
            "instance": instance,
            "stage3_action": "needs_new_dump_run_or_hpc_artifact",
            "reason": "existing exp-8 raw outputs have no [BestSolution] vertex dump",
            "verified_dump_path": "",
            "verified_ub": "",
            "applied": 0,
        }
        for dataset, instance in sorted(selected)
    ]
    write_csv(OUT_DIR / "stage3_ub_portfolio_plan.csv", stage3_plan, list(stage3_plan[0].keys()))
    stage3_rows = clone_rows(stage2_rows)
    write_csv(OUT_DIR / "stage3_ub_verified.csv", stage3_rows, base_fields)

    stage4_plan = exact_closure_plan(stage3_rows, selected, instance_stats)
    write_csv(OUT_DIR / "stage4_exact_closure_plan.csv", stage4_plan, list(stage4_plan[0].keys()))
    stage4_rows = clone_rows(stage3_rows)
    write_csv(OUT_DIR / "stage4_exact_closed.csv", stage4_rows, base_fields)

    version_rows = [
        summarise(base_rows, "plus_aco"),
        summarise(stage2_rows, "plus_verified_lb_certificate"),
        summarise(stage3_rows, "plus_verified_ub_portfolio"),
        summarise(stage4_rows, "plus_exact_closure"),
    ]
    write_csv(OUT_DIR / "version_summary.csv", version_rows, list(version_rows[0].keys()))
    fam_rows = family_summary(stage4_rows)
    write_csv(OUT_DIR / "family_summary.csv", fam_rows, ["family", "rows", "certified_total", "new_certified_total", "open_rows", "lb_gt_ub_rows", "total_delta_lb", "total_delta_ub", "total_delta_gap"])
    write_report(version_rows, baseline_rows, stage2_plan, raw_audit, stage4_plan)
    print(f"wrote exp-8 Stage234 workspace to {OUT_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
