#!/usr/bin/env python3
"""Strict gates for exp10 Stage-1 result directories."""

from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


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


def find_candidate_dirs(root: Path) -> list[Path]:
    if (root / "layer_a_runs.csv").exists():
        return [root]
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_runs.csv").exists())


def check_candidate(path: Path, *, max_ub_regression: int, require_lb_positive: bool) -> tuple[list[str], list[str]]:
    failures: list[str] = []
    warnings: list[str] = []
    runs = read_csv(path / "layer_a_runs.csv")
    fair = read_csv(path / "layer_a_fair_summary.csv")
    aggregate = read_csv(path / "layer_a_fair_aggregate.csv")
    by_family = read_csv(path / "layer_a_fair_aggregate_by_family.csv")

    if not runs:
        failures.append("missing or empty layer_a_runs.csv")
    if not fair:
        failures.append("missing or empty layer_a_fair_summary.csv")
    if not aggregate:
        failures.append("missing or empty layer_a_fair_aggregate.csv")
    if failures:
        return failures, warnings

    parse_failures = [row for row in runs if not as_bool(row.get("parse_ok"))]
    nonzero_exit = [row for row in runs if as_int(row.get("exit_code")) != 0]
    if parse_failures:
        failures.append(f"parse failures: {len(parse_failures)}")
    if nonzero_exit:
        failures.append(f"non-zero exits: {len(nonzero_exit)}")

    grouped: dict[tuple[str, str, str, str, str], dict[str, int]] = {}
    for row in runs:
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
        failures.append(f"unequal dbs/controller run counts: {len(unfair)} groups")

    for row in aggregate:
        candidate = row.get("candidate", "?")
        solver = row.get("solver", "?")
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
            failures.append(f"{label}: no paired fair rows")
        if require_lb_positive and total_delta_lb <= 0:
            failures.append(f"{label}: total_delta_lb <= 0 ({total_delta_lb})")
        if lb_wins <= lb_losses:
            warnings.append(f"{label}: LB wins <= losses ({lb_wins}/{lb_losses})")
        if total_delta_gap >= 0:
            failures.append(f"{label}: total_delta_gap >= 0 ({total_delta_gap})")
        if gap_wins <= gap_losses:
            warnings.append(f"{label}: gap wins <= losses ({gap_wins}/{gap_losses})")
        if max_ub > max_ub_regression:
            failures.append(f"{label}: max UB regression {max_ub} > {max_ub_regression}")
        if total_delta_opt < 0:
            failures.append(f"{label}: #OPT regression ({total_delta_opt})")

    for row in by_family:
        label = f"{row.get('candidate', '?')}/{row.get('solver', '?')}/{row.get('family', '?')}"
        if as_int(row.get("max_ub_regression")) > max_ub_regression:
            failures.append(f"{label}: max UB regression {row.get('max_ub_regression')} > {max_ub_regression}")
        if as_int(row.get("total_delta_gap")) > 0:
            warnings.append(f"{label}: family gap regression ({row.get('total_delta_gap')})")

    return failures, warnings


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("analysis/strict_check_report.md"))
    parser.add_argument("--max-ub-regression", type=int, default=500)
    parser.add_argument("--allow-nonpositive-lb", action="store_true")
    parser.add_argument("--strict", action="store_true")
    args = parser.parse_args()

    candidate_dirs = find_candidate_dirs(args.result)
    if not candidate_dirs:
        raise SystemExit(f"No Stage-1 candidate result dirs found under {args.result}")

    all_failures: list[str] = []
    all_warnings: list[str] = []
    lines = ["# Stage 1 Strict Check", ""]
    for candidate_dir in candidate_dirs:
        failures, warnings = check_candidate(
            candidate_dir,
            max_ub_regression=args.max_ub_regression,
            require_lb_positive=not args.allow_nonpositive_lb,
        )
        lines.append(f"## {candidate_dir}")
        lines.append("")
        lines.append("Failures:")
        lines.extend([f"- {item}" for item in failures] or ["- none"])
        lines.append("")
        lines.append("Warnings:")
        lines.extend([f"- {item}" for item in warnings] or ["- none"])
        lines.append("")
        all_failures.extend(f"{candidate_dir}: {item}" for item in failures)
        all_warnings.extend(f"{candidate_dir}: {item}" for item in warnings)

    lines.append("## Summary")
    lines.append("")
    lines.append(f"- checked_dirs: {len(candidate_dirs)}")
    lines.append(f"- failures: {len(all_failures)}")
    lines.append(f"- warnings: {len(all_warnings)}")
    report = "\n".join(lines) + "\n"
    print(report)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    if args.strict and all_failures:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
