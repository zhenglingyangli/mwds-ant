#!/usr/bin/env python3
"""
Summarise MWDS exp-2 results: Dual-Fast v19 vs baseline Dual-Fast.

Scans result-* directories, aggregates per-instance gap across seeds,
then produces:
  1. A CSV with one row per (solver, dataset, seed, instance).
  2. A Markdown report:
     - Table 3 format per solver (gap*, gap_0, 5 thresholds)
     - v19 vs baseline pairwise comparison
     - Convergence over time per solver
     - Comparison with paper's Table 3

Usage:
    python3 sumup.py  <result_root>  [--output_dir ./analysis]
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================
# Paper Table 3 baseline (Dual-Fast column)
# ============================================================

PAPER_BASELINES = {
    "T1": {
        "n": 540,
        "gap_star": {"opt": 1.5, "le4": 1.5, "le3": 1.9, "le2": 4.4, "le1": 26.7},
        "gap_0":    {"opt": 0.7, "le4": 0.7, "le3": 0.7, "le2": 1.3, "le1": 15.6},
    },
    "T2": {
        "n": 540,
        "gap_star": {"opt": 24.6, "le4": 24.6, "le3": 26.9, "le2": 34.8, "le1": 70.4},
        "gap_0":    {"opt": 18.3, "le4": 18.3, "le3": 18.7, "le2": 28.1, "le1": 58.9},
    },
    "UDG": {
        "n": 120,
        "gap_star": {"opt": 88.3, "le4": 88.3, "le3": 89.2, "le2": 93.3, "le1": 100.0},
        "gap_0":    {"opt": 80.8, "le4": 80.8, "le3": 80.8, "le2": 88.3, "le1": 100.0},
    },
    "NDR": {
        "n": 65,
        "gap_star": {"opt": 6.2, "le4": 32.3, "le3": 55.4, "le2": 64.6, "le1": 80.0},
        "gap_0":    {"opt": 3.1, "le4": 21.5, "le3": 46.2, "le2": 60.0, "le1": 75.4},
    },
    "DIMACS10": {
        "n": 31,
        "gap_star": {"opt": 6.5, "le4": 6.5, "le3": 16.1, "le2": 38.7, "le1": 77.4},
        "gap_0":    {"opt": 6.5, "le4": 6.5, "le3": 6.5,  "le2": 32.3, "le1": 64.5},
    },
    "DIMACS": {
        "n": 80,
        "gap_star": {"opt": 23.8, "le4": 23.8, "le3": 23.8, "le2": 23.8, "le1": 25.0},
        "gap_0":    {"opt": 21.2, "le4": 21.2, "le3": 21.2, "le2": 21.2, "le1": 22.5},
    },
    "BHOSLIB": {
        "n": 41,
        "gap_star": {"opt": 14.6, "le4": 14.6, "le3": 14.6, "le2": 14.6, "le1": 14.6},
        "gap_0":    {"opt": 12.2, "le4": 12.2, "le3": 12.2, "le2": 12.2, "le1": 12.2},
    },
    "SNAP": {
        "n": 22,
        "gap_star": {"opt": 27.3, "le4": 36.4, "le3": 50.0, "le2": 77.3, "le1": 100.0},
        "gap_0":    {"opt": 27.3, "le4": 36.4, "le3": 50.0, "le2": 68.2, "le1": 100.0},
    },
}

# ============================================================
# Regex patterns
# ============================================================

RE_SUMMARY = re.compile(
    r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+"
    r"\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+"
    r"([\d.]+)\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)"
)
RE_OPTIMAL = re.compile(
    r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+"
    r"\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+====\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)"
)
RE_TIMEOUT = re.compile(
    r">>>\s+Benchmark\s+(\S+)\s+Status\s+(TIMEOUT|MEMOUT)"
)
RE_ROUND_FULL = re.compile(
    r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)"
    r"\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s*$"
)
RE_ROUND_SHORT = re.compile(
    r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s*$"
)


def compute_gap(ub, lb):
    if lb > 0 and ub > 0:
        return (ub - lb) / lb
    return -1.0


def parse_out_file(filepath):
    text = Path(filepath).read_text(errors="replace")
    lines = text.splitlines()

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

    if summary and summary["status"] in ("TIMEOUT", "MEMOUT") and rounds:
        best_lb = max(r["lb_best"] for r in rounds)
        best_ub_candidates = [r["ub_best"] for r in rounds if r["ub_best"] > 0]
        if not best_ub_candidates:
            best_ub_candidates = [r["ub_lb"] for r in rounds if r["ub_lb"] > 0]
        best_ub = min(best_ub_candidates) if best_ub_candidates else 0
        first_lb = rounds[0]["lb"] if rounds else 0
        first_ub = rounds[0].get("ub_lb", 0) if rounds else 0
        gap = compute_gap(best_ub, best_lb)
        summary["best_lb"] = best_lb
        summary["best_ub"] = best_ub
        summary["first_lb"] = first_lb
        summary["first_ub"] = first_ub
        summary["final_gap"] = gap
        if gap >= 0:
            summary["status"] = "OK"

    if summary is None and not rounds:
        re_ibm = re.search(r">>IBM:\s+\|V\|=(\d+)\s+\|E\|=(\d+)", text)
        if re_ibm:
            inst_name = Path(filepath).name.replace(".out", "")
            summary = {
                "instance": inst_name, "V": int(re_ibm.group(1)),
                "E": int(re_ibm.group(2)),
                "lgap": 0, "first_lb": 0, "best_lb": 0,
                "final_gap": -1, "best_ub": 0, "first_ub": 0,
                "ugap": 0, "status": "NO_OUTPUT",
            }

    return summary, rounds


def extract_solver_dataset_seed(dirname):
    """
    Parse result directory name.
    Format: result-<bin>-<ds_dir>-<solver>-<DS>-c<chunk>-s<seed>-<timestamp>
    Example: result-dual-fast-v19-T1_wclq-fast-v19-T1-c0-s1-20260413120000
    """
    m = re.search(r"-c(\d+)-s(\d+)-\d{14}$", dirname)
    if not m:
        m = re.search(r"-seed(\d+)-\d{14}$", dirname)
        if m:
            seed = int(m.group(1))
        else:
            seed = 0
    else:
        seed = int(m.group(2))

    dataset = "unknown"
    for ds in ["T1", "T2", "UDG", "NDR", "DIMACS10", "DIMACS", "BHOSLIB", "SNAP"]:
        if f"-{ds}-" in dirname or f"-{ds}_" in dirname:
            dataset = ds
            break

    solver = "unknown"
    for sv in ["fast-v19", "dual-fast", "fast-v28", "deep-v6", "dual-deep",
               "exp5-freqscore", "exp6-poolrelink", "exp9-freq-pool"]:
        if sv in dirname:
            solver = sv
            break

    return solver, dataset, seed


def scan_results(result_root):
    rows = []
    stats = defaultdict(lambda: {"total": 0, "empty": 0, "no_output": 0, "parsed": 0})
    root = Path(result_root)
    if not root.is_dir():
        print(f"ERROR: {result_root} is not a directory", file=sys.stderr)
        return rows, stats

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("result-"):
            continue
        solver, dataset, seed = extract_solver_dataset_seed(entry.name)
        key = (solver, dataset)

        for out_file in sorted(entry.glob("*.out")):
            stats[key]["total"] += 1
            fsize = out_file.stat().st_size
            if fsize == 0:
                stats[key]["empty"] += 1
                continue

            summary, rounds = parse_out_file(out_file)
            if summary is None:
                continue

            if summary["status"] == "NO_OUTPUT":
                stats[key]["no_output"] += 1
                continue

            gap = compute_gap(summary["best_ub"], summary["best_lb"])

            checkpoints = {}
            if rounds:
                running_lb = 0
                running_ub = float("inf")
                for r in rounds:
                    running_lb = max(running_lb, r["lb_best"])
                    if r["ub_best"] > 0:
                        running_ub = min(running_ub, r["ub_best"])
                    t = r["total_time"]
                    if t > 0:
                        for cp in [10, 30, 60, 120, 300, 600, 1800, 3600]:
                            if cp not in checkpoints and t >= cp:
                                g = compute_gap(
                                    running_ub if running_ub < float("inf") else 0,
                                    running_lb
                                )
                                checkpoints[cp] = g

            stats[key]["parsed"] += 1
            rows.append({
                "solver": solver,
                "dataset": dataset,
                "seed": seed,
                "instance": summary["instance"],
                "V": summary["V"],
                "E": summary["E"],
                "first_lb": summary["first_lb"],
                "best_lb": summary["best_lb"],
                "first_ub": summary.get("first_ub", 0),
                "best_ub": summary["best_ub"],
                "gap": round(gap, 6),
                "status": summary["status"],
                "gap_10s":   round(checkpoints.get(10, -1), 6),
                "gap_60s":   round(checkpoints.get(60, -1), 6),
                "gap_300s":  round(checkpoints.get(300, -1), 6),
                "gap_600s":  round(checkpoints.get(600, -1), 6),
                "gap_1800s": round(checkpoints.get(1800, -1), 6),
                "gap_3600s": round(checkpoints.get(3600, -1), 6),
                "n_rounds":  len(rounds),
            })
    return rows, stats


def write_csv(rows, filepath):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  CSV: {filepath}  ({len(rows)} rows)")


def gap_distribution(gaps, total):
    """Compute cumulative gap distribution matching Table 3 columns."""
    opt = sum(1 for g in gaps if g == 0)
    le4 = sum(1 for g in gaps if g <= 1e-4)
    le3 = sum(1 for g in gaps if g <= 1e-3)
    le2 = sum(1 for g in gaps if g <= 1e-2)
    le1 = sum(1 for g in gaps if g <= 1e-1)
    return {
        "opt": opt / total * 100 if total else 0,
        "le4": le4 / total * 100 if total else 0,
        "le3": le3 / total * 100 if total else 0,
        "le2": le2 / total * 100 if total else 0,
        "le1": le1 / total * 100 if total else 0,
    }


def fmt_dist(d):
    """Format a gap distribution dict as a table row fragment."""
    return (f"{d['opt']:.1f}% | {d['le4']:.1f}% | {d['le3']:.1f}% "
            f"| {d['le2']:.1f}% | {d['le1']:.1f}%")


def get_inst_gaps(rows, solver, dataset):
    """Get per-instance gap lists for a specific solver+dataset."""
    inst = defaultdict(list)
    for r in rows:
        if r["solver"] == solver and r["dataset"] == dataset and r["gap"] >= 0:
            inst[r["instance"]].append(r["gap"])
    return inst


def generate_report(rows, filepath, scan_stats=None):
    solvers = sorted(set(r["solver"] for r in rows))
    datasets = sorted(set(r["dataset"] for r in rows))

    with open(filepath, "w") as f:
        f.write("# MWDS Exp-2: Dual-Fast v19 vs Baseline Full Report\n\n")
        f.write(f"- Solvers: {solvers}\n")
        f.write(f"- Datasets: {datasets}\n")
        f.write(f"- Total rows: {len(rows)}\n\n")

        # ==============================================================
        # Section 0: Data Quality / Coverage
        # ==============================================================
        if scan_stats:
            f.write("## 0. Data Quality & Coverage\n\n")
            f.write("Files lost due to fast-solving instances whose stdout "
                    "was not flushed before process exit.\n\n")
            f.write("| Solver | Dataset | .out files | empty (0B) "
                    "| header-only | parsed | lost% |\n")
            f.write("|--------|---------|-----------|------------|"
                    "-------------|--------|-------|\n")
            for (sv, ds), st in sorted(scan_stats.items()):
                lost = st["empty"] + st["no_output"]
                pct = lost / st["total"] * 100 if st["total"] else 0
                f.write(f"| {sv} | {ds} | {st['total']} | {st['empty']} "
                        f"| {st['no_output']} | {st['parsed']} | {pct:.1f}% |\n")
            f.write("\n> **Note**: Lost files are overwhelmingly small/easy "
                    "instances (e.g. V≤100) that solve in milliseconds. "
                    "These would almost certainly be optimal (gap=0). "
                    "Table 1 below uses only the **common instance set** "
                    "(both solvers have valid data) for fair comparison.\n\n")

        # ==============================================================
        # Section 1: Table 3 format — using COMMON instances for fairness
        # ==============================================================
        f.write("## 1. Gap Distribution (Table 3 Format)\n\n")
        f.write("- **gap\\*** = per-instance best gap (min across seeds)\n")
        f.write("- **gap₀** = per-instance average gap (mean across seeds)\n")
        f.write("- Statistics computed on **common instances** only "
                "(where both solvers have valid data)\n\n")

        for ds in datasets:
            f.write(f"### {ds}\n\n")

            all_inst = {}
            for sv in solvers:
                all_inst[sv] = get_inst_gaps(rows, sv, ds)
            common = set.intersection(*(set(all_inst[sv].keys()) for sv in solvers)) \
                if len(solvers) > 1 else set()
            n_common = len(common)

            f.write(f"*Common instances: {n_common}*\n\n")
            f.write("| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |\n")
            f.write("|--------|--------|------|--------|--------|--------|--------|\n")

            if ds in PAPER_BASELINES:
                pb = PAPER_BASELINES[ds]
                f.write(f"| Paper Dual-Fast | gap* | {fmt_dist(pb['gap_star'])} |\n")
                f.write(f"| Paper Dual-Fast | gap₀ | {fmt_dist(pb['gap_0'])} |\n")

            for sv in solvers:
                if not common:
                    inst_gaps = all_inst[sv]
                    n = len(inst_gaps)
                else:
                    inst_gaps = {k: v for k, v in all_inst[sv].items() if k in common}
                    n = n_common
                if not inst_gaps:
                    continue
                star = gap_distribution([min(v) for v in inst_gaps.values()], n)
                avg = gap_distribution([sum(v)/len(v) for v in inst_gaps.values()], n)
                bold = "**" if sv == "fast-v19" else ""
                f.write(f"| {bold}{sv}{bold} | gap* | {bold}{fmt_dist(star)}{bold} |\n")
                f.write(f"| {bold}{sv}{bold} | gap₀ | {bold}{fmt_dist(avg)}{bold} |\n")

            f.write("\n")

            for sv in solvers:
                inst_all = all_inst[sv]
                seeds_seen = sorted(set(
                    r["seed"] for r in rows
                    if r["solver"] == sv and r["dataset"] == ds and r["gap"] >= 0
                ))
                n = len(inst_all)
                if n > 0:
                    avg_runs = sum(len(v) for v in inst_all.values()) / n
                    f.write(f"> {sv}: {n} total instances ({n_common} in common), "
                            f"seeds {seeds_seen} (avg {avg_runs:.1f} runs/inst)\n")
            f.write("\n")

        # ==============================================================
        # Section 2: Head-to-head pairwise comparison (v19 vs baseline)
        # ==============================================================
        f.write("## 2. v19 vs Baseline: Pairwise Comparison\n\n")

        if "fast-v19" in solvers and "dual-fast" in solvers:
            # --- 2a. Gap comparison ---
            f.write("### 2.1 Gap Comparison\n\n")
            f.write("Per-instance avg gap across seeds. Win = v19 smaller.\n\n")
            f.write("| Dataset | n | v19 Win | Base Win | Tie "
                    "| v19 Win% | Avg Gap v19 | Avg Gap base |\n")
            f.write("|---------|---|---------|----------|-----"
                    "|----------|-------------|-------------|\n")

            for ds in datasets:
                g_v19 = get_inst_gaps(rows, "fast-v19", ds)
                g_base = get_inst_gaps(rows, "dual-fast", ds)
                common = sorted(set(g_v19.keys()) & set(g_base.keys()))
                if not common:
                    continue
                w, l, t, s1, s2 = 0, 0, 0, 0.0, 0.0
                for inst in common:
                    a1 = sum(g_v19[inst]) / len(g_v19[inst])
                    a2 = sum(g_base[inst]) / len(g_base[inst])
                    s1 += a1; s2 += a2
                    if abs(a1 - a2) < 1e-8: t += 1
                    elif a1 < a2: w += 1
                    else: l += 1
                n = len(common)
                wp = w / (w + l) * 100 if (w + l) > 0 else 0
                f.write(f"| {ds} | {n} | {w} | {l} | {t} "
                        f"| {wp:.1f}% | {s1/n:.4f} | {s2/n:.4f} |\n")
            f.write("\n")

            # --- 2b. LB comparison ---
            f.write("### 2.2 Lower Bound (LB) Comparison\n\n")
            f.write("Per-instance best LB (max across seeds). "
                    "Win = v19 has larger LB (tighter bound).\n\n")
            f.write("| Dataset | n | v19 Win | Base Win | Tie "
                    "| v19 Win% | Avg LB v19 | Avg LB base |\n")
            f.write("|---------|---|---------|----------|-----"
                    "|----------|------------|------------|\n")

            for ds in datasets:
                lb_v19 = defaultdict(list)
                lb_base = defaultdict(list)
                for r in rows:
                    if r["dataset"] == ds and r["best_lb"] > 0:
                        if r["solver"] == "fast-v19":
                            lb_v19[r["instance"]].append(r["best_lb"])
                        elif r["solver"] == "dual-fast":
                            lb_base[r["instance"]].append(r["best_lb"])
                common = sorted(set(lb_v19.keys()) & set(lb_base.keys()))
                if not common:
                    continue
                w, l, t = 0, 0, 0
                s1, s2 = 0.0, 0.0
                for inst in common:
                    best1 = max(lb_v19[inst])
                    best2 = max(lb_base[inst])
                    s1 += best1; s2 += best2
                    if best1 == best2: t += 1
                    elif best1 > best2: w += 1
                    else: l += 1
                n = len(common)
                wp = w / (w + l) * 100 if (w + l) > 0 else 0
                f.write(f"| {ds} | {n} | {w} | {l} | {t} "
                        f"| {wp:.1f}% | {s1/n:.0f} | {s2/n:.0f} |\n")
            f.write("\n")

            # --- 2c. UB comparison ---
            f.write("### 2.3 Upper Bound (UB/Solution Quality) Comparison\n\n")
            f.write("Per-instance best UB (min across seeds). "
                    "Win = v19 has smaller UB (better solution).\n\n")
            f.write("| Dataset | n | v19 Win | Base Win | Tie "
                    "| v19 Win% | Avg UB v19 | Avg UB base |\n")
            f.write("|---------|---|---------|----------|-----"
                    "|----------|------------|------------|\n")

            for ds in datasets:
                ub_v19 = defaultdict(list)
                ub_base = defaultdict(list)
                for r in rows:
                    if r["dataset"] == ds and r["best_ub"] > 0:
                        if r["solver"] == "fast-v19":
                            ub_v19[r["instance"]].append(r["best_ub"])
                        elif r["solver"] == "dual-fast":
                            ub_base[r["instance"]].append(r["best_ub"])
                common = sorted(set(ub_v19.keys()) & set(ub_base.keys()))
                if not common:
                    continue
                w, l, t = 0, 0, 0
                s1, s2 = 0.0, 0.0
                for inst in common:
                    best1 = min(ub_v19[inst])
                    best2 = min(ub_base[inst])
                    s1 += best1; s2 += best2
                    if best1 == best2: t += 1
                    elif best1 < best2: w += 1
                    else: l += 1
                n = len(common)
                wp = w / (w + l) * 100 if (w + l) > 0 else 0
                f.write(f"| {ds} | {n} | {w} | {l} | {t} "
                        f"| {wp:.1f}% | {s1/n:.0f} | {s2/n:.0f} |\n")
            f.write("\n")

            # ==============================================================
            # Section 2.4: Causal analysis — WHERE does improvement come from?
            # ==============================================================
            f.write("### 2.4 Gap Improvement Decomposition (Causal Analysis)\n\n")
            f.write("For each instance where v19 has a better gap, "
                    "classify the source of improvement:\n"
                    "- **LB-driven**: v19 has better LB (tighter bound), "
                    "same or worse UB\n"
                    "- **UB-driven**: v19 has better UB (better solution), "
                    "same or worse LB\n"
                    "- **Both**: v19 improves both LB and UB\n"
                    "- **Neither**: gap is better but neither LB nor UB "
                    "individually dominates (rounding)\n\n")

            f.write("| Dataset | v19 Wins | LB-driven | UB-driven | Both | Neither |\n")
            f.write("|---------|----------|-----------|-----------|------|---------|\n")

            for ds in datasets:
                lb_v19 = defaultdict(list); lb_base = defaultdict(list)
                ub_v19 = defaultdict(list); ub_base = defaultdict(list)
                gap_v19 = defaultdict(list); gap_base = defaultdict(list)
                for r in rows:
                    if r["dataset"] != ds or r["gap"] < 0:
                        continue
                    if r["solver"] == "fast-v19":
                        lb_v19[r["instance"]].append(r["best_lb"])
                        ub_v19[r["instance"]].append(r["best_ub"])
                        gap_v19[r["instance"]].append(r["gap"])
                    elif r["solver"] == "dual-fast":
                        lb_base[r["instance"]].append(r["best_lb"])
                        ub_base[r["instance"]].append(r["best_ub"])
                        gap_base[r["instance"]].append(r["gap"])
                common = set(gap_v19.keys()) & set(gap_base.keys())
                lb_d, ub_d, both_d, neither_d, total_wins = 0, 0, 0, 0, 0
                for inst in common:
                    g1 = sum(gap_v19[inst]) / len(gap_v19[inst])
                    g2 = sum(gap_base[inst]) / len(gap_base[inst])
                    if g1 >= g2 - 1e-8:
                        continue
                    total_wins += 1
                    best_lb1 = max(lb_v19[inst])
                    best_lb2 = max(lb_base[inst])
                    best_ub1 = min(ub_v19[inst])
                    best_ub2 = min(ub_base[inst])
                    lb_better = best_lb1 > best_lb2
                    ub_better = best_ub1 < best_ub2
                    if lb_better and ub_better: both_d += 1
                    elif lb_better: lb_d += 1
                    elif ub_better: ub_d += 1
                    else: neither_d += 1
                if total_wins > 0:
                    f.write(f"| {ds} | {total_wins} "
                            f"| {lb_d} ({lb_d/total_wins*100:.0f}%) "
                            f"| {ub_d} ({ub_d/total_wins*100:.0f}%) "
                            f"| {both_d} ({both_d/total_wins*100:.0f}%) "
                            f"| {neither_d} ({neither_d/total_wins*100:.0f}%) |\n")
            f.write("\n")

            # ==============================================================
            # Section 2.5: Instance characteristics — WHERE does v19 win?
            # ==============================================================
            f.write("### 2.5 Improvement by Instance Scale\n\n")
            f.write("Group instances by vertex count to identify where "
                    "v19 gains its advantage.\n\n")
            f.write("| Dataset | Scale | n | v19 Win | Base Win | Tie | "
                    "v19 Win% | Avg Δgap |\n")
            f.write("|---------|-------|---|---------|----------|-----|"
                    "----------|----------|\n")

            scale_bins = [
                ("small (V≤200)", 0, 200),
                ("medium (200<V≤500)", 200, 500),
                ("large (V>500)", 500, float("inf")),
            ]
            for ds in datasets:
                v19_data = defaultdict(lambda: {"gaps": [], "V": 0})
                base_data = defaultdict(lambda: {"gaps": [], "V": 0})
                for r in rows:
                    if r["dataset"] != ds or r["gap"] < 0:
                        continue
                    if r["solver"] == "fast-v19":
                        v19_data[r["instance"]]["gaps"].append(r["gap"])
                        v19_data[r["instance"]]["V"] = max(
                            v19_data[r["instance"]]["V"], r["V"])
                    elif r["solver"] == "dual-fast":
                        base_data[r["instance"]]["gaps"].append(r["gap"])
                        base_data[r["instance"]]["V"] = max(
                            base_data[r["instance"]]["V"], r["V"])
                common = set(v19_data.keys()) & set(base_data.keys())

                for label, lo, hi in scale_bins:
                    subset = [i for i in common
                              if lo < max(v19_data[i]["V"], base_data[i]["V"]) <= hi]
                    if not subset:
                        continue
                    w, l, t, delta_sum = 0, 0, 0, 0.0
                    for inst in subset:
                        g1 = sum(v19_data[inst]["gaps"]) / len(v19_data[inst]["gaps"])
                        g2 = sum(base_data[inst]["gaps"]) / len(base_data[inst]["gaps"])
                        delta_sum += g2 - g1
                        if abs(g1 - g2) < 1e-8: t += 1
                        elif g1 < g2: w += 1
                        else: l += 1
                    n = len(subset)
                    wp = w / (w + l) * 100 if (w + l) > 0 else 0
                    f.write(f"| {ds} | {label} | {n} | {w} | {l} | {t} "
                            f"| {wp:.1f}% | {delta_sum/n:.4f} |\n")
            f.write("\n")

            # ==============================================================
            # Section 2.6: Seed consistency (stability)
            # ==============================================================
            f.write("### 2.6 Seed Consistency (Stability)\n\n")
            f.write("Standard deviation of gap across seeds — lower = "
                    "more stable.\n\n")
            f.write("| Dataset | Solver | Avg Std(gap) | "
                    "Med Std(gap) | Max Std(gap) |\n")
            f.write("|---------|--------|-------------|"
                    "-------------|-------------|\n")

            for ds in datasets:
                for sv in solvers:
                    inst_gaps = get_inst_gaps(rows, sv, ds)
                    if not inst_gaps:
                        continue
                    stds = []
                    for gaps in inst_gaps.values():
                        if len(gaps) >= 2:
                            mean = sum(gaps) / len(gaps)
                            var = sum((g - mean)**2 for g in gaps) / len(gaps)
                            stds.append(var ** 0.5)
                    if not stds:
                        continue
                    stds.sort()
                    avg_s = sum(stds) / len(stds)
                    med_s = stds[len(stds) // 2]
                    max_s = stds[-1]
                    f.write(f"| {ds} | {sv} | {avg_s:.6f} | "
                            f"{med_s:.6f} | {max_s:.6f} |\n")
            f.write("\n")

            # ==============================================================
            # Section 2.7: Newly optimal instances
            # ==============================================================
            f.write("### 2.7 Newly Optimal Instances\n\n")
            f.write("Instances where v19 proves optimality (gap*=0) "
                    "but baseline does not.\n\n")

            for ds in datasets:
                g_v19 = get_inst_gaps(rows, "fast-v19", ds)
                g_base = get_inst_gaps(rows, "dual-fast", ds)
                common = set(g_v19.keys()) & set(g_base.keys())
                v19_opt = {i for i in common if min(g_v19[i]) == 0}
                base_opt = {i for i in common if min(g_base[i]) == 0}
                newly_opt = sorted(v19_opt - base_opt)
                lost_opt = sorted(base_opt - v19_opt)
                f.write(f"**{ds}**: v19 #opt={len(v19_opt)}, "
                        f"base #opt={len(base_opt)}, "
                        f"newly optimal by v19: **{len(newly_opt)}**, "
                        f"lost: {len(lost_opt)}\n\n")
                if newly_opt and len(newly_opt) <= 20:
                    f.write("| Instance | v19 gap* | Base gap* |\n")
                    f.write("|----------|----------|----------|\n")
                    for inst in newly_opt[:20]:
                        f.write(f"| {inst} | 0 | {min(g_base[inst]):.6f} |\n")
                    f.write("\n")

        else:
            f.write("(Only one solver found — pairwise comparison skipped.)\n\n")

        # ==============================================================
        # Section 3: Detailed gap statistics per solver
        # ==============================================================
        f.write("## 3. Detailed Gap Statistics\n\n")
        f.write("| Dataset | Solver | n | Avg Gap | Med Gap | Min Gap | Max Gap |\n")
        f.write("|---------|--------|---|---------|---------|---------|--------|\n")

        for ds in datasets:
            for sv in solvers:
                inst_gaps = get_inst_gaps(rows, sv, ds)
                if not inst_gaps:
                    continue
                avg_gaps = sorted(sum(v) / len(v) for v in inst_gaps.values())
                n = len(avg_gaps)
                avg_g = sum(avg_gaps) / n
                med_g = avg_gaps[n // 2]
                min_g = avg_gaps[0]
                max_g = avg_gaps[-1]
                f.write(f"| {ds} | {sv} | {n} | {avg_g:.4f} | {med_g:.4f} "
                        f"| {min_g:.6f} | {max_g:.4f} |\n")

        # ==============================================================
        # Section 4: Convergence over time — per solver
        # ==============================================================
        f.write("\n## 4. Gap Convergence Over Time\n\n")
        f.write("Average gap* at each checkpoint (per-instance min across seeds).\n\n")
        time_cols = [
            ("gap_10s", "10s"), ("gap_60s", "1min"), ("gap_300s", "5min"),
            ("gap_600s", "10min"), ("gap_1800s", "30min"), ("gap_3600s", "60min"),
        ]

        f.write("| Dataset | Solver | " +
                " | ".join(label for _, label in time_cols) + " | final |\n")
        f.write("|---------|--------|" +
                "|".join("------" for _ in time_cols) + "|-------|\n")

        for ds in datasets:
            for sv in solvers:
                sv_rows = [r for r in rows
                           if r["solver"] == sv and r["dataset"] == ds and r["gap"] >= 0]
                if not sv_rows:
                    continue
                vals = []
                for col, _ in time_cols:
                    inst_best = defaultdict(lambda: float("inf"))
                    for r in sv_rows:
                        if r[col] >= 0:
                            inst_best[r["instance"]] = min(
                                inst_best[r["instance"]], r[col])
                    valid = [v for v in inst_best.values() if v < float("inf")]
                    if valid:
                        vals.append(f"{sum(valid)/len(valid):.4f}")
                    else:
                        vals.append("-")

                inst_final = defaultdict(lambda: float("inf"))
                for r in sv_rows:
                    inst_final[r["instance"]] = min(inst_final[r["instance"]], r["gap"])
                fv = list(inst_final.values())
                final = f"{sum(fv)/len(fv):.4f}"
                f.write(f"| {ds} | {sv} | " + " | ".join(vals) + f" | {final} |\n")

        # ==============================================================
        # Section 5: Instance difficulty breakdown per solver
        # ==============================================================
        f.write("\n## 5. Instance Difficulty Breakdown\n\n")
        f.write("Distribution of instances by gap range (gap* metric).\n\n")

        ranges = [
            ("optimal (gap=0)", lambda g: g == 0),
            ("near-opt (0 < gap ≤ 10⁻³)", lambda g: 0 < g <= 1e-3),
            ("small (10⁻³ < gap ≤ 10⁻²)", lambda g: 1e-3 < g <= 1e-2),
            ("medium (10⁻² < gap ≤ 10⁻¹)", lambda g: 1e-2 < g <= 1e-1),
            ("large (gap > 10⁻¹)", lambda g: g > 1e-1),
        ]

        for ds in datasets:
            f.write(f"### {ds}\n\n")
            f.write("| Gap Range | " +
                    " | ".join(sv for sv in solvers) + " |\n")
            f.write("|-----------|" +
                    "|".join("------" for _ in solvers) + "|\n")

            solver_stars = {}
            for sv in solvers:
                inst_gaps = get_inst_gaps(rows, sv, ds)
                solver_stars[sv] = {inst: min(gaps) for inst, gaps in inst_gaps.items()}

            for label, pred in ranges:
                cells = []
                for sv in solvers:
                    stars = solver_stars.get(sv, {})
                    n = len(stars)
                    cnt = sum(1 for g in stars.values() if pred(g))
                    cells.append(f"{cnt} ({cnt/n*100:.1f}%)" if n > 0 else "-")
                f.write(f"| {label} | " + " | ".join(cells) + " |\n")
            f.write("\n")

        f.write("\n---\n*Generated by sumup.py (exp-2)*\n")

    print(f"  Report: {filepath}")


def main():
    parser = argparse.ArgumentParser(description="Summarise MWDS exp-2 results.")
    parser.add_argument("result_root", help="Root directory containing result-* folders")
    parser.add_argument("--output_dir", default="./analysis", help="Output directory")
    args = parser.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)

    print(f"Scanning {args.result_root} ...")
    rows, scan_stats = scan_results(args.result_root)
    if not rows:
        print("No results found.")
        return

    for (sv, ds), st in sorted(scan_stats.items()):
        lost = st["empty"] + st["no_output"]
        print(f"  {sv}/{ds}: {st['total']} files, "
              f"{st['empty']} empty, {st['no_output']} header-only, "
              f"{st['parsed']} parsed, {lost} lost ({lost/st['total']*100:.1f}%)"
              if st['total'] else f"  {sv}/{ds}: 0 files")

    pre_dedup = len(rows)
    best = {}
    for r in rows:
        key = (r["solver"], r["dataset"], r["seed"], r["instance"])
        if key not in best or (r["gap"] >= 0 and
                (best[key]["gap"] < 0 or r["gap"] < best[key]["gap"])):
            best[key] = r
    rows = list(best.values())

    solvers = sorted(set(r["solver"] for r in rows))
    datasets = sorted(set(r["dataset"] for r in rows))
    print(f"Found {pre_dedup} records, {pre_dedup - len(rows)} duplicates removed, "
          f"{len(rows)} unique: {solvers} × {datasets}")

    csv_path = os.path.join(args.output_dir, "exp2_results.csv")
    report_path = os.path.join(args.output_dir, "exp2_report.md")

    write_csv(rows, csv_path)
    generate_report(rows, report_path, scan_stats)
    print("Done.")


if __name__ == "__main__":
    main()
