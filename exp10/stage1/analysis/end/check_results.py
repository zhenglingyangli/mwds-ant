#!/usr/bin/env python3
"""Strict gates for exp10 Stage-1 result directories.

The strict gate is applied to the core screen. Large stress families are
reported separately so resource-heavy instances do not hide the Layer-A signal.
"""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any

DEFAULT_STRESS_FAMILIES = "DIMACS10,SNAP"


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


def find_candidate_dirs(root: Path) -> list[Path]:
    if (root / "layer_a_runs.csv").exists():
        return [root]
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_runs.csv").exists())


def in_scope(row: dict[str, str], stress_families: set[str], *, stress: bool) -> bool:
    family = row.get("family", "")
    return family in stress_families if stress else family not in stress_families


def summarize_fair(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    group_keys = sorted({(row.get("candidate", ""), row.get("solver", "")) for row in rows})
    out_rows: list[dict[str, Any]] = []
    for candidate, solver in group_keys:
        subset = [row for row in rows if (row.get("candidate", ""), row.get("solver", "")) == (candidate, solver)]
        lb_deltas = [as_int(row.get("delta_lb_controller_minus_dbs")) for row in subset]
        ub_deltas = [as_int(row.get("delta_ub_controller_minus_dbs")) for row in subset]
        gap_deltas = [as_int(row.get("delta_gap_controller_minus_dbs")) for row in subset]
        opt_deltas = [as_int(row.get("delta_opt_controller_minus_dbs")) for row in subset]
        out_rows.append(
            {
                "candidate": candidate,
                "solver": solver,
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
    return out_rows


def check_scope(
    *,
    runs: list[dict[str, str]],
    fair: list[dict[str, str]],
    by_family: list[dict[str, str]],
    stress_families: set[str],
    stress: bool,
    max_ub_regression: int,
    require_lb_positive: bool,
) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    scoped_runs = [row for row in runs if in_scope(row, stress_families, stress=stress)]
    scoped_fair = [row for row in fair if in_scope(row, stress_families, stress=stress)]
    scoped_by_family = [row for row in by_family if in_scope(row, stress_families, stress=stress)]
    aggregate = summarize_fair(scoped_fair)
    issue_target = failures

    if not scoped_fair:
        issue_target.append("missing or empty scoped layer_a_fair_summary rows")
        return failures, warnings

    parse_failures = [row for row in scoped_runs if not as_bool(row.get("parse_ok"))]
    nonzero_exit = [row for row in scoped_runs if as_int(row.get("exit_code")) != 0]
    if parse_failures:
        issue_target.append(f"parse failures: {len(parse_failures)}")
    if nonzero_exit:
        issue_target.append(f"non-zero exits: {len(nonzero_exit)}")

    grouped: dict[tuple[str, str, str, str, str], dict[str, int]] = {}
    for row in scoped_runs:
        key = (
            row.get("candidate", ""),
            row.get("family", ""),
            row.get("instance", ""),
            row.get("solver", ""),
            row.get("logical_seed", ""),
        )
        bucket = grouped.setdefault(key, {"dbs": 0, "controller": 0})
        mode = row.get("mode", "")
        if mode.startswith("dbs_"):
            bucket["dbs"] += 1
        elif mode.startswith("controller_"):
            bucket["controller"] += 1
    unfair = {key: value for key, value in grouped.items() if value["dbs"] != value["controller"]}
    if unfair:
        issue_target.append(f"unequal dbs/controller run counts: {len(unfair)} groups")

    for row in aggregate:
        candidate = str(row.get("candidate", "?"))
        solver = str(row.get("solver", "?"))
        label = f"{candidate}/{solver}"
        total_delta_lb = as_int(row.get("total_delta_lb"))
        total_delta_gap = as_int(row.get("total_delta_gap"))
        total_delta_opt = as_int(row.get("total_delta_opt"))
        lb_wins = as_int(row.get("lb_wins"))
        lb_losses = as_int(row.get("lb_losses"))
        gap_wins = as_int(row.get("gap_wins"))
        gap_losses = as_int(row.get("gap_losses"))
        max_ub = as_int(row.get("max_ub_regression"))
        if as_int(row.get("rows")) <= 0:
            issue_target.append(f"{label}: no paired fair rows")
        if require_lb_positive and total_delta_lb <= 0:
            issue_target.append(f"{label}: total_delta_lb <= 0 ({total_delta_lb})")
        if lb_wins <= lb_losses:
            warnings.append(f"{label}: LB wins <= losses ({lb_wins}/{lb_losses})")
        if total_delta_gap >= 0:
            issue_target.append(f"{label}: total_delta_gap >= 0 ({total_delta_gap})")
        if gap_wins <= gap_losses:
            warnings.append(f"{label}: gap wins <= losses ({gap_wins}/{gap_losses})")
        if max_ub > max_ub_regression:
            issue_target.append(f"{label}: max UB regression {max_ub} > {max_ub_regression}")
        if total_delta_opt < 0:
            issue_target.append(f"{label}: #OPT regression ({total_delta_opt})")

    for row in scoped_by_family:
        label = f"{row.get('candidate', '?')}/{row.get('solver', '?')}/{row.get('family', '?')}"
        if as_int(row.get("max_ub_regression")) > max_ub_regression:
            issue_target.append(f"{label}: max UB regression {row.get('max_ub_regression')} > {max_ub_regression}")
        if as_int(row.get("total_delta_gap")) > 0:
            warnings.append(f"{label}: family gap regression ({row.get('total_delta_gap')})")

    return failures, warnings


def check_candidate(
    path: Path,
    *,
    stress_families: set[str],
    max_ub_regression: int,
    require_lb_positive: bool,
) -> tuple[list[str], list[str], list[str], list[str]]:
    runs = read_csv(path / "layer_a_runs.csv")
    fair = read_csv(path / "layer_a_fair_summary.csv")
    aggregate = read_csv(path / "layer_a_fair_aggregate.csv")
    by_family = read_csv(path / "layer_a_fair_aggregate_by_family.csv")

    missing: list[str] = []
    if not runs:
        missing.append("missing or empty layer_a_runs.csv")
    if not fair:
        missing.append("missing or empty layer_a_fair_summary.csv")
    if not aggregate:
        missing.append("missing or empty layer_a_fair_aggregate.csv")
    if missing:
        return missing, [], [], []

    core_failures, core_warnings = check_scope(
        runs=runs,
        fair=fair,
        by_family=by_family,
        stress_families=stress_families,
        stress=False,
        max_ub_regression=max_ub_regression,
        require_lb_positive=require_lb_positive,
    )
    stress_failures, stress_warnings = check_scope(
        runs=runs,
        fair=fair,
        by_family=by_family,
        stress_families=stress_families,
        stress=True,
        max_ub_regression=max_ub_regression,
        require_lb_positive=require_lb_positive,
    )
    return core_failures, core_warnings, stress_failures, stress_warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("analysis/strict_check_report.md"))
    parser.add_argument("--max-ub-regression", type=int, default=500)
    parser.add_argument("--stress-families", default=DEFAULT_STRESS_FAMILIES)
    parser.add_argument("--allow-nonpositive-lb", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()
    stress_families = set(csv_list(args.stress_families))

    candidate_dirs = find_candidate_dirs(args.result)
    if not candidate_dirs:
        raise SystemExit(f"No Stage-1 candidate result dirs found under {args.result}")

    all_core_failures: list[str] = []
    all_warnings: list[str] = []
    all_stress_observations: list[str] = []
    core_passing_dirs = 0
    lines = [
        "# Stage 1 Strict Check",
        "",
        f"Core gate excludes stress families: {', '.join(sorted(stress_families))}",
        "Stress families are reported as risk observations and do not fail `--strict`.",
        "",
    ]
    for candidate_dir in candidate_dirs:
        core_failures, core_warnings, stress_observations, stress_warnings = check_candidate(
            candidate_dir,
            stress_families=stress_families,
            max_ub_regression=args.max_ub_regression,
            require_lb_positive=not args.allow_nonpositive_lb,
        )
        lines.append(f"## {candidate_dir}")
        lines.append("")
        lines.append("Core Failures:")
        lines.extend([f"- {item}" for item in core_failures] or ["- none"])
        lines.append("")
        lines.append("Core Warnings:")
        lines.extend([f"- {item}" for item in core_warnings] or ["- none"])
        lines.append("")
        lines.append("Stress Observations:")
        lines.extend([f"- {item}" for item in stress_observations] or ["- none"])
        lines.append("")
        lines.append("Stress Warnings:")
        lines.extend([f"- {item}" for item in stress_warnings] or ["- none"])
        lines.append("")
        all_core_failures.extend(f"{candidate_dir}: {item}" for item in core_failures)
        all_warnings.extend(f"{candidate_dir}: {item}" for item in core_warnings + stress_warnings)
        all_stress_observations.extend(f"{candidate_dir}: {item}" for item in stress_observations)
        if not core_failures:
            core_passing_dirs += 1

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- checked_dirs: {len(candidate_dirs)}")
    lines.append(f"- core_passing_dirs: {core_passing_dirs}")
    lines.append(f"- core_failures: {len(all_core_failures)}")
    lines.append(f"- stress_observations: {len(all_stress_observations)}")
    lines.append(f"- warnings: {len(all_warnings)}")
    report = "\n".join(lines) + "\n"
    print(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    if args.strict and core_passing_dirs == 0:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
