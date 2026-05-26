#!/usr/bin/env python3
"""Reference sanity check for the selected Stage-1 candidate.

This compares the selected controller mode against original reference binaries.
It is intentionally separate from `check_results.py`, which evaluates
within-candidate DBS-vs-controller effects.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

MAX_REASONABLE_OBJECTIVE = 10**12


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def csv_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def mode_matches(row: dict[str, str], mode_prefix: str) -> bool:
    if mode_prefix == "all":
        return True
    return row.get("mode", "").startswith(mode_prefix + "_")


def build_records(path: Path, *, mode_prefix: str, datasets: set[str]) -> tuple[dict[tuple[str, str, str, str], dict[str, int]], list[str]]:
    rows = read_csv(path / "layer_a_runs.csv")
    warnings: list[str] = []
    if not rows:
        return {}, [f"{path}: missing or empty layer_a_runs.csv"]

    grouped: dict[tuple[str, str, str, str], list[dict[str, str]]] = {}
    ignored_sentinels: set[tuple[str, str, str, str]] = set()
    for row in rows:
        if datasets and row.get("family", "") not in datasets:
            continue
        if not mode_matches(row, mode_prefix):
            continue
        best_lb = as_int(row.get("best_lb"))
        verified_ub = as_int(row.get("verified_ub"))
        if best_lb >= MAX_REASONABLE_OBJECTIVE or verified_ub >= MAX_REASONABLE_OBJECTIVE:
            sentinel_key = (row.get("family", ""), row.get("instance", ""), row.get("solver", ""), row.get("logical_seed", ""))
            if sentinel_key not in ignored_sentinels:
                warnings.append(
                    f"{path.name}: ignored sentinel objective for "
                    f"{row.get('family', '')}/{row.get('instance', '')}/{row.get('solver', '')}/seed={row.get('logical_seed', '')}"
                )
                ignored_sentinels.add(sentinel_key)
            continue
        key = (row.get("family", ""), row.get("instance", ""), row.get("solver", ""), row.get("logical_seed", ""))
        grouped.setdefault(key, []).append(row)

    records: dict[tuple[str, str, str, str], dict[str, int]] = {}
    for key, group in grouped.items():
        valid = [row for row in group if as_bool(row.get("parse_ok")) and as_int(row.get("exit_code")) == 0]
        if not valid:
            warnings.append(f"{path.name}: no valid rows for {key}")
            continue
        best_lb = max(as_int(row.get("best_lb")) for row in valid)
        best_ub = min(as_int(row.get("verified_ub")) for row in valid)
        gap = max(0, best_ub - best_lb)
        records[key] = {
            "best_lb": best_lb,
            "verified_ub": best_ub,
            "absolute_gap": gap,
            "solver_certified_opt": int(gap == 0),
        }
    return records, warnings


def compare_records(
    selected: dict[tuple[str, str, str, str], dict[str, int]],
    reference: dict[tuple[str, str, str, str], dict[str, int]],
) -> tuple[list[dict[str, Any]], list[str]]:
    rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    common = sorted(set(selected) & set(reference))
    missing_selected = sorted(set(reference) - set(selected))
    missing_reference = sorted(set(selected) - set(reference))
    if missing_selected:
        warnings.append(f"missing selected records: {len(missing_selected)}")
    if missing_reference:
        warnings.append(f"missing reference records: {len(missing_reference)}")

    for family, instance, solver, seed in common:
        sel = selected[(family, instance, solver, seed)]
        ref = reference[(family, instance, solver, seed)]
        rows.append(
            {
                "family": family,
                "instance": instance,
                "solver": solver,
                "logical_seed": seed,
                "selected_best_lb": sel["best_lb"],
                "reference_best_lb": ref["best_lb"],
                "delta_lb_selected_minus_reference": sel["best_lb"] - ref["best_lb"],
                "selected_verified_ub": sel["verified_ub"],
                "reference_verified_ub": ref["verified_ub"],
                "delta_ub_selected_minus_reference": sel["verified_ub"] - ref["verified_ub"],
                "selected_gap": sel["absolute_gap"],
                "reference_gap": ref["absolute_gap"],
                "delta_gap_selected_minus_reference": sel["absolute_gap"] - ref["absolute_gap"],
                "delta_opt_selected_minus_reference": sel["solver_certified_opt"] - ref["solver_certified_opt"],
            }
        )
    return rows, warnings


def aggregate(rows: list[dict[str, Any]], *, label: str) -> list[dict[str, Any]]:
    group_keys = sorted({(row["solver"],) for row in rows})
    out: list[dict[str, Any]] = []
    for (solver,) in group_keys:
        subset = [row for row in rows if row["solver"] == solver]
        lb = [as_int(row["delta_lb_selected_minus_reference"]) for row in subset]
        ub = [as_int(row["delta_ub_selected_minus_reference"]) for row in subset]
        gap = [as_int(row["delta_gap_selected_minus_reference"]) for row in subset]
        opt = [as_int(row["delta_opt_selected_minus_reference"]) for row in subset]
        out.append(
            {
                "comparison": label,
                "solver": solver,
                "rows": len(subset),
                "lb_wins": sum(delta > 0 for delta in lb),
                "lb_ties": sum(delta == 0 for delta in lb),
                "lb_losses": sum(delta < 0 for delta in lb),
                "total_delta_lb": sum(lb),
                "gap_wins": sum(delta < 0 for delta in gap),
                "gap_ties": sum(delta == 0 for delta in gap),
                "gap_losses": sum(delta > 0 for delta in gap),
                "total_delta_gap": sum(gap),
                "ub_wins": sum(delta < 0 for delta in ub),
                "ub_ties": sum(delta == 0 for delta in ub),
                "ub_losses": sum(delta > 0 for delta in ub),
                "max_ub_regression": max(ub) if ub else 0,
                "total_delta_opt": sum(opt),
            }
        )
    return out


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-result", type=Path, default=Path("../../sumup/result/v006"))
    parser.add_argument("--reference-result", type=Path, default=Path("../../sumup/reference_result"))
    parser.add_argument("--output", type=Path, default=Path("reference_check_report.md"))
    parser.add_argument("--selected", default="v006")
    parser.add_argument("--selected-mode", default="controller")
    parser.add_argument("--references", default="reference,baseline")
    parser.add_argument("--reference-mode", default="dbs")
    parser.add_argument("--datasets", default="T1,T2,UDG,BHOSLIB,DIMACS,NDR")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    datasets = set(csv_list(args.datasets))
    selected_records, warnings = build_records(args.selected_result, mode_prefix=args.selected_mode, datasets=datasets)
    lines = ["# Stage 1 Reference Check", ""]
    lines.append(f"- selected: {args.selected} ({args.selected_mode}) from {args.selected_result}")
    lines.append(f"- reference_root: {args.reference_result}")
    lines.append(f"- references: {args.references}")
    lines.append(f"- reference_mode: {args.reference_mode}")
    lines.append(f"- datasets: {','.join(sorted(datasets))}")
    lines.append("")

    failures: list[str] = []
    all_summary: list[dict[str, Any]] = []
    for ref_name in csv_list(args.references):
        ref_records, ref_warnings = build_records(args.reference_result / ref_name, mode_prefix=args.reference_mode, datasets=datasets)
        warnings.extend(ref_warnings)
        rows, compare_warnings = compare_records(selected_records, ref_records)
        warnings.extend(f"{ref_name}: {item}" for item in compare_warnings)
        summary = aggregate(rows, label=f"{args.selected}_vs_{ref_name}")
        all_summary.extend(summary)

        lines.append(f"## {args.selected} vs {ref_name}")
        lines.append("")
        lines.append("Summary:")
        for row in summary:
            lines.append(
                "- {solver}: rows={rows}, total_delta_lb={lb}, total_delta_gap={gap}, "
                "lb_wins/ties/losses={lw}/{lt}/{ll}, gap_wins/ties/losses={gw}/{gt}/{gl}, max_ub_regression={ub}".format(
                    solver=row["solver"],
                    rows=row["rows"],
                    lb=row["total_delta_lb"],
                    gap=row["total_delta_gap"],
                    lw=row["lb_wins"],
                    lt=row["lb_ties"],
                    ll=row["lb_losses"],
                    gw=row["gap_wins"],
                    gt=row["gap_ties"],
                    gl=row["gap_losses"],
                    ub=row["max_ub_regression"],
                )
            )
            if as_int(row["total_delta_lb"]) <= 0:
                failures.append(f"{args.selected} vs {ref_name}/{row['solver']}: total_delta_lb <= 0 ({row['total_delta_lb']})")
            if as_int(row["total_delta_gap"]) >= 0:
                failures.append(f"{args.selected} vs {ref_name}/{row['solver']}: total_delta_gap >= 0 ({row['total_delta_gap']})")
        lines.append("")

    lines.append("## Warnings")
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    lines.append("")
    lines.append("## Result")
    lines.extend([f"- FAILURE: {item}" for item in failures] or ["- PASS"])
    lines.append("")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    report = "\n".join(lines)
    args.output.write_text(report + "\n")
    print(report)

    if all_summary:
        write_csv(
            args.output.with_suffix(".csv"),
            all_summary,
            [
                "comparison", "solver", "rows", "lb_wins", "lb_ties", "lb_losses", "total_delta_lb",
                "gap_wins", "gap_ties", "gap_losses", "total_delta_gap", "ub_wins", "ub_ties",
                "ub_losses", "max_ub_regression", "total_delta_opt",
            ],
        )
    if args.strict and failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
