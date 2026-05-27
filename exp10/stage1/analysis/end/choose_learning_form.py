#!/usr/bin/env python3
"""Decide whether Stage-1 evidence supports per-run selection or bandit naming."""

from __future__ import annotations

import argparse
import csv
import re
from collections import Counter
from pathlib import Path
from typing import Any


ARM_RE = re.compile(r"\[AQ bandit arm\]")
SLOPE_RE = re.compile(r"\[AQ slope (?:accept|reject)\]")
REWARD_UPDATE_RE = re.compile(r"\b(UCB|EXP3|Thompson|reward|credit|update)\b", re.IGNORECASE)


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def csv_list(text: str) -> list[str]:
    return [item.strip() for item in text.split(",") if item.strip()]


def find_candidate_dirs(root: Path) -> list[Path]:
    if (root / "layer_a_runs.csv").exists():
        return [root]
    if not root.exists():
        return []
    return sorted(path for path in root.iterdir() if path.is_dir() and (path / "layer_a_runs.csv").exists())


def as_int(value: Any, default: int = 0) -> int:
    try:
        return int(float(str(value)))
    except (TypeError, ValueError):
        return default


def inspect_raw_outputs(rows: list[dict[str, str]]) -> dict[str, int]:
    counts = {
        "raw_files": 0,
        "runs_with_multiple_arm_decisions": 0,
        "runs_with_slope_reward": 0,
        "runs_with_reward_update_terms": 0,
    }
    for row in rows:
        raw = row.get("raw_output", "")
        if not raw:
            continue
        path = Path(raw)
        if not path.exists():
            continue
        text = path.read_text(errors="replace")
        counts["raw_files"] += 1
        if len(ARM_RE.findall(text)) > 1:
            counts["runs_with_multiple_arm_decisions"] += 1
        if SLOPE_RE.search(text):
            counts["runs_with_slope_reward"] += 1
        if REWARD_UPDATE_RE.search(text):
            counts["runs_with_reward_update_terms"] += 1
    return counts


def decide(rows: list[dict[str, str]], *, inspect_raw: bool) -> tuple[dict[str, Any], list[str]]:
    mode_counts = Counter(row.get("mode", "") for row in rows)
    arm_counts = Counter(row.get("arm", "") for row in rows if row.get("arm"))
    aq_arm_counts = Counter(row.get("aq_arm", "") for row in rows if row.get("aq_arm"))
    slope_decisions = Counter(row.get("aq_slope_decision", "") for row in rows if row.get("aq_slope_decision"))
    guard_reasons = Counter(row.get("aq_guard_reason", "") for row in rows if row.get("aq_guard_reason"))
    raw_counts = inspect_raw_outputs(rows) if inspect_raw else {
        "raw_files": 0,
        "runs_with_multiple_arm_decisions": 0,
        "runs_with_slope_reward": 0,
        "runs_with_reward_update_terms": 0,
    }

    planned_arms = sum(arm_counts.values())
    observed_solver_arms = sum(aq_arm_counts.values())
    multiple_decisions = raw_counts["runs_with_multiple_arm_decisions"]
    reward_updates = raw_counts["runs_with_reward_update_terms"]

    if multiple_decisions > 0 and reward_updates > 0:
        recommendation = "contextual_bandit_candidate"
        naming = "contextual bandit is defensible if updates are action-conditioned and evaluated against non-contextual baselines"
    elif planned_arms > 0 or observed_solver_arms > 0:
        recommendation = "per_run_selection"
        naming = "use selection hyper-heuristic or SATzilla-style per-run selection; do not call this contextual bandit"
    else:
        recommendation = "hand_written_gating_audit"
        naming = "current logs only support hand-written gating / controller audit terminology"

    summary = {
        "runs": len(rows),
        "modes": dict(sorted(mode_counts.items())),
        "planned_arm_rows": planned_arms,
        "observed_solver_arm_rows": observed_solver_arms,
        "slope_decisions": dict(sorted(slope_decisions.items())),
        "guard_reasons": dict(sorted(guard_reasons.items())),
        **raw_counts,
        "recommendation": recommendation,
    }
    requirements = [
        naming,
        "If per-run selection: train/evaluate DBS-only, random arm, v006, non-contextual mean/UCB, and ridge/linear selector on held-out family or seed folds.",
        "If contextual bandit: add multiple arm decisions per run plus explicit action reward updates before using bandit/RL terminology.",
        "In both cases: primary gate is negative-transfer control, not LB-only improvement.",
    ]
    return summary, requirements


def render_report(summary: dict[str, Any], requirements: list[str], *, result: Path) -> str:
    lines = [
        "# Stage 1 Learning Form Decision",
        "",
        f"- result: `{result}`",
        f"- runs: {summary['runs']}",
        f"- recommendation: `{summary['recommendation']}`",
        f"- planned_arm_rows: {summary['planned_arm_rows']}",
        f"- observed_solver_arm_rows: {summary['observed_solver_arm_rows']}",
        f"- raw_files_inspected: {summary['raw_files']}",
        f"- runs_with_multiple_arm_decisions: {summary['runs_with_multiple_arm_decisions']}",
        f"- runs_with_reward_update_terms: {summary['runs_with_reward_update_terms']}",
        "",
        "## Counts",
        "",
        f"- modes: `{summary['modes']}`",
        f"- slope_decisions: `{summary['slope_decisions']}`",
        f"- guard_reasons: `{summary['guard_reasons']}`",
        "",
        "## Naming And Experiment Requirements",
        "",
    ]
    lines.extend(f"- {item}" for item in requirements)
    return "\n".join(lines) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--result", type=Path, default=Path("../../sumup/result"))
    parser.add_argument("--output", type=Path, default=Path("stage1_learning_form_decision.md"))
    parser.add_argument("--candidates", default="")
    parser.add_argument("--inspect-raw", action="store_true")
    args = parser.parse_args()

    allowed_candidates = set(csv_list(args.candidates))
    rows: list[dict[str, str]] = []
    for candidate_dir in find_candidate_dirs(args.result):
        candidate_rows = read_csv(candidate_dir / "layer_a_runs.csv")
        if allowed_candidates:
            candidate_rows = [row for row in candidate_rows if row.get("candidate", "") in allowed_candidates]
        rows.extend(candidate_rows)

    summary, requirements = decide(rows, inspect_raw=args.inspect_raw)
    report = render_report(summary, requirements, result=args.result)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    print(report)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
