#!/usr/bin/env python3
"""Audit exp10 Stage-1 controller failures by family and failure mode."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


CORE_FIELDS = [
    "candidate",
    "solver",
    "family",
    "rows",
    "improved",
    "no_observed_effect",
    "lb_regression",
    "ub_regression",
    "opt_regression",
    "lb_gain_not_converted",
    "gap_regression_without_lb_gain",
    "early_stop_runs",
    "timeout_or_parse_runs",
    "no_lb_gain_runs",
    "controller_guards",
    "controller_actions",
]


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, Any]], fields: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows([{field: row.get(field, "") for field in fields} for row in rows])


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
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_runs.csv").exists())


def classify_pair(row: dict[str, str], *, max_ub_regression: int) -> str:
    delta_lb = as_int(row.get("delta_lb_controller_minus_dbs"))
    delta_ub = as_int(row.get("delta_ub_controller_minus_dbs"))
    delta_gap = as_int(row.get("delta_gap_controller_minus_dbs"))
    delta_opt = as_int(row.get("delta_opt_controller_minus_dbs"))

    if delta_opt < 0:
        return "opt_regression"
    if delta_ub > max_ub_regression:
        return "ub_regression"
    if delta_lb < 0:
        return "lb_regression"
    if delta_lb > 0 and delta_gap < 0:
        return "improved"
    if delta_lb > 0:
        return "lb_gain_not_converted"
    if delta_gap > 0:
        return "gap_regression_without_lb_gain"
    return "no_observed_effect"


def summarize_candidate(path: Path, *, min_rounds: int, max_ub_regression: int) -> tuple[list[dict[str, Any]], list[str]]:
    runs = read_csv(path / "layer_a_runs.csv")
    fair = read_csv(path / "layer_a_fair_summary.csv")
    warnings: list[str] = []
    if not runs:
        return [], [f"{path}: missing layer_a_runs.csv"]
    if not fair:
        return [], [f"{path}: missing layer_a_fair_summary.csv"]

    run_groups: dict[tuple[str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in runs:
        run_groups[(row.get("candidate", ""), row.get("solver", ""), row.get("family", ""))].append(row)

    pair_counts: dict[tuple[str, str, str], Counter[str]] = defaultdict(Counter)
    for row in fair:
        key = (row.get("candidate", ""), row.get("solver", ""), row.get("family", ""))
        pair_counts[key][classify_pair(row, max_ub_regression=max_ub_regression)] += 1

    rows: list[dict[str, Any]] = []
    for key in sorted(set(run_groups) | set(pair_counts)):
        candidate, solver, family = key
        grouped_runs = run_groups.get(key, [])
        early_stop = [
            row for row in grouped_runs
            if as_bool(row.get("parse_ok")) and as_int(row.get("exit_code")) == 0 and as_int(row.get("n_rounds")) < min_rounds
        ]
        timeout_or_parse = [
            row for row in grouped_runs
            if not as_bool(row.get("parse_ok")) or as_int(row.get("exit_code")) != 0
        ]
        no_lb_gain = [row for row in grouped_runs if as_bool(row.get("parse_ok")) and as_int(row.get("lb_gain")) == 0]
        guard_counts = Counter(row.get("aq_guard_reason", "") for row in grouped_runs if row.get("aq_guard_reason"))
        action_counts = Counter(row.get("aq_action", "") for row in grouped_runs if row.get("aq_action"))
        counts = pair_counts.get(key, Counter())
        out = {
            "candidate": candidate,
            "solver": solver,
            "family": family,
            "rows": sum(counts.values()),
            "early_stop_runs": len(early_stop),
            "timeout_or_parse_runs": len(timeout_or_parse),
            "no_lb_gain_runs": len(no_lb_gain),
            "controller_guards": ";".join(f"{name}:{count}" for name, count in sorted(guard_counts.items())),
            "controller_actions": ";".join(f"{name}:{count}" for name, count in sorted(action_counts.items())),
        }
        for field in CORE_FIELDS[4:11]:
            out[field] = counts.get(field, 0)
        rows.append(out)

    if not any(row.get("rows") for row in rows):
        warnings.append(f"{path}: no paired fair rows; audit is run-level only")
    return rows, warnings


def render_report(rows: list[dict[str, Any]], warnings: list[str], *, result: Path) -> str:
    lines = [
        "# Stage 1 Failure Audit",
        "",
        f"- result: `{result}`",
        f"- groups: {len(rows)}",
        "",
        "## Findings By Family",
        "",
    ]
    if not rows:
        lines.append("- no rows")
    for row in rows:
        label = f"{row['candidate']}/{row['solver']}/{row['family']}"
        lines.append(
            "- {label}: pairs={rows}, improved={improved}, no_effect={no_effect}, "
            "lb_reg={lb_reg}, ub_reg={ub_reg}, opt_reg={opt_reg}, early_stop_runs={early}, "
            "timeout_or_parse_runs={timeout}, no_lb_gain_runs={no_gain}".format(
                label=label,
                rows=row.get("rows", 0),
                improved=row.get("improved", 0),
                no_effect=row.get("no_observed_effect", 0),
                lb_reg=row.get("lb_regression", 0),
                ub_reg=row.get("ub_regression", 0),
                opt_reg=row.get("opt_regression", 0),
                early=row.get("early_stop_runs", 0),
                timeout=row.get("timeout_or_parse_runs", 0),
                no_gain=row.get("no_lb_gain_runs", 0),
            )
        )
        if row.get("controller_guards") or row.get("controller_actions"):
            lines.append(
                f"  guards=`{row.get('controller_guards', '') or 'none'}`, "
                f"actions=`{row.get('controller_actions', '') or 'none'}`"
            )
    lines.extend(["", "## Warnings", ""])
    lines.extend([f"- {item}" for item in warnings] or ["- none"])
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("stage1_failure_audit.md"))
    parser.add_argument("--min-rounds", type=int, default=3)
    parser.add_argument("--max-ub-regression", type=int, default=500)
    args = parser.parse_args()

    all_rows: list[dict[str, Any]] = []
    warnings: list[str] = []
    for candidate_dir in find_candidate_dirs(args.result):
        rows, candidate_warnings = summarize_candidate(
            candidate_dir,
            min_rounds=args.min_rounds,
            max_ub_regression=args.max_ub_regression,
        )
        all_rows.extend(rows)
        warnings.extend(candidate_warnings)

    report = render_report(all_rows, warnings, result=args.result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    write_csv(args.output.with_suffix(".csv"), all_rows, CORE_FIELDS)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
