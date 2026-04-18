#!/usr/bin/env python3
"""
Compare Dual-Deep baseline, v6, and v10 using exp-1 and exp-3 results.
Match by (instance, seed) for fair comparison.
"""

import csv
from collections import defaultdict

EXP1_CSV = "../../exp-1/sumup/analysis/exp1_results.csv"
EXP3_CSV = "./analysis/exp1_results.csv"


def load_results(csv_path, solver_prefix_map):
    """Load results into {solver: {(instance, seed): row}}"""
    data = defaultdict(dict)
    with open(csv_path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            raw_solver = row["solver"]
            for prefix, name in solver_prefix_map.items():
                if raw_solver == prefix:
                    key = (row["instance"], int(row["seed"]))
                    data[name][key] = row
    return data


def main():
    exp1_data = load_results(EXP1_CSV, {
        "deep-T1": "deep", "deep-T2": "deep",
        "v6-T1": "v6", "v6-T2": "v6",
    })
    exp3_data = load_results(EXP3_CSV, {
        "v10-T1": "v10", "v10-T2": "v10",
    })

    deep = exp1_data["deep"]
    v6 = exp1_data["v6"]
    v10 = exp3_data["v10"]

    print(f"Loaded: deep={len(deep)}, v6={len(v6)}, v10={len(v10)} (instance,seed) pairs\n")

    # === Three-way comparison: deep vs v6 vs v10 ===
    common_all = set(deep.keys()) & set(v6.keys()) & set(v10.keys())
    print(f"=== Three-way overlap (deep ∩ v6 ∩ v10): {len(common_all)} (instance,seed) pairs ===\n")

    if not common_all:
        print("No three-way overlap found.\n")
    else:
        run_comparison_three(deep, v6, v10, common_all)

    # === v6 vs v10 (pairwise) ===
    common_v6_v10 = set(v6.keys()) & set(v10.keys())
    print(f"\n=== v6 vs v10 overlap: {len(common_v6_v10)} (instance,seed) pairs ===\n")
    if common_v6_v10:
        run_comparison_pair(v6, v10, "v6", "v10", common_v6_v10)

    # === deep vs v10 (pairwise) ===
    common_deep_v10 = set(deep.keys()) & set(v10.keys())
    print(f"\n=== deep vs v10 overlap: {len(common_deep_v10)} (instance,seed) pairs ===\n")
    if common_deep_v10:
        run_comparison_pair(deep, v10, "deep", "v10", common_deep_v10)


def run_comparison_pair(data_a, data_b, name_a, name_b, common_keys):
    a_wins_ub, b_wins_ub, ties_ub = 0, 0, 0
    a_wins_gap, b_wins_gap, ties_gap = 0, 0, 0
    a_gap_sum, b_gap_sum = 0.0, 0.0
    a_ub_sum, b_ub_sum = 0, 0

    details = []
    skipped = 0

    for key in sorted(common_keys):
        inst, seed = key
        ra, rb = data_a[key], data_b[key]

        ub_a = int(ra["best_ub"])
        ub_b = int(rb["best_ub"])

        if ub_a <= 0 or ub_b <= 0:
            skipped += 1
            continue
        gap_a = float(ra["gap"])
        gap_b = float(rb["gap"])

        a_ub_sum += ub_a
        b_ub_sum += ub_b
        a_gap_sum += gap_a
        b_gap_sum += gap_b

        if ub_a < ub_b:
            a_wins_ub += 1
            winner = f"{name_a}+"
        elif ub_a > ub_b:
            b_wins_ub += 1
            winner = f"{name_b}+"
        else:
            ties_ub += 1
            winner = "tie"

        if gap_a < gap_b:
            a_wins_gap += 1
        elif gap_a > gap_b:
            b_wins_gap += 1
        else:
            ties_gap += 1

        diff_pct = (ub_a - ub_b) / ub_a * 100 if ub_a > 0 else 0
        details.append((inst, seed, ub_a, ub_b, diff_pct, gap_a, gap_b, winner))

    n = a_wins_ub + b_wins_ub + ties_ub
    if skipped:
        print(f"  (Skipped {skipped} pairs with UB=0)")
    if n == 0:
        print("  No valid pairs to compare.")
        return
    print(f"  UB comparison:  {name_a} wins {a_wins_ub}, {name_b} wins {b_wins_ub}, ties {ties_ub}")
    print(f"  Gap comparison: {name_a} wins {a_wins_gap}, {name_b} wins {b_wins_gap}, ties {ties_gap}")
    print(f"  Avg UB:  {name_a}={a_ub_sum/n:.1f}  {name_b}={b_ub_sum/n:.1f}  (diff={((a_ub_sum-b_ub_sum)/a_ub_sum*100):.2f}%)")
    print(f"  Avg Gap: {name_a}={a_gap_sum/n:.4f}  {name_b}={b_gap_sum/n:.4f}")

    # By graph size
    size_buckets = defaultdict(lambda: [0, 0, 0])  # [a_win, b_win, tie]
    for inst, seed, ub_a, ub_b, diff, gap_a, gap_b, winner in details:
        parts = inst.replace(".wclq", "").split("_")
        if parts[0] in ("T1", "T2"):
            v_count = parts[1]
            bucket = f"{parts[0]}_{v_count}"
        else:
            bucket = parts[0]

        if ub_a < ub_b:
            size_buckets[bucket][0] += 1
        elif ub_a > ub_b:
            size_buckets[bucket][1] += 1
        else:
            size_buckets[bucket][2] += 1

    print(f"\n  By graph size (UB: {name_a}_win / {name_b}_win / tie):")
    for bucket in sorted(size_buckets.keys()):
        aw, bw, t = size_buckets[bucket]
        total = aw + bw + t
        print(f"    {bucket:20s}: {aw:3d} / {bw:3d} / {t:3d}  (n={total})")

    # Top improvements for name_b
    improvements = [(inst, seed, ub_a, ub_b, diff, gap_a, gap_b)
                    for inst, seed, ub_a, ub_b, diff, gap_a, gap_b, _ in details
                    if ub_b < ub_a]
    if improvements:
        improvements.sort(key=lambda x: -x[4])
        print(f"\n  Top 10 instances where {name_b} improves over {name_a}:")
        print(f"    {'Instance':40s} {'Seed':>4s} {name_a+'_UB':>10s} {name_b+'_UB':>10s} {'Diff%':>7s}")
        for inst, seed, ub_a, ub_b, diff, gap_a, gap_b in improvements[:10]:
            print(f"    {inst:40s} {seed:4d} {ub_a:10d} {ub_b:10d} {diff:+6.2f}%")

    # Top regressions for name_b
    regressions = [(inst, seed, ub_a, ub_b, diff, gap_a, gap_b)
                   for inst, seed, ub_a, ub_b, diff, gap_a, gap_b, _ in details
                   if ub_b > ub_a]
    if regressions:
        regressions.sort(key=lambda x: x[4])
        print(f"\n  Top 10 instances where {name_b} regresses vs {name_a}:")
        print(f"    {'Instance':40s} {'Seed':>4s} {name_a+'_UB':>10s} {name_b+'_UB':>10s} {'Diff%':>7s}")
        for inst, seed, ub_a, ub_b, diff, gap_a, gap_b in regressions[:10]:
            print(f"    {inst:40s} {seed:4d} {ub_a:10d} {ub_b:10d} {diff:+6.2f}%")


def run_comparison_three(deep, v6, v10, common_keys):
    best_counts = {"deep": 0, "v6": 0, "v10": 0, "tie": 0}
    gap_sums = {"deep": 0.0, "v6": 0.0, "v10": 0.0}
    ub_sums = {"deep": 0, "v6": 0, "v10": 0}

    skipped = 0
    for key in sorted(common_keys):
        rd, r6, r10 = deep[key], v6[key], v10[key]
        ub_d = int(rd["best_ub"])
        ub_6 = int(r6["best_ub"])
        ub_10 = int(r10["best_ub"])
        if ub_d <= 0 or ub_6 <= 0 or ub_10 <= 0:
            skipped += 1
            continue
        gap_sums["deep"] += float(rd["gap"])
        gap_sums["v6"] += float(r6["gap"])
        gap_sums["v10"] += float(r10["gap"])
        ub_sums["deep"] += ub_d
        ub_sums["v6"] += ub_6
        ub_sums["v10"] += ub_10

        best_ub = min(ub_d, ub_6, ub_10)
        winners = []
        if ub_d == best_ub: winners.append("deep")
        if ub_6 == best_ub: winners.append("v6")
        if ub_10 == best_ub: winners.append("v10")

        if len(winners) == 3:
            best_counts["tie"] += 1
        elif len(winners) == 1:
            best_counts[winners[0]] += 1
        else:
            for w in winners:
                best_counts[w] += 0.5

    n = sum(v for v in best_counts.values() if isinstance(v, (int, float)))
    n = int(best_counts["deep"] + best_counts["v6"] + best_counts["v10"] + best_counts["tie"])
    if skipped:
        print(f"  (Skipped {skipped} pairs with UB=0)")
    print(f"  Valid pairs: {n}")
    print(f"  Best UB count (sole or shared winner):")
    print(f"    deep: {best_counts['deep']:.0f}")
    print(f"    v6:   {best_counts['v6']:.0f}")
    print(f"    v10:  {best_counts['v10']:.0f}")
    print(f"    tie (all equal): {best_counts['tie']:.0f}")
    print()
    print(f"  Avg UB:  deep={ub_sums['deep']/n:.1f}  v6={ub_sums['v6']/n:.1f}  v10={ub_sums['v10']/n:.1f}")
    print(f"  Avg Gap: deep={gap_sums['deep']/n:.4f}  v6={gap_sums['v6']/n:.4f}  v10={gap_sums['v10']/n:.4f}")


if __name__ == "__main__":
    main()
