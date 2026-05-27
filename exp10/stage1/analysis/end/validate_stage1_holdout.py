#!/usr/bin/env python3
"""Validate Stage-1 candidates on holdout family and seed folds."""

from __future__ import annotations

import argparse
import csv
from collections import defaultdict
from pathlib import Path
from typing import Any


FIELDS = [
    "fold_type",
    "fold",
    "candidate",
    "solver",
    "rows",
    "lb_wins",
    "lb_losses",
    "total_delta_lb",
    "gap_wins",
    "gap_losses",
    "total_delta_gap",
    "max_ub_regression",
    "total_delta_opt",
    "passes_gate",
    "baseline_candidate",
    "delta_lb_vs_baseline_candidate",
    "delta_gap_vs_baseline_candidate",
    "delta_opt_vs_baseline_candidate",
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


def csv_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def find_candidate_dirs(root: Path) -> list[Path]:
    if (root / "layer_a_fair_summary.csv").exists():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_fair_summary.csv").exists())


def load_fair_rows(root: Path) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for candidate_dir in find_candidate_dirs(root):
        rows.extend(read_csv(candidate_dir / "layer_a_fair_summary.csv"))
    return rows


def aggregate(rows: list[dict[str, str]], *, fold_type: str, fold: str, max_ub_regression: int) -> list[dict[str, Any]]:
    groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        groups[(row.get("candidate", ""), row.get("solver", ""))].append(row)

    out: list[dict[str, Any]] = []
    for (candidate, solver), subset in sorted(groups.items()):
        lb = [as_int(row.get("delta_lb_controller_minus_dbs")) for row in subset]
        gap = [as_int(row.get("delta_gap_controller_minus_dbs")) for row in subset]
        ub = [as_int(row.get("delta_ub_controller_minus_dbs")) for row in subset]
        opt = [as_int(row.get("delta_opt_controller_minus_dbs")) for row in subset]
        total_delta_lb = sum(lb)
        total_delta_gap = sum(gap)
        total_delta_opt = sum(opt)
        max_ub = max(ub) if ub else 0
        passes_gate = (
            len(subset) > 0
            and total_delta_lb > 0
            and sum(delta > 0 for delta in lb) > sum(delta < 0 for delta in lb)
            and total_delta_gap < 0
            and max_ub <= max_ub_regression
            and total_delta_opt >= 0
        )
        out.append(
            {
                "fold_type": fold_type,
                "fold": fold,
                "candidate": candidate,
                "solver": solver,
                "rows": len(subset),
                "lb_wins": sum(delta > 0 for delta in lb),
                "lb_losses": sum(delta < 0 for delta in lb),
                "total_delta_lb": total_delta_lb,
                "gap_wins": sum(delta < 0 for delta in gap),
                "gap_losses": sum(delta > 0 for delta in gap),
                "total_delta_gap": total_delta_gap,
                "max_ub_regression": max_ub,
                "total_delta_opt": total_delta_opt,
                "passes_gate": int(passes_gate),
            }
        )
    return out


def add_baseline_deltas(rows: list[dict[str, Any]], baseline_candidate: str) -> None:
    baseline: dict[tuple[str, str, str], dict[str, Any]] = {}
    for row in rows:
        if row.get("candidate") == baseline_candidate:
            baseline[(str(row["fold_type"]), str(row["fold"]), str(row["solver"]))] = row

    for row in rows:
        key = (str(row["fold_type"]), str(row["fold"]), str(row["solver"]))
        base = baseline.get(key)
        row["baseline_candidate"] = baseline_candidate
        if base is None or row.get("candidate") == baseline_candidate:
            row["delta_lb_vs_baseline_candidate"] = ""
            row["delta_gap_vs_baseline_candidate"] = ""
            row["delta_opt_vs_baseline_candidate"] = ""
            continue
        row["delta_lb_vs_baseline_candidate"] = as_int(row["total_delta_lb"]) - as_int(base["total_delta_lb"])
        row["delta_gap_vs_baseline_candidate"] = as_int(row["total_delta_gap"]) - as_int(base["total_delta_gap"])
        row["delta_opt_vs_baseline_candidate"] = as_int(row["total_delta_opt"]) - as_int(base["total_delta_opt"])


def render_report(rows: list[dict[str, Any]], *, result: Path, baseline_candidate: str) -> str:
    lines = [
        "# Stage 1 Holdout Validation",
        "",
        f"- result: `{result}`",
        f"- baseline_candidate: `{baseline_candidate}`",
        f"- folds: {len({(row['fold_type'], row['fold']) for row in rows})}",
        "",
        "## Fold Summary",
        "",
    ]
    for row in rows:
        lines.append(
            "- {fold_type}={fold} {candidate}/{solver}: rows={rows}, pass={passes}, "
            "total_delta_lb={lb}, total_delta_gap={gap}, total_delta_opt={opt}, max_ub={ub}".format(
                fold_type=row["fold_type"],
                fold=row["fold"],
                candidate=row["candidate"],
                solver=row["solver"],
                rows=row["rows"],
                passes=row["passes_gate"],
                lb=row["total_delta_lb"],
                gap=row["total_delta_gap"],
                opt=row["total_delta_opt"],
                ub=row["max_ub_regression"],
            )
        )
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("stage1_holdout_validation.md"))
    parser.add_argument("--baseline-candidate", default="v006")
    parser.add_argument("--max-ub-regression", type=int, default=500)
    parser.add_argument("--folds", default="family,seed")
    args = parser.parse_args()

    fair_rows = load_fair_rows(args.result)
    output_rows: list[dict[str, Any]] = []
    requested_folds = set(csv_list(args.folds))
    if "family" in requested_folds:
        for family in sorted({row.get("family", "") for row in fair_rows if row.get("family")}):
            output_rows.extend(
                aggregate(
                    [row for row in fair_rows if row.get("family") == family],
                    fold_type="family",
                    fold=family,
                    max_ub_regression=args.max_ub_regression,
                )
            )
    if "seed" in requested_folds:
        for seed in sorted({row.get("seed", "") for row in fair_rows if row.get("seed")}):
            output_rows.extend(
                aggregate(
                    [row for row in fair_rows if row.get("seed") == seed],
                    fold_type="seed",
                    fold=seed,
                    max_ub_regression=args.max_ub_regression,
                )
            )

    add_baseline_deltas(output_rows, args.baseline_candidate)
    report = render_report(output_rows, result=args.result, baseline_candidate=args.baseline_candidate)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    write_csv(args.output.with_suffix(".csv"), output_rows, FIELDS)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
