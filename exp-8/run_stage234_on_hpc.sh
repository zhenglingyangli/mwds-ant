#!/bin/bash
# Run the exp-8 post-search certification pipeline on HPC.
#
# Usage:
#   cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
#   bash exp-8/run_stage234_on_hpc.sh
#
# Optional environment knobs:
#   STAGE234_PYTHON=/path/to/python-with-scipy
#   STAGE234_LP_TIME_LIMIT=30
#   STAGE234_MILP_TIME_LIMIT=120
#   STAGE234_LP_MAX_N=1200
#   STAGE234_LP_MAX_INCIDENCE=50000
#   STAGE234_MILP_MAX_N=1200
#   STAGE234_MILP_MAX_INCIDENCE=50000
#   STAGE234_MILP_MAX_GAP=20
#   EXP8_DUMP_ROOT=/path/to/raw/outputs/with/BestSolution

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUT_DIR="$SCRIPT_DIR/stage234"

LP_TIME_LIMIT="${STAGE234_LP_TIME_LIMIT:-30}"
MILP_TIME_LIMIT="${STAGE234_MILP_TIME_LIMIT:-120}"
LP_MAX_N="${STAGE234_LP_MAX_N:-1200}"
LP_MAX_INCIDENCE="${STAGE234_LP_MAX_INCIDENCE:-50000}"
MILP_MAX_N="${STAGE234_MILP_MAX_N:-1200}"
MILP_MAX_INCIDENCE="${STAGE234_MILP_MAX_INCIDENCE:-50000}"
MILP_MAX_GAP="${STAGE234_MILP_MAX_GAP:-20}"
DUMP_ROOT="${EXP8_DUMP_ROOT:-$SCRIPT_DIR}"
PYTHON_BIN="${STAGE234_PYTHON:-python3}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "ERROR: required command not found: $1" >&2
    exit 2
  fi
}

require_cmd "$PYTHON_BIN"

echo "=== exp-8 Stage234 HPC pipeline ==="
echo "repo     : $REPO_ROOT"
echo "exp      : $SCRIPT_DIR"
echo "out      : $OUT_DIR"
echo "dump root: $DUMP_ROOT"
echo "python   : $PYTHON_BIN"

echo
echo "=== 0) Python dependency check ==="
if ! "$PYTHON_BIN" - <<'PY'
import sys
try:
    import numpy  # noqa: F401
    import scipy  # noqa: F401
except ModuleNotFoundError as exc:
    print(f"missing Python dependency: {exc}", file=sys.stderr)
    raise SystemExit(42)
print("python deps OK: scipy/numpy importable")
PY
then
  cat >&2 <<'EOF'

ERROR: exp-8 Stage234 requires numpy and scipy because Stage2/4 use HiGHS
through scipy.optimize.linprog/milp.

Use an HPC Python environment with scipy, then rerun one of these forms:

  module avail scipy python anaconda miniconda
  module load <python-or-conda-module-with-scipy>
  bash exp-8/run_stage234_on_hpc.sh

or:

  conda activate <env-with-scipy>
  bash exp-8/run_stage234_on_hpc.sh

or pass a Python explicitly:

  STAGE234_PYTHON=/path/to/python bash exp-8/run_stage234_on_hpc.sh

If the cluster allows user installs:

  python3 -m pip install --user numpy scipy
  bash exp-8/run_stage234_on_hpc.sh

EOF
  exit 42
fi

echo
echo "=== 1) Build local exp-8 base workspace ==="
"$PYTHON_BIN" "$SCRIPT_DIR/tools/build_stage234_pipeline.py"

echo
echo "=== 2) Run exp-8 Stage2/3/4 certification pass ==="
"$PYTHON_BIN" - "$SCRIPT_DIR" "$OUT_DIR" "$DUMP_ROOT" \
  "$LP_TIME_LIMIT" "$MILP_TIME_LIMIT" "$LP_MAX_N" "$LP_MAX_INCIDENCE" \
  "$MILP_MAX_N" "$MILP_MAX_INCIDENCE" "$MILP_MAX_GAP" <<'PY'
from __future__ import annotations

import csv
import hashlib
import json
import math
import os
import re
import sys
import time
from collections import defaultdict
from pathlib import Path

import numpy as np
from scipy.optimize import Bounds, LinearConstraint, linprog, milp
from scipy.sparse import coo_matrix


EXP8 = Path(sys.argv[1])
OUT = Path(sys.argv[2])
DUMP_ROOT = Path(sys.argv[3])
LP_TIME_LIMIT = float(sys.argv[4])
MILP_TIME_LIMIT = float(sys.argv[5])
LP_MAX_N = int(sys.argv[6])
LP_MAX_INCIDENCE = int(sys.argv[7])
MILP_MAX_N = int(sys.argv[8])
MILP_MAX_INCIDENCE = int(sys.argv[9])
MILP_MAX_GAP = int(sys.argv[10])

BEST_RE = re.compile(r"\[BestSolution\]\s+size=(\d+)\s+cost=(\d+)\s+vertices=([0-9, ]*)")


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict[str, object]], fieldnames: list[str] | None = None) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if fieldnames is None:
        fieldnames = list(rows[0].keys()) if rows else []
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def to_int(value: object, default: int = 0) -> int:
    if value in ("", None):
        return default
    return int(float(str(value)))


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def read_solver_weighted_clq(path: Path) -> tuple[int, list[int], list[tuple[int, int]]]:
    n = 0
    weights: list[int] = []
    edges: list[tuple[int, int]] = []
    for raw in path.read_text(errors="ignore").splitlines():
        line = raw.strip()
        if not line or line.startswith("c"):
            continue
        parts = line.split()
        if parts[0] == "p":
            n = int(parts[2])
            weights = [((i + 1) % 200) + 1 for i in range(n)]
        elif parts[0] == "v":
            if not weights:
                raise ValueError(f"weight line before p line in {path}")
            weights[int(parts[1]) - 1] = int(parts[2])
        elif parts[0] == "e":
            edges.append((int(parts[1]) - 1, int(parts[2]) - 1))
    if n <= 0:
        raise ValueError(f"missing p line in {path}")
    return n, weights, edges


def closed_neighborhoods(n: int, edges: list[tuple[int, int]]) -> list[set[int]]:
    adj = [set([i]) for i in range(n)]
    for u, v in edges:
        if 0 <= u < n and 0 <= v < n and u != v:
            adj[u].add(v)
            adj[v].add(u)
    return adj


def incidence_size(n: int, edges: list[tuple[int, int]]) -> int:
    return n + 2 * len(edges)


def lp_dual_certificate(instance_path: Path, cert_path: Path) -> dict[str, object]:
    start = time.monotonic()
    n, weights, edges = read_solver_weighted_clq(instance_path)
    adj = closed_neighborhoods(n, edges)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for candidate, covered in enumerate(adj):
        for demand in covered:
            rows.append(candidate)
            cols.append(demand)
            data.append(1.0)
    matrix = coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()
    res = linprog(
        c=-np.ones(n),
        A_ub=matrix,
        b_ub=np.array(weights, dtype=float),
        bounds=[(0, None)] * n,
        method="highs",
        options={"time_limit": LP_TIME_LIMIT},
    )
    if not res.success:
        raise RuntimeError(res.message)
    y = np.maximum(res.x, 0.0)
    loads = matrix @ y
    weights_np = np.array(weights, dtype=float)
    ratios = np.divide(loads, weights_np, out=np.zeros_like(loads), where=weights_np > 0)
    shrink = max(1.0, float(np.max(ratios)) * (1.0 + 1e-12))
    y = y / shrink
    loads = matrix @ y
    max_violation = float(np.max(loads - weights_np)) if n else 0.0
    if max_violation > 1e-8:
        raise RuntimeError(f"dual violation after shrink: {max_violation}")
    objective = float(np.sum(y))
    cert = {
        "format": "mwds-solver-weighted-fullgraph-setcover-dual-v1",
        "instance": str(instance_path),
        "instance_sha256": sha256(instance_path),
        "weight_interpretation": "solver_default_i_mod_200_plus_1_unless_explicit_v",
        "n": n,
        "m": len(edges),
        "incidence": len(data),
        "time_limit": LP_TIME_LIMIT,
        "elapsed_sec": round(time.monotonic() - start, 6),
        "verified_objective": objective,
        "verified_floor": int(objective + 1e-7),
        "max_violation": max_violation,
        "positive_duals": int(np.sum(y > 1e-10)),
    }
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n")
    return cert


def full_milp_certificate(instance_path: Path, cert_path: Path, case_id: str) -> dict[str, object]:
    start = time.monotonic()
    n, weights, edges = read_solver_weighted_clq(instance_path)
    adj = closed_neighborhoods(n, edges)
    rows: list[int] = []
    cols: list[int] = []
    data: list[float] = []
    for demand in range(n):
        for candidate in adj[demand]:
            rows.append(demand)
            cols.append(candidate)
            data.append(1.0)
    matrix = coo_matrix((data, (rows, cols)), shape=(n, n)).tocsr()
    res = milp(
        c=np.array(weights, dtype=float),
        integrality=np.ones(n),
        bounds=Bounds(0, 1),
        constraints=LinearConstraint(matrix, np.ones(n), np.full(n, np.inf)),
        options={"time_limit": MILP_TIME_LIMIT, "mip_rel_gap": 0},
    )
    if not res.success or int(res.status) != 0:
        raise RuntimeError(f"status={res.status} message={res.message}")
    selected = [idx + 1 for idx, value in enumerate(res.x) if value >= 0.5]
    objective = int(round(float(res.fun)))
    cost = sum(weights[v - 1] for v in selected)
    if cost != objective:
        raise RuntimeError(f"selected cost mismatch: {cost} vs {objective}")
    cert = {
        "format": "mwds-solver-weighted-full-milp-opt-v1",
        "case_id": case_id,
        "instance": str(instance_path),
        "instance_sha256": sha256(instance_path),
        "weight_interpretation": "solver_default_i_mod_200_plus_1_unless_explicit_v",
        "n": n,
        "m": len(edges),
        "incidence": len(data),
        "time_limit": MILP_TIME_LIMIT,
        "elapsed_sec": round(time.monotonic() - start, 6),
        "optimal_cost": objective,
        "selected_size": len(selected),
        "mip_status": int(res.status),
        "mip_success": bool(res.success),
        "mip_message": str(res.message),
        "mip_dual_bound": getattr(res, "mip_dual_bound", None),
        "mip_gap": getattr(res, "mip_gap", None),
        "selected_vertices": selected,
    }
    cert_path.parent.mkdir(parents=True, exist_ok=True)
    cert_path.write_text(json.dumps(cert, indent=2, sort_keys=True) + "\n")
    return cert


def resolve_instances() -> dict[tuple[str, str], Path]:
    manifest = json.loads((EXP8 / "dataset_manifest.json").read_text())
    resolved: dict[tuple[str, str], Path] = {}
    for selected_file in sorted((EXP8 / "selected_instances").glob("*.txt")):
        dataset = selected_file.stem
        base = Path(manifest[dataset]["hpc_path"])
        names = [line.strip() for line in selected_file.read_text().splitlines() if line.strip()]
        for name in names:
            match = None
            for cur, _dirs, files in os.walk(base):
                if name in files:
                    match = Path(cur) / name
                    break
            if match is None:
                raise SystemExit(f"missing instance {dataset}/{name} under {base}")
            resolved[(dataset, name)] = match
    return resolved


def verify_dump(instance_path: Path, raw_output: Path) -> dict[str, object] | None:
    matches = list(BEST_RE.finditer(raw_output.read_text(errors="ignore")))
    if not matches:
        return None
    match = matches[-1]
    declared_size = int(match.group(1))
    declared_cost = int(match.group(2))
    vertices = [int(x) for x in re.split(r"[,\s]+", match.group(3).strip()) if x]
    n, weights, edges = read_solver_weighted_clq(instance_path)
    adj = closed_neighborhoods(n, edges)
    selected = {v - 1 for v in vertices}
    invalid = [v for v in vertices if v < 1 or v > n]
    covered: set[int] = set()
    for v in selected:
        if 0 <= v < n:
            covered |= adj[v]
    recomputed_cost = sum(weights[v] for v in selected if 0 <= v < n)
    verified = declared_size == len(selected) and declared_cost == recomputed_cost and len(covered) == n and not invalid
    return {
        "raw_output": str(raw_output),
        "declared_size": declared_size,
        "declared_cost": declared_cost,
        "recomputed_cost": recomputed_cost,
        "covered_vertices": len(covered),
        "n": n,
        "verified": verified,
    }


def recompute_fields(row: dict[str, object]) -> None:
    base_lb = to_int(row["pipeline_base_lb"])
    base_ub = to_int(row["pipeline_base_ub"])
    lb = to_int(row["pipeline_best_lb"])
    ub = to_int(row["pipeline_best_ub"])
    row["pipeline_delta_lb"] = lb - base_lb
    row["pipeline_delta_ub"] = ub - base_ub
    row["pipeline_base_absolute_gap"] = base_ub - base_lb
    row["pipeline_absolute_gap"] = ub - lb
    row["pipeline_delta_absolute_gap"] = (ub - lb) - (base_ub - base_lb)
    row["pipeline_certified_opt"] = int(ub == lb)


resolved = resolve_instances()
base_rows = read_csv(OUT / "exp8_pipeline_base.csv")
fieldnames = list(base_rows[0].keys())

print(f"resolved instances: {len(resolved)}")

# Stage2: verified full LP dual certificates.
stage2_rows = [dict(row) for row in base_rows]
stage2_manifest: list[dict[str, object]] = []
for key, instance_path in sorted(resolved.items()):
    dataset, instance = key
    n, _weights, edges = read_solver_weighted_clq(instance_path)
    inc = incidence_size(n, edges)
    cert_rel = Path("stage234") / "certificates" / "lb" / dataset / f"{instance}.lp_dual.json"
    cert_path = EXP8 / cert_rel
    status = "skipped"
    reason = ""
    floor = ""
    applied_rows = 0
    if n > LP_MAX_N or inc > LP_MAX_INCIDENCE:
        reason = f"size_gate n={n} incidence={inc}"
    else:
        try:
            cert = lp_dual_certificate(instance_path, cert_path)
            floor = cert["verified_floor"]
            status = "verified"
            for row in stage2_rows:
                if row["dataset"] == dataset and row["instance"] == instance:
                    old_lb = to_int(row["pipeline_best_lb"])
                    old_ub = to_int(row["pipeline_best_ub"])
                    if int(floor) > old_lb and int(floor) <= old_ub:
                        row["pipeline_best_lb"] = int(floor)
                        row["stage2_lb_applied"] = 1
                        recompute_fields(row)
                        applied_rows += 1
        except Exception as exc:
            status = "failed"
            reason = str(exc)
    stage2_manifest.append(
        {
            "dataset": dataset,
            "instance": instance,
            "instance_path": str(instance_path),
            "n": n,
            "incidence": inc,
            "status": status,
            "reason": reason,
            "verified_floor": floor,
            "certificate_path": str(cert_path) if status == "verified" else "",
            "applied_rows": applied_rows,
        }
    )
write_csv(OUT / "stage2_lb_certified.csv", stage2_rows, fieldnames)
write_csv(OUT / "stage2_lb_certificate_manifest.csv", stage2_manifest)

# Stage3: verify dumps if present, but never apply numeric UB without vertices.
stage3_rows = [dict(row) for row in stage2_rows]
stage3_manifest: list[dict[str, object]] = []
dump_files = list(DUMP_ROOT.glob("**/*.out"))
for key, instance_path in sorted(resolved.items()):
    dataset, instance = key
    candidates = [p for p in dump_files if p.name == f"{instance}.out"]
    best_verified: dict[str, object] | None = None
    for raw in candidates:
        result = verify_dump(instance_path, raw)
        if result and result["verified"]:
            if best_verified is None or int(result["recomputed_cost"]) < int(best_verified["recomputed_cost"]):
                best_verified = result
    applied_rows = 0
    if best_verified is not None:
        ub = int(best_verified["recomputed_cost"])
        for row in stage3_rows:
            if row["dataset"] == dataset and row["instance"] == instance:
                old_ub = to_int(row["pipeline_best_ub"])
                lb = to_int(row["pipeline_best_lb"])
                if ub < old_ub and ub >= lb:
                    row["pipeline_best_ub"] = ub
                    row["stage3_ub_applied"] = 1
                    recompute_fields(row)
                    applied_rows += 1
    stage3_manifest.append(
        {
            "dataset": dataset,
            "instance": instance,
            "candidate_dumps": len(candidates),
            "verified_dump_path": best_verified["raw_output"] if best_verified else "",
            "verified_ub": best_verified["recomputed_cost"] if best_verified else "",
            "applied_rows": applied_rows,
            "status": "verified" if best_verified else "no_verified_dump",
        }
    )
write_csv(OUT / "stage3_ub_verified.csv", stage3_rows, fieldnames)
write_csv(OUT / "stage3_ub_verified_manifest.csv", stage3_manifest)

# Stage4: exact closure for small current-gap candidates.
stage4_rows = [dict(row) for row in stage3_rows]
best_gap_by_instance: dict[tuple[str, str], int] = {}
for row in stage3_rows:
    key = (row["dataset"], row["instance"])
    gap = to_int(row["pipeline_absolute_gap"])
    best_gap_by_instance[key] = min(gap, best_gap_by_instance.get(key, gap))

stage4_manifest: list[dict[str, object]] = []
for key, gap in sorted(best_gap_by_instance.items(), key=lambda item: (item[1], item[0])):
    dataset, instance = key
    instance_path = resolved[key]
    n, _weights, edges = read_solver_weighted_clq(instance_path)
    inc = incidence_size(n, edges)
    cert_rel = Path("stage234") / "certificates" / "exact" / dataset / f"{instance}.full_milp_opt.json"
    cert_path = EXP8 / cert_rel
    status = "skipped"
    reason = ""
    opt = ""
    applied_rows = 0
    if gap == 0:
        status = "already_closed_by_solver"
    elif gap > MILP_MAX_GAP:
        reason = f"gap_gate gap={gap}"
    elif n > MILP_MAX_N or inc > MILP_MAX_INCIDENCE:
        reason = f"size_gate n={n} incidence={inc}"
    else:
        try:
            cert = full_milp_certificate(instance_path, cert_path, f"{dataset}:{instance}")
            opt = int(cert["optimal_cost"])
            status = "verified_opt"
            for row in stage4_rows:
                if row["dataset"] == dataset and row["instance"] == instance:
                    lb = to_int(row["pipeline_best_lb"])
                    ub = to_int(row["pipeline_best_ub"])
                    if lb <= opt <= ub:
                        row["pipeline_best_lb"] = opt
                        row["pipeline_best_ub"] = opt
                        row["stage4_exact_applied"] = 1
                        row["pipeline_new_certified_opt"] = 0 if to_int(row["pipeline_base_absolute_gap"]) == 0 else 1
                        recompute_fields(row)
                        applied_rows += 1
                    else:
                        reason = f"opt outside current bounds lb={lb} opt={opt} ub={ub}"
        except Exception as exc:
            status = "failed"
            reason = str(exc)
    stage4_manifest.append(
        {
            "dataset": dataset,
            "instance": instance,
            "current_best_gap": gap,
            "n": n,
            "incidence": inc,
            "status": status,
            "reason": reason,
            "verified_opt": opt,
            "certificate_path": str(cert_path) if status == "verified_opt" else "",
            "applied_rows": applied_rows,
        }
    )
write_csv(OUT / "stage4_exact_closed.csv", stage4_rows, fieldnames)
write_csv(OUT / "stage4_exact_closure_manifest.csv", stage4_manifest)


def summarise(rows: list[dict[str, object]], version: str) -> dict[str, object]:
    certified = sum(to_int(row["pipeline_certified_opt"]) for row in rows)
    return {
        "version": version,
        "rows": len(rows),
        "certified_total": certified,
        "new_certified_total": sum(to_int(row["pipeline_new_certified_opt"]) for row in rows),
        "open_rows": len(rows) - certified,
        "lb_gt_ub_rows": sum(1 for row in rows if to_int(row["pipeline_best_lb"]) > to_int(row["pipeline_best_ub"])),
        "total_delta_lb": sum(to_int(row["pipeline_delta_lb"]) for row in rows),
        "total_delta_ub": sum(to_int(row["pipeline_delta_ub"]) for row in rows),
        "total_delta_gap": sum(to_int(row["pipeline_delta_absolute_gap"]) for row in rows),
    }


versions = [
    summarise(base_rows, "plus_aco"),
    summarise(stage2_rows, "plus_verified_lb_certificate"),
    summarise(stage3_rows, "plus_verified_ub_portfolio"),
    summarise(stage4_rows, "plus_exact_closure"),
]
write_csv(OUT / "version_summary.csv", versions)

grouped: dict[str, list[dict[str, object]]] = defaultdict(list)
for row in stage4_rows:
    grouped[row["dataset"]].append(row)
family_rows = []
for dataset, rows in sorted(grouped.items()):
    item = summarise(rows, dataset)
    item["family"] = dataset
    del item["version"]
    family_rows.append(item)
write_csv(
    OUT / "family_summary.csv",
    family_rows,
    ["family", "rows", "certified_total", "new_certified_total", "open_rows", "lb_gt_ub_rows", "total_delta_lb", "total_delta_ub", "total_delta_gap"],
)

report = ["# exp-8 Stage234 HPC Run Report", "", "## Version Summary", ""]
report.append("| version | rows | certified | new certified | open | delta LB | delta UB | delta gap | LB>UB |")
report.append("|---|---:|---:|---:|---:|---:|---:|---:|---:|")
for row in versions:
    report.append(
        f"| {row['version']} | {row['rows']} | {row['certified_total']} | {row['new_certified_total']} | "
        f"{row['open_rows']} | {row['total_delta_lb']} | {row['total_delta_ub']} | {row['total_delta_gap']} | {row['lb_gt_ub_rows']} |"
    )
report.extend(
    [
        "",
        "## Manifests",
        "",
        "- `stage2_lb_certificate_manifest.csv`",
        "- `stage3_ub_verified_manifest.csv`",
        "- `stage4_exact_closure_manifest.csv`",
        "",
        "Only verifier-backed artifacts are applied. Numeric solver CSV values are not treated as verified UB or exact closure certificates.",
        "",
    ]
)
(OUT / "HPC_REPORT.md").write_text("\n".join(report))

print("wrote:")
print(f"  {OUT / 'version_summary.csv'}")
print(f"  {OUT / 'HPC_REPORT.md'}")
PY

echo
echo "=== 3) Final summary ==="
if [ -f "$OUT_DIR/version_summary.csv" ]; then
  python3 - <<'PY' "$OUT_DIR/version_summary.csv"
import csv, sys
for row in csv.DictReader(open(sys.argv[1], newline="")):
    print(row)
PY
fi

echo
echo "Done. Inspect:"
echo "  $OUT_DIR/HPC_REPORT.md"
echo "  $OUT_DIR/stage2_lb_certificate_manifest.csv"
echo "  $OUT_DIR/stage3_ub_verified_manifest.csv"
echo "  $OUT_DIR/stage4_exact_closure_manifest.csv"
