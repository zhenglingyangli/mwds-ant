#!/usr/bin/env python3
"""
Summarise MWDS exp-6 selection results: 9 solvers × T1 half × 2 seeds.

Produces:
  1. CSV with one row per (solver, seed, instance)
  2. Markdown report:
     - Per-solver stats (avg gap, #opt, gap<=0.01, gap<=0.1)
     - Fast-family pairwise matrix (6x6) + ranking
     - Deep-family pairwise matrix (3x3) + ranking
     - Selection recommendation: winner per family
     - Reality check: does the winner really beat the baseline?

Usage:
    python3 sumup.py ../jobs/result --output_dir ./analysis
"""

import argparse
import csv
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

# ============================================================
# Solver families -- must match generate_scripts.py
# ============================================================

FAST_SOLVERS = [
    "dual-fast", "fast-v19", "fast-v28",
    "fast-freqscore", "fast-poolrelink", "fast-pool",
]
DEEP_SOLVERS = ["dual-deep", "deep-v6", "deep-v10"]

FAST_BASELINE = "dual-fast"
DEEP_BASELINE = "dual-deep"

ALL_SOLVERS = FAST_SOLVERS + DEEP_SOLVERS

# ============================================================
# Regex (same as exp-1 / exp-2)
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
    """Return summary dict (recovers LB/UB from intermediate rounds on TIMEOUT)."""
    text = Path(filepath).read_text(errors="replace")
    lines = text.splitlines()

    summary = None
    for line in reversed(lines):
        m = RE_SUMMARY.search(line)
        if m:
            return {
                "instance": m.group(1), "V": int(m.group(2)), "E": int(m.group(3)),
                "best_lb": int(m.group(6)), "best_ub": int(m.group(8)),
                "status": "OK",
            }
        m = RE_OPTIMAL.search(line)
        if m:
            return {
                "instance": m.group(1), "V": int(m.group(2)), "E": int(m.group(3)),
                "best_lb": int(m.group(6)), "best_ub": int(m.group(7)),
                "status": "OPT",
            }
        m = RE_TIMEOUT.search(line)
        if m:
            summary = {
                "instance": m.group(1), "V": 0, "E": 0,
                "best_lb": 0, "best_ub": 0, "status": m.group(2),
            }
            break

    # TIMEOUT/MEMOUT: recover best_lb/best_ub from round data
    best_lb, best_ub = 0, 10**12
    saw_round = False
    inst_name = summary["instance"] if summary else None
    for line in lines:
        m = RE_ROUND_FULL.match(line) or RE_ROUND_SHORT.match(line)
        if m:
            saw_round = True
            lb_best = int(m.group(3))
            best_lb = max(best_lb, lb_best)
            if m.re is RE_ROUND_FULL:
                ub_best = int(m.group(7))
                if ub_best > 0:
                    best_ub = min(best_ub, ub_best)

    if saw_round:
        if summary is None:
            # no TIMEOUT sentinel but we have rounds -> treat as partial
            summary = {
                "instance": inst_name or Path(filepath).stem.replace(".out", ""),
                "V": 0, "E": 0, "best_lb": 0, "best_ub": 0, "status": "PARTIAL",
            }
        summary["best_lb"] = best_lb
        summary["best_ub"] = best_ub if best_ub < 10**12 else 0

    return summary


# ============================================================
# Directory name parsing
# ============================================================
# exp-6 result dirs:
#   result-<binary>-T1_wclq-<tag>-<timestamp>
# where tag = <solver_name>-T1-c<chunk>-s<seed>

RE_DIRNAME = re.compile(
    r"result-[^-]+(?:-[^-]+)*-T1_wclq-(?P<solver>.+?)-T1-c\d+-s(?P<seed>\d+)-\d{14}$"
)


def extract_solver_seed(dirname):
    m = RE_DIRNAME.match(dirname)
    if m:
        return m.group("solver"), int(m.group("seed"))
    # Fallback: try to find any `-s<N>-<timestamp>` suffix
    m = re.search(r"-s(\d+)-\d{14}$", dirname)
    if not m:
        return None, None
    seed = int(m.group(1))
    # Find which known solver name the dir contains (longest-first to avoid
    # 'dual-fast' matching inside 'dual-fast-v19').
    for sv in sorted(ALL_SOLVERS, key=len, reverse=True):
        if f"-{sv}-" in dirname:
            return sv, seed
    return None, seed


def scan_results(result_root):
    rows = []
    root = Path(result_root)
    if not root.is_dir():
        print(f"ERROR: {result_root} is not a directory", file=sys.stderr)
        return rows

    for entry in sorted(root.iterdir()):
        if not entry.is_dir() or not entry.name.startswith("result-"):
            continue
        solver, seed = extract_solver_seed(entry.name)
        if solver is None or solver not in ALL_SOLVERS:
            print(f"  SKIP (unrecognised solver in dir name): {entry.name}", file=sys.stderr)
            continue

        for out_file in sorted(entry.glob("*.out")):
            summary = parse_out_file(out_file)
            if summary is None:
                continue
            gap = compute_gap(summary["best_ub"], summary["best_lb"])
            rows.append({
                "solver": solver,
                "seed": seed,
                "instance": summary["instance"],
                "V": summary["V"],
                "E": summary["E"],
                "best_lb": summary["best_lb"],
                "best_ub": summary["best_ub"],
                "gap": round(gap, 6),
                "status": summary["status"],
            })

    return rows


# ============================================================
# Analysis
# ============================================================

def per_instance_avg_gap(rows, solver):
    """Map instance -> avg gap across seeds (only valid gaps)."""
    inst_gaps = defaultdict(list)
    for r in rows:
        if r["solver"] != solver or r["gap"] < 0:
            continue
        inst_gaps[r["instance"]].append(r["gap"])
    return {k: sum(v) / len(v) for k, v in inst_gaps.items()}


def solver_stats(rows, solver):
    gaps = list(per_instance_avg_gap(rows, solver).values())
    if not gaps:
        return None
    gaps.sort()
    n = len(gaps)
    return {
        "n": n,
        "avg": sum(gaps) / n,
        "med": gaps[n // 2],
        "opt": sum(1 for g in gaps if g == 0),
        "le_01": sum(1 for g in gaps if g <= 0.01),
        "le_1":  sum(1 for g in gaps if g <= 0.1),
    }


def pairwise(rows, s1, s2):
    g1 = per_instance_avg_gap(rows, s1)
    g2 = per_instance_avg_gap(rows, s2)
    common = set(g1) & set(g2)
    w = l = t = 0
    for inst in common:
        d = g1[inst] - g2[inst]
        if abs(d) < 1e-6:
            t += 1
        elif d < 0:
            w += 1
        else:
            l += 1
    return w, l, t, len(common)


def rank_family(rows, family_solvers):
    """Return solvers sorted by avg gap (ascending = better)."""
    scored = []
    for sv in family_solvers:
        st = solver_stats(rows, sv)
        if st:
            scored.append((sv, st["avg"]))
    scored.sort(key=lambda x: x[1])
    return [sv for sv, _ in scored]


def net_score_vs_baseline(rows, solver, baseline):
    """Net wins (wins - losses) vs baseline. Positive = solver beats baseline."""
    w, l, _, n = pairwise(rows, solver, baseline)
    return w - l, w, l, n


# ============================================================
# Report
# ============================================================

def generate_report(rows, filepath):
    solvers_present = sorted(set(r["solver"] for r in rows))
    n_inst = len(set(r["instance"] for r in rows))
    n_seed = len(set(r["seed"] for r in rows))

    with open(filepath, "w") as f:
        f.write("# exp-6: alpha=90 Selection Report\n\n")
        f.write(f"- Solvers present: {len(solvers_present)} / 9 expected\n")
        f.write(f"- Distinct instances: {n_inst}\n")
        f.write(f"- Distinct seeds: {n_seed}\n")
        f.write(f"- Total records: {len(rows)}\n\n")

        if sorted(solvers_present) != sorted(ALL_SOLVERS):
            missing = set(ALL_SOLVERS) - set(solvers_present)
            extra = set(solvers_present) - set(ALL_SOLVERS)
            f.write("**WARNING**: solver set mismatch.\n")
            if missing:
                f.write(f"  Missing: {sorted(missing)}\n")
            if extra:
                f.write(f"  Extra  : {sorted(extra)}\n")
            f.write("\n")

        # ------------------------------------------------------------
        f.write("## 1. Per-solver Stats (T1 subset, avg across seeds)\n\n")
        f.write("| Solver | Family | n | Avg Gap | Med Gap | #opt | gap<=0.01 | gap<=0.1 |\n")
        f.write("|---|---|---|---|---|---|---|---|\n")
        for sv in FAST_SOLVERS + DEEP_SOLVERS:
            st = solver_stats(rows, sv)
            fam = "fast" if sv in FAST_SOLVERS else "deep"
            if st is None:
                f.write(f"| {sv} | {fam} | - | - | - | - | - | - |\n")
                continue
            pct = lambda x: f"{x} ({x/st['n']*100:.1f}%)"
            f.write(f"| {sv} | {fam} | {st['n']} | {st['avg']:.4f} | "
                    f"{st['med']:.4f} | {pct(st['opt'])} | "
                    f"{pct(st['le_01'])} | {pct(st['le_1'])} |\n")

        # ------------------------------------------------------------
        f.write("\n## 2. Pairwise Comparison within Family\n\n")
        f.write("Each cell: wins / losses / ties (per-instance avg gap across seeds, common instances only).\n")
        f.write("Row beats column on the `wins` count.\n\n")

        for fam_name, fam_solvers in [("Fast", FAST_SOLVERS), ("Deep", DEEP_SOLVERS)]:
            present = [s for s in fam_solvers if s in solvers_present]
            if len(present) < 2:
                f.write(f"### {fam_name} family: <2 solvers present, skipping pairwise.\n\n")
                continue
            f.write(f"### {fam_name} Family ({len(present)} solvers)\n\n")
            f.write("| vs | " + " | ".join(present) + " |\n")
            f.write("|" + "---|" * (len(present) + 1) + "\n")
            for s1 in present:
                cells = []
                for s2 in present:
                    if s1 == s2:
                        cells.append("-")
                    else:
                        w, l, t, _ = pairwise(rows, s1, s2)
                        cells.append(f"{w}/{l}/{t}")
                f.write(f"| **{s1}** | " + " | ".join(cells) + " |\n")
            f.write("\n")

        # ------------------------------------------------------------
        f.write("## 3. Ranking per Family (by avg gap, ascending)\n\n")
        for fam_name, fam_solvers, baseline in [
            ("Fast", FAST_SOLVERS, FAST_BASELINE),
            ("Deep", DEEP_SOLVERS, DEEP_BASELINE),
        ]:
            ranked = rank_family(rows, fam_solvers)
            if not ranked:
                f.write(f"### {fam_name}: no data\n\n")
                continue
            f.write(f"### {fam_name}\n\n")
            f.write("| Rank | Solver | Avg Gap | Net vs baseline (wins-losses) |\n")
            f.write("|---|---|---|---|\n")
            for i, sv in enumerate(ranked, 1):
                st = solver_stats(rows, sv)
                if sv == baseline:
                    net_str = "(baseline)"
                else:
                    net, w, l, nc = net_score_vs_baseline(rows, sv, baseline)
                    sign = "+" if net >= 0 else ""
                    net_str = f"{sign}{net} ({w}W/{l}L, {nc} common)"
                f.write(f"| {i} | {sv} | {st['avg']:.4f} | {net_str} |\n")
            f.write("\n")

        # ------------------------------------------------------------
        f.write("## 4. Selection Recommendation\n\n")
        fast_rank = rank_family(rows, FAST_SOLVERS)
        deep_rank = rank_family(rows, DEEP_SOLVERS)

        fast_winner = next((s for s in fast_rank if s != FAST_BASELINE), None)
        deep_winner = next((s for s in deep_rank if s != DEEP_BASELINE), None)

        def verdict(winner, baseline, family_name):
            if not winner:
                return f"- **{family_name}**: no non-baseline solver has data.\n"
            net, w, l, nc = net_score_vs_baseline(rows, winner, baseline)
            st_w = solver_stats(rows, winner)
            st_b = solver_stats(rows, baseline)
            line = f"- **{family_name} winner (at alpha=90)**: `{winner}`\n"
            line += f"  - Avg gap: {st_w['avg']:.4f} vs baseline `{baseline}` {st_b['avg']:.4f}\n"
            line += f"  - Head-to-head: {w}W / {l}L / {nc-w-l}T on {nc} common instances (net {net:+d})\n"
            if net <= 2:
                line += f"  - **WARNING**: margin over baseline is <=2 net. Signal is weak, "
                line += f"consider more seeds before committing.\n"
            elif net < 0:
                line += f"  - **ALERT**: winner actually *loses* to baseline at alpha=90! "
                line += f"None of the modifications help here. Reconsider the approach.\n"
            return line

        f.write(verdict(fast_winner, FAST_BASELINE, "Fast"))
        f.write(verdict(deep_winner, DEEP_BASELINE, "Deep"))

        f.write("\n### Next steps by outcome\n\n")
        f.write("| Outcome | Action |\n|---|---|\n")
        f.write("| Fast winner = `fast-v19` | exp-5 SOLVERS unchanged, proceed with pilot |\n")
        f.write("| Fast winner != `fast-v19` | update exp-5/jobs/generate_scripts.py SOLVERS, regenerate pilot |\n")
        f.write("| Deep winner = `deep-v6`  | exp-4 SOLVERS unchanged, proceed with pilot |\n")
        f.write("| Deep winner != `deep-v6` | update exp-4/jobs/generate_scripts.py SOLVERS, regenerate pilot |\n")

        f.write("\n---\n*Generated by exp-6 sumup.py*\n")

    print(f"  Report: {filepath}")


def write_csv(rows, filepath):
    if not rows:
        return
    fields = list(rows[0].keys())
    with open(filepath, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"  CSV   : {filepath}  ({len(rows)} rows)")


def main():
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("result_root", help="Root directory containing result-* folders")
    p.add_argument("--output_dir", default="./analysis", help="Output directory")
    args = p.parse_args()

    os.makedirs(args.output_dir, exist_ok=True)
    print(f"Scanning {args.result_root} ...")
    rows = scan_results(args.result_root)
    if not rows:
        print("No results found.")
        return
    print(f"Found {len(rows)} records from {len(set(r['solver'] for r in rows))} solvers.")

    write_csv(rows, os.path.join(args.output_dir, "exp6_results.csv"))
    generate_report(rows, os.path.join(args.output_dir, "selection_report.md"))
    print("Done.")


if __name__ == "__main__":
    main()
