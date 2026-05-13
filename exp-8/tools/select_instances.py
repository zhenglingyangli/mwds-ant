#!/usr/bin/env python3
"""Select 5 representative instances per dataset from baseline_index.csv."""

import csv
import re
from collections import defaultdict
from pathlib import Path

EXP8_ROOT = Path(__file__).resolve().parents[1]
DATASETS = ['T1', 'T2', 'UDG', 'BHOSLIB', 'DIMACS', 'DIMACS10', 'NDR', 'SNAP']


def as_float(x, default=None):
    try:
        return float(x) if x not in ('', None) else default
    except ValueError:
        return default


def name_score(name):
    nums = [int(x) for x in re.findall(r'\d+', name)]
    if not nums:
        return 0
    # emphasize graph size-like numbers first, but keep deterministic ordering
    return nums[0] * 10**9 + sum(nums[1:])


def choose_quantiles(items, k=5):
    if len(items) <= k:
        return items
    idxs = []
    for i in range(k):
        idx = round(i * (len(items) - 1) / (k - 1))
        while idx in idxs and idx + 1 < len(items):
            idx += 1
        while idx in idxs and idx - 1 >= 0:
            idx -= 1
        idxs.append(idx)
    return [items[i] for i in sorted(idxs)]


def main():
    index_path = EXP8_ROOT / 'baseline_index.csv'
    rows = list(csv.DictReader(index_path.open()))
    by_ds_inst = defaultdict(dict)
    for r in rows:
        by_ds_inst[(r['dataset'], r['instance'])][r['family']] = r

    summary = []
    out_dir = EXP8_ROOT / 'selected_instances'
    out_dir.mkdir(exist_ok=True)

    for ds in DATASETS:
        candidates = []
        for (dataset, inst), fams in by_ds_inst.items():
            if dataset != ds or 'deep' not in fams or 'fast' not in fams:
                continue
            deep = fams['deep']; fast = fams['fast']
            gap_vals = [as_float(deep.get('final_gap_mean')), as_float(fast.get('final_gap_mean'))]
            gap_vals = [x for x in gap_vals if x is not None]
            V_vals = [as_float(deep.get('V')), as_float(fast.get('V'))]
            V_vals = [x for x in V_vals if x is not None]
            E_vals = [as_float(deep.get('E')), as_float(fast.get('E'))]
            E_vals = [x for x in E_vals if x is not None]
            hist_vals = [as_float(deep.get('historical_value_mean')), as_float(fast.get('historical_value_mean'))]
            hist_vals = [x for x in hist_vals if x is not None]
            if gap_vals:
                score = (0, sum(gap_vals) / len(gap_vals), name_score(inst))
            elif V_vals or E_vals:
                score = (1, max(V_vals or [0]), max(E_vals or [0]), name_score(inst))
            elif hist_vals:
                score = (2, sum(hist_vals) / len(hist_vals), name_score(inst))
            else:
                score = (3, name_score(inst))
            candidates.append((score, inst, deep, fast))
        candidates.sort(key=lambda x: x[0])
        chosen = choose_quantiles(candidates, 5)
        with (out_dir / f'{ds}.txt').open('w') as f:
            for _score, inst, _deep, _fast in chosen:
                f.write(inst + '\n')
        for rank, (score, inst, deep, fast) in enumerate(chosen, 1):
            summary.append({
                'dataset': ds, 'rank': rank, 'instance': inst,
                'deep_repeats': deep.get('repeats', ''), 'fast_repeats': fast.get('repeats', ''),
                'deep_has_lb': deep.get('has_lb_summary', ''), 'fast_has_lb': fast.get('has_lb_summary', ''),
                'deep_value_mean': deep.get('historical_value_mean', ''),
                'fast_value_mean': fast.get('historical_value_mean', ''),
                'score': score,
            })
        print(f'{ds}: {len(chosen)} selected from {len(candidates)} common baseline instances')

    with (EXP8_ROOT / 'selected_instances_summary.csv').open('w', newline='') as f:
        fieldnames = ['dataset', 'rank', 'instance', 'deep_repeats', 'fast_repeats', 'deep_has_lb', 'fast_has_lb', 'deep_value_mean', 'fast_value_mean', 'score']
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(summary)


if __name__ == '__main__':
    main()
