#!/usr/bin/env python3
"""Analyze randomized Stage-1 arm logging results."""

from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean
from typing import Any


SUMMARY_FIELDS = [
    "candidate",
    "solver",
    "family",
    "arm",
    "rows",
    "valid_rows",
    "parse_failures",
    "nonzero_exits",
    "avg_best_lb",
    "avg_lb_gain",
    "avg_gap",
    "avg_ub_gain",
    "avg_rounds",
    "opt_count",
    "slope_accepts",
    "slope_rejects",
    "guard_reasons",
]

BASELINE_FIELDS = [
    "candidate",
    "solver",
    "family",
    "arm",
    "rows",
    "baseline_rows",
    "delta_avg_best_lb_vs_dbs_only",
    "delta_avg_lb_gain_vs_dbs_only",
    "delta_avg_gap_vs_dbs_only",
    "delta_avg_ub_gain_vs_dbs_only",
    "delta_opt_rate_vs_dbs_only",
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


def as_float(value: Any, default: float = 0.0) -> float:
    try:
        return float(str(value))
    except (TypeError, ValueError):
        return default


def as_bool(value: Any) -> bool:
    return str(value).strip().lower() in {"1", "true", "yes"}


def find_candidate_dirs(root: Path) -> list[Path]:
    if (root / "layer_a_runs.csv").exists():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_runs.csv").exists())


def metric_mean(rows: list[dict[str, str]], field: str) -> float:
    values = [as_float(row.get(field)) for row in rows]
    return mean(values) if values else 0.0


def summarize(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str, str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        arm = row.get("arm", "")
        if not arm:
            continue
        key = (row.get("candidate", ""), row.get("solver", ""), row.get("family", ""), arm)
        groups[key].append(row)

    out: list[dict[str, Any]] = []
    for (candidate, solver, family, arm), group in sorted(groups.items()):
        valid = [row for row in group if as_bool(row.get("parse_ok")) and as_int(row.get("exit_code")) == 0]
        slope = Counter(row.get("aq_slope_decision", "") for row in group if row.get("aq_slope_decision"))
        guards = Counter(row.get("aq_guard_reason", "") for row in group if row.get("aq_guard_reason"))
        out.append(
            {
                "candidate": candidate,
                "solver": solver,
                "family": family,
                "arm": arm,
                "rows": len(group),
                "valid_rows": len(valid),
                "parse_failures": sum(not as_bool(row.get("parse_ok")) for row in group),
                "nonzero_exits": sum(as_int(row.get("exit_code")) != 0 for row in group),
                "avg_best_lb": metric_mean(valid, "best_lb"),
                "avg_lb_gain": metric_mean(valid, "lb_gain"),
                "avg_gap": metric_mean(valid, "absolute_gap"),
                "avg_ub_gain": metric_mean(valid, "ub_gain"),
                "avg_rounds": metric_mean(valid, "n_rounds"),
                "opt_count": sum(as_int(row.get("solver_certified_opt")) for row in valid),
                "slope_accepts": slope.get("accept", 0),
                "slope_rejects": slope.get("reject", 0),
                "guard_reasons": ";".join(f"{name}:{count}" for name, count in sorted(guards.items())),
            }
        )
    return out


def compare_to_dbs(summary: list[dict[str, Any]]) -> list[dict[str, Any]]:
    baseline: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in summary:
        if row.get("arm") == "dbs_only":
            baseline[(str(row["candidate"]), str(row["solver"]), str(row["family"]))] = row

    out: list[dict[str, Any]] = []
    for row in summary:
        if row.get("arm") == "dbs_only":
            continue
        base = baseline.get((str(row["candidate"]), str(row["solver"]), str(row["family"])))
        if base is None:
            continue
        row_valid = as_int(row.get("valid_rows"))
        base_valid = as_int(base.get("valid_rows"))
        opt_rate = (as_int(row.get("opt_count")) / row_valid) if row_valid else 0.0
        base_opt_rate = (as_int(base.get("opt_count")) / base_valid) if base_valid else 0.0
        out.append(
            {
                "candidate": row["candidate"],
                "solver": row["solver"],
                "family": row["family"],
                "arm": row["arm"],
                "rows": row["valid_rows"],
                "baseline_rows": base["valid_rows"],
                "delta_avg_best_lb_vs_dbs_only": as_float(row["avg_best_lb"]) - as_float(base["avg_best_lb"]),
                "delta_avg_lb_gain_vs_dbs_only": as_float(row["avg_lb_gain"]) - as_float(base["avg_lb_gain"]),
                "delta_avg_gap_vs_dbs_only": as_float(row["avg_gap"]) - as_float(base["avg_gap"]),
                "delta_avg_ub_gain_vs_dbs_only": as_float(row["avg_ub_gain"]) - as_float(base["avg_ub_gain"]),
                "delta_opt_rate_vs_dbs_only": opt_rate - base_opt_rate,
            }
        )
    return out


def render_report(summary: list[dict[str, Any]], comparison: list[dict[str, Any]], *, result: Path) -> str:
    lines = [
        "# Stage 1 Randomized Arm Analysis",
        "",
        f"- result: `{result}`",
        f"- arm_groups: {len(summary)}",
        f"- comparison_groups: {len(comparison)}",
        "",
        "## Arm Summary",
        "",
    ]
    for row in summary:
        lines.append(
            "- {candidate}/{solver}/{family}/{arm}: valid={valid}/{rows}, "
            "avg_lb_gain={lb_gain:.3f}, avg_gap={gap:.3f}, opt={opt}, guards=`{guards}`".format(
                candidate=row["candidate"],
                solver=row["solver"],
                family=row["family"],
                arm=row["arm"],
                valid=as_int(row["valid_rows"]),
                rows=as_int(row["rows"]),
                lb_gain=as_float(row["avg_lb_gain"]),
                gap=as_float(row["avg_gap"]),
                opt=as_int(row["opt_count"]),
                guards=row.get("guard_reasons", "") or "none",
            )
        )

    lines.extend(["", "## Against DBS-only", ""])
    if not comparison:
        lines.append("- no DBS-only baseline rows available for comparison")
    for row in comparison:
        lines.append(
            "- {candidate}/{solver}/{family}/{arm}: dLB={dlb:.3f}, dLBGain={dlg:.3f}, "
            "dGap={dgap:.3f}, dUBGain={dub:.3f}, dOptRate={dopt:.3f}".format(
                candidate=row["candidate"],
                solver=row["solver"],
                family=row["family"],
                arm=row["arm"],
                dlb=as_float(row["delta_avg_best_lb_vs_dbs_only"]),
                dlg=as_float(row["delta_avg_lb_gain_vs_dbs_only"]),
                dgap=as_float(row["delta_avg_gap_vs_dbs_only"]),
                dub=as_float(row["delta_avg_ub_gain_vs_dbs_only"]),
                dopt=as_float(row["delta_opt_rate_vs_dbs_only"]),
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("stage1_randomized_arm_analysis.md"))
    args = parser.parse_args()

    rows: list[dict[str, str]] = []
    for candidate_dir in find_candidate_dirs(args.result):
        rows.extend(read_csv(candidate_dir / "layer_a_runs.csv"))

    summary = summarize(rows)
    comparison = compare_to_dbs(summary)
    report = render_report(summary, comparison, result=args.result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    write_csv(args.output.with_name(args.output.stem + "_summary.csv"), summary, SUMMARY_FIELDS)
    write_csv(args.output.with_name(args.output.stem + "_vs_dbs.csv"), comparison, BASELINE_FIELDS)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
