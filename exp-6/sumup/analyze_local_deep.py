#!/usr/bin/env python3
"""
Minimal pairwise analyzer for the local deep-v6 vs deep-v10 test.

Reuses exp-6 sumup.py's file parsing and pairwise logic, but skips the
"standard 9-solver" expectations so it works with just 2 solvers.
"""
import sys
from pathlib import Path
from collections import defaultdict

# Reuse parsers from the main sumup
sys.path.insert(0, str(Path(__file__).parent))
from sumup import (
    parse_out_file, extract_solver_seed, compute_gap,
    per_instance_avg_gap, pairwise,
)

RESULT_ROOT = Path(sys.argv[1] if len(sys.argv) > 1 else "../jobs/result_local_deep")
OUT_DIR = Path(sys.argv[2] if len(sys.argv) > 2 else "../analysis_local_deep")
OUT_DIR.mkdir(parents=True, exist_ok=True)

rows = []
for entry in sorted(RESULT_ROOT.iterdir()):
    if not entry.is_dir() or not entry.name.startswith("result-"):
        continue
    solver, seed = extract_solver_seed(entry.name)
    if solver is None:
        print(f"SKIP (bad name): {entry.name}")
        continue
    for out_file in sorted(entry.glob("*.out")):
        summary, rounds = parse_out_file(out_file)
        if summary is None:
            continue
        g = compute_gap(summary["best_ub"], summary["best_lb"])
        rows.append({
            "solver": solver, "seed": seed, "instance": summary["instance"],
            "V": summary["V"], "E": summary["E"],
            "best_lb": summary["best_lb"], "best_ub": summary["best_ub"],
            "gap": g, "status": summary["status"],
        })

print(f"Parsed {len(rows)} records")
solvers = sorted({r["solver"] for r in rows})
print(f"Solvers: {solvers}")
seeds = sorted({r["seed"] for r in rows})
print(f"Seeds: {seeds}")

# --- per-solver stats
lines = ["# Local deep comparison (300s, alpha=90)\n"]
lines.append(f"- Solvers: {solvers}\n- Seeds: {seeds}\n- Total records: {len(rows)}\n")
lines.append("\n## Per-solver stats\n\n")
lines.append("| Solver | n | Avg Gap | Med Gap | #opt | gap<=0.01 | gap<=0.1 |\n")
lines.append("|---|---|---|---|---|---|---|\n")
for sv in solvers:
    sub = [r for r in rows if r["solver"] == sv]
    gaps = sorted(r["gap"] for r in sub if r["gap"] >= 0)
    n = len(sub); nv = len(gaps)
    avg = sum(gaps)/nv if nv else 0
    med = gaps[nv//2] if nv else 0
    n_opt = sum(1 for r in sub if r["status"] == "OPT")
    n_001 = sum(1 for g in gaps if g <= 0.01)
    n_01  = sum(1 for g in gaps if g <= 0.1)
    lines.append(f"| {sv} | {n} | {avg:.4f} | {med:.4f} | {n_opt} ({n_opt/n*100:.1f}%) | "
                 f"{n_001} ({n_001/n*100:.1f}%) | {n_01} ({n_01/n*100:.1f}%) |\n")

# --- pairwise v6 vs v10 (if both present)
if len(solvers) == 2:
    s1, s2 = solvers
    w, l, t, total = pairwise(rows, s1, s2)
    lines.append(f"\n## Pairwise: {s1} vs {s2}\n\n")
    lines.append(f"- {s1} wins: **{w}**\n- {s2} wins: **{l}**\n- Ties: **{t}**\n- Total common: **{total}**\n")
    net = w - l
    lines.append(f"- Net (rows=s1, s2): **{net:+d}**\n")
    if w > l:
        lines.append(f"\n**{s1}** wins head-to-head (net +{net})\n")
    elif l > w:
        lines.append(f"\n**{s2}** wins head-to-head (net {-net:+d})\n")
    else:
        lines.append(f"\n**Tied**\n")

    # Also show per-seed to check stability
    lines.append("\n## Per-seed breakdown\n\n")
    lines.append("| Seed | " + s1 + " avg gap | " + s2 + " avg gap |\n")
    lines.append("|---|---|---|\n")
    for sd in seeds:
        g1 = [r["gap"] for r in rows if r["solver"]==s1 and r["seed"]==sd and r["gap"]>=0]
        g2 = [r["gap"] for r in rows if r["solver"]==s2 and r["seed"]==sd and r["gap"]>=0]
        a1 = sum(g1)/len(g1) if g1 else 0
        a2 = sum(g2)/len(g2) if g2 else 0
        lines.append(f"| {sd} | {a1:.4f} ({len(g1)}) | {a2:.4f} ({len(g2)}) |\n")

# --- write report + csv
report = OUT_DIR / "local_deep_report.md"
report.write_text("".join(lines))
print(f"Report: {report}")

csv_path = OUT_DIR / "local_deep_results.csv"
with csv_path.open("w") as f:
    f.write("solver,seed,instance,V,E,best_lb,best_ub,gap,status\n")
    for r in rows:
        f.write(f"{r['solver']},{r['seed']},{r['instance']},{r['V']},{r['E']},"
                f"{r['best_lb']},{r['best_ub']},{r['gap']:.6f},{r['status']}\n")
print(f"CSV: {csv_path}")
