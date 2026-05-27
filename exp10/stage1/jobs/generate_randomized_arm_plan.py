#!/usr/bin/env python3
"""Generate a randomized Stage-1 arm logging plan.

The output is a CSV protocol for collecting counterfactual-friendly observations.
It does not run solvers; feed the CSV to a runner or use it as the submission
manifest for a randomized pilot.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import random
from pathlib import Path
from typing import Any


DEFAULT_SELECTED = Path(__file__).resolve().parents[2] / "selected_instances"
DEFAULT_ARMS = "dbs_only,light_probe,standard_probe,heavy_probe,rollback_probe"
DEFAULT_SOLVERS = "deep-v6,fast-v19"


ARM_ENV: dict[str, dict[str, str]] = {
    "dbs_only": {"MWDS_AQ_MODE": "dbs"},
    "light_probe": {
        "MWDS_AQ_MODE": "guarded",
        "MWDS_AQ_MIN_FIRST_GAP": "0.0",
        "MWDS_AQ_SMALL_PROBE_FRAC": "0.05",
        "MWDS_AQ_NORMAL_PROBE_FRAC": "0.05",
        "MWDS_AQ_PROBE_FRAC": "0.05",
    },
    "standard_probe": {
        "MWDS_AQ_MODE": "guarded",
        "MWDS_AQ_MIN_FIRST_GAP": "0.0",
        "MWDS_AQ_NORMAL_PROBE_FRAC": "0.15",
        "MWDS_AQ_PROBE_FRAC": "0.15",
    },
    "heavy_probe": {
        "MWDS_AQ_MODE": "guarded",
        "MWDS_AQ_MIN_FIRST_GAP": "0.0",
        "MWDS_AQ_HEAVY_PROBE_FRAC": "0.25",
        "MWDS_AQ_HEAVY_ANTS": "7",
        "MWDS_DEEP_AQ_T1LIKE_PROBE_FRAC": "0.25",
    },
    "rollback_probe": {
        "MWDS_AQ_MODE": "guarded",
        "MWDS_AQ_MIN_FIRST_GAP": "0.0",
        "MWDS_AQ_SLOPE_MARGIN": "999.0",
    },
}


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


def stable_seed(*parts: Any, base_seed: int) -> int:
    digest = hashlib.sha256("|".join(str(part) for part in parts).encode()).hexdigest()
    return base_seed + int(digest[:12], 16)


def load_instances(selected_root: Path, datasets: list[str]) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    for family in datasets:
        path = selected_root / f"{family}.txt"
        if not path.exists():
            raise SystemExit(f"Missing selected instance file: {path}")
        for rank, raw in enumerate(path.read_text().splitlines(), start=1):
            instance = raw.strip()
            if instance:
                rows.append({"family": family, "rank": str(rank), "instance": instance})
    return rows


def choose_arm(arms: list[str], *, base_seed: int, keys: tuple[Any, ...]) -> str:
    rng = random.Random(stable_seed(*keys, base_seed=base_seed))
    return rng.choice(arms)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--selected-root", type=Path, default=DEFAULT_SELECTED)
    parser.add_argument("--datasets", default="T1,T2,UDG,BHOSLIB,DIMACS,NDR")
    parser.add_argument("--solvers", default=DEFAULT_SOLVERS)
    parser.add_argument("--seeds", default="1,2,3")
    parser.add_argument("--reps", type=int, default=2)
    parser.add_argument("--arms", default=DEFAULT_ARMS)
    parser.add_argument("--policy-seed", type=int, default=20260527)
    parser.add_argument("--output", type=Path, default=Path("../sumup/randomized_arm_plan.csv"))
    args = parser.parse_args()

    arms = csv_list(args.arms)
    unknown = sorted(set(arms) - set(ARM_ENV))
    if unknown:
        raise SystemExit(f"Unknown arms {unknown}; known={sorted(ARM_ENV)}")

    rows: list[dict[str, Any]] = []
    for inst in load_instances(args.selected_root, csv_list(args.datasets)):
        for solver in csv_list(args.solvers):
            for logical_seed in parse_ints(args.seeds):
                for rep in range(1, args.reps + 1):
                    arm = choose_arm(
                        arms,
                        base_seed=args.policy_seed,
                        keys=(inst["family"], inst["instance"], solver, logical_seed, rep),
                    )
                    env = ARM_ENV[arm]
                    rows.append(
                        {
                            **inst,
                            "solver": solver,
                            "logical_seed": logical_seed,
                            "rep": rep,
                            "arm": arm,
                            "mode_family": env["MWDS_AQ_MODE"],
                            "env_overrides_json": json.dumps(env, sort_keys=True),
                            "policy_seed": args.policy_seed,
                        }
                    )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "family",
        "rank",
        "instance",
        "solver",
        "logical_seed",
        "rep",
        "arm",
        "mode_family",
        "env_overrides_json",
        "policy_seed",
    ]
    with args.output.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)

    counts: dict[str, int] = {arm: 0 for arm in arms}
    for row in rows:
        counts[str(row["arm"])] += 1
    print(json.dumps({"output": str(args.output), "rows": len(rows), "arm_counts": counts}, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
