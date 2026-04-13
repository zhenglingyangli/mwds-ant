#!/usr/bin/env python3
"""
Summarise MWDS dual-bounds experiment results.

Scans result directories, parses solver output (.out files),
extracts per-round convergence data and final >>> summary,
then produces:
  1. A CSV with one row per (solver, dataset, seed, instance).
  2. A Markdown report with gap statistics and pairwise comparisons.

Usage:
    python3 sumup.py  <result_root>  [--output_dir ./analysis]

Example:
    python3 sumup.py  ../jobs/result  --output_dir ./analysis
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================
# Regex patterns for parsing solver output
# ============================================================

# Final summary:  >>> name |V| 1000 |E| 10000  (#LB 0.1144 1014 ---> 1130  0.8646  2107 <--- 2658  0.2073 #UB)
RE_SUMMARY = re.compile(
    r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+"
    r"\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+"
    r"([\d.]+)\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)"
)
# Optimal (LB==UB):  >>> name |V| ... ---> LB  ====  UB <--- ...
RE_OPTIMAL = re.compile(
    r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+"
    r"\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+====\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)"
)
# Timeout/memout sentinel written by goSolver:  >>> Benchmark name Status TIMEOUT TimeTotal 300.000
RE_TIMEOUT = re.compile(
    r">>>\s+Benchmark\s+(\S+)\s+Status\s+(TIMEOUT|MEMOUT)"
)
# Per-round line (9-col full):  round  LB  LB*  UB_lb  time_lb  UB+  UB*  time_ub  TotalTime
RE_ROUND_FULL = re.compile(
    r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)"
    r"\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s*$"
)
# Per-round line (5-col short, LB phase only):  round  LB  LB*  UB_lb  time_lb
RE_ROUND_SHORT = re.compile(
    r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s*$"
)


def parse_out_file(filepath):
    """Return (summary_dict, rounds_list) from a .out file."""
    text = Path(filepath).read_text(errors="replace")
    lines = text.splitlines()

    # --- Parse final summary ---
    summary = None
    for line in reversed(lines):
        m = RE_SUMMARY.search(line)
        if m:
            summary = {
                "instance": m.group(1), "V": int(m.group(2)), "E": int(m.group(3)),
                "lgap": float(m.group(4)), "first_lb": int(m.group(5)),
                "best_lb": int(m.group(6)), "final_gap": float(m.group(7)),
                "best_ub": int(m.group(8)), "first_ub": int(m.group(9)),
                "ugap": float(m.group(10)), "status": "OK",
            }
            break
        m = RE_OPTIMAL.search(line)
        if m:
            summary = {
                "instance": m.group(1), "V": int(m.group(2)), "E": int(m.group(3)),
                "lgap": float(m.group(4)), "first_lb": int(m.group(5)),
                "best_lb": int(m.group(6)), "best_ub": int(m.group(7)),
                "first_ub": int(m.group(8)), "ugap": float(m.group(9)),
                "final_gap": 0.0, "status": "OPT",
            }
            break
        m = RE_TIMEOUT.search(line)
        if m:
            summary = {
                "instance": m.group(1), "V": 0, "E": 0,
                "lgap": 0, "first_lb": 0, "best_lb": 0,
                "final_gap": -1, "best_ub": 0, "first_ub": 0,
                "ugap": 0, "status": m.group(2),
            }
            break

    # --- Parse per-round convergence data ---
    rounds = []
    for line in lines:
        m = RE_ROUND_FULL.match(line)
        if m:
            rounds.append({
                "rd": int(m.group(1)),
                "lb": int(m.group(2)), "lb_best": int(m.group(3)),
                "ub_lb": int(m.group(4)), "time_lb": float(m.group(5)),
                "ub_plus": int(m.group(6)), "ub_best": int(m.group(7)),
                "time_ub": float(m.group(8)), "total_time": float(m.group(9)),
            })
            continue
        m = RE_ROUND_SHORT.match(line)
        if m:
            rounds.append({
                "rd": int(m.group(1)),
                "lb": int(m.group(2)), "lb_best": int(m.group(3)),
                "ub_lb": int(m.group(4)), "time_lb": float(m.group(5)),
                "ub_plus": 0, "ub_best": 0, "time_ub": 0, "total_time": 0,
            })

    return summary, rounds


def extract_solver_seed(dirname):
    """
    Parse result directory name to extract solver and seed.
    Format: result-<binary>-<dataset>-<solver>-<DS>-seed<N>-<timestamp>
    """
    m = re.search(r"-([^-]+-[^-]+)-seed(\d+)-\d{14}$", dirname)
    if m:
        return m.group(1), int(m.group(2))
    m = re.search(r"-seed(\d+)", dirname)
    if m:
        parts = dirname.split("-")
        seed = int(m.group(1))
        solver_name = "-".join(parts[1:-2]) if len(parts) > 3 else parts[1]
        return solver_name, seed
    return dirname, 0


def compute_gap(ub, lb):
    """Unified gap = (UB - LB) / LB, consistent with the paper."""
    if lb > 0 and ub > 0:
        return (ub - lb) / lb
    return -1.0


def scan_results(result_root):
    """Scan all result directories and return list of row dicts."""
    rows = []
    root = Path(result_root)
    if not root.is_dir():
        print(f"ERROR: {result_root} is not a directory", file=sys.stderr)
        return rows

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("result-"):
            continue
        solver_name, seed = extract_solver_seed(entry.name)

        for out_file in sorted(entry.glob("*.out")):
            summary, rounds = parse_out_file(out_file)
            if summary is None:
                continue

            gap = compute_gap(summary["best_ub"], summary["best_lb"])

            # Build convergence snapshots at key time points
            checkpoints = {}
            if rounds:
                running_lb = 0
                running_ub = float("inf")
                for r in rounds:
                    running_lb = max(running_lb, r["lb_best"])
                    if r["ub_best"] > 0:
                        running_ub = min(running_ub, r["ub_best"])
                    if r["total_time"] > 0:
                        for t in [10, 30, 60, 120, 300]:
                            if t not in checkpoints and r["total_time"] >= t:
                                g = compute_gap(running_ub if running_ub < float("inf") else 0, running_lb)
                                checkpoints[t] = g

            rows.append({
                "solver": solver_name,
                "seed": seed,
                "instance": summary["instance"],
                "V": summary["V"],
                "E": summary["E"],
                "first_lb": summary["first_lb"],
                "best_lb": summary["best_lb"],
                "first_ub": summary["first_ub"],
                "best_ub": summary["best_ub"],
                "gap": round(gap, 6),
                "status": summary["status"],
                "gap_10s": round(checkpoints.get(10, -1), 6),
                "gap_30s": round(checkpoints.get(30, -1), 6),
                "gap_60s": round(checkpoints.get(60, -1), 6),
                "gap_120s": round(checkpoints.get(120, -1), 6),
                "gap_300s": round(checkpoints.get(300, -1), 6),
                "n_rounds": len(rounds),
            })
    return rows


def write_csv(rows, filepath):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  CSV: {filepath}  ({len(rows)} rows)")


def generate_report(rows, filepath):
    """Generate a Markdown summary report."""
    solvers = sorted(set(r["solver"] for r in rows))
    instances = sorted(set(r["instance"] for r in rows))

    with open(filepath, "w") as f:
        f.write("# MWDS Exp-1 Summary Report\n\n")
        f.write(f"- Solvers: {len(solvers)}\n")
        f.write(f"- Instances: {len(instances)}\n")
        f.write(f"- Total rows: {len(rows)}\n\n")

        # --- Per-solver statistics ---
        f.write("## 1. Per-solver Gap Statistics\n\n")
        f.write("| Solver | n | Avg Gap | Med Gap | #opt | gap≤0.01 | gap≤0.1 |\n")
        f.write("|--------|---|---------|---------|------|----------|--------|\n")

        for sv in solvers:
            sub = [r for r in rows if r["solver"] == sv and r["gap"] >= 0]
            if not sub:
                continue
            # Per-instance avg gap across seeds
            inst_gaps = defaultdict(list)
            for r in sub:
                inst_gaps[r["instance"]].append(r["gap"])
            avg_gaps = {k: sum(v) / len(v) for k, v in inst_gaps.items()}
            gaps = sorted(avg_gaps.values())
            n = len(gaps)
            avg = sum(gaps) / n
            med = gaps[n // 2]
            opt = sum(1 for g in gaps if g == 0)
            le2 = sum(1 for g in gaps if g <= 0.01)
            le1 = sum(1 for g in gaps if g <= 0.1)
            f.write(f"| {sv} | {n} | {avg:.4f} | {med:.4f} | "
                    f"{opt} ({opt/n*100:.1f}%) | {le2} ({le2/n*100:.1f}%) | "
                    f"{le1} ({le1/n*100:.1f}%) |\n")

        # --- Pairwise comparisons ---
        f.write("\n## 2. Pairwise Gap Comparison\n\n")
        f.write("Each cell: wins / losses / ties (based on per-instance avg gap across seeds).\n\n")

        if len(solvers) > 1:
            f.write("| vs | " + " | ".join(solvers) + " |\n")
            f.write("|" + "---|" * (len(solvers) + 1) + "\n")
            for s1 in solvers:
                cells = []
                for s2 in solvers:
                    if s1 == s2:
                        cells.append("-")
                        continue
                    w, l, t = 0, 0, 0
                    for inst in instances:
                        r1 = [r for r in rows if r["solver"] == s1 and r["instance"] == inst and r["gap"] >= 0]
                        r2 = [r for r in rows if r["solver"] == s2 and r["instance"] == inst and r["gap"] >= 0]
                        if not r1 or not r2:
                            continue
                        g1 = sum(r["gap"] for r in r1) / len(r1)
                        g2 = sum(r["gap"] for r in r2) / len(r2)
                        if abs(g1 - g2) < 1e-6:
                            t += 1
                        elif g1 < g2:
                            w += 1
                        else:
                            l += 1
                    cells.append(f"{w}/{l}/{t}")
                f.write(f"| {s1} | " + " | ".join(cells) + " |\n")

        # --- Convergence over time ---
        f.write("\n## 3. Gap Convergence Over Time\n\n")
        f.write("Average gap at each time checkpoint (only rows with valid data).\n\n")
        time_cols = ["gap_10s", "gap_30s", "gap_60s", "gap_120s", "gap_300s"]
        f.write("| Solver | 10s | 30s | 60s | 120s | 300s | final |\n")
        f.write("|--------|-----|-----|-----|------|------|-------|\n")
        for sv in solvers:
            sub = [r for r in rows if r["solver"] == sv]
            vals = []
            for col in time_cols:
                valid = [r[col] for r in sub if r[col] >= 0]
                vals.append(f"{sum(valid)/len(valid):.4f}" if valid else "-")
            final_valid = [r["gap"] for r in sub if r["gap"] >= 0]
            final = f"{sum(final_valid)/len(final_valid):.4f}" if final_valid else "-"
            f.write(f"| {sv} | " + " | ".join(vals) + f" | {final} |\n")

        f.write("\n---\n*Generated by sumup.py*\n")

    print(f"  Report: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Summarise MWDS experiment results.")
    parser.add_argument("result_root", help="Root directory containing result-* folders")
    parser.add_argument("--output_dir", default="./analysis", help="Output directory for CSV and report")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Scanning {args.result_root} ...")
    rows = scan_results(args.result_root)
    if not rows:
        print("No results found.")
        return

    print(f"Found {len(rows)} records from {len(set(r['solver'] for r in rows))} solvers.")

    csv_path = os.path.join(args.output_dir, "exp1_results.csv")
    report_path = os.path.join(args.output_dir, "exp1_report.md")

    write_csv(rows, csv_path)
    generate_report(rows, report_path)
    print("Done.")


if __name__ == "__main__":
    main()
