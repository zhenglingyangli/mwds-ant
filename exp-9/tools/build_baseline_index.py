#!/usr/bin/env python3
"""Build a historical baseline index from Technical Appendix-2814 raw-data.

Covers all four historical solvers per instance:
- deep family: dualdeep (paper baseline) + deepOpt / deep1H (paper improved DeepOPT)
- fast family: dualcc2v3 (paper baseline) + cc2v3 / cc2v31H (paper improved FastMWDS)

Three raw-data formats are supported:
1. SUMMARY  : ``<inst> |V| n |E| m  (#LB ... ---> ... [====|gap] <num> <--- <num> ... #UB) ...``
2. SIMPLE   : ``<inst> , <reported_value>``           (usually UB/solution value)
3. WSPACE6  : ``<inst> <run_id> <reported_a> <reported_value> <gap> <time>``

Output files (overwrites prior content):
- ``baseline_records.csv`` : every parsed row tagged with baseline_solver
- ``baseline_index.csv``   : aggregated per (dataset, family, baseline_solver, instance)
"""

import csv
import re
import statistics as stats
from collections import defaultdict
from pathlib import Path

EXP8_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = EXP8_ROOT.parent / 'Technical Appendix-2814' / 'Technical Appendix-2814' / 'experiments' / 'raw-data'

# (dataset, family, baseline_solver) -> raw csv path
FILES = {
    # T1 (synthetic dense weighted)
    ('T1', 'deep', 'dualdeep'): RAW_ROOT / 'T1/deepOpt/dualdeep-T1.csv',
    ('T1', 'deep', 'deepOpt'):  RAW_ROOT / 'T1/deepOpt/deepOpt-T1.csv',
    ('T1', 'fast', 'dualcc2v3'): RAW_ROOT / 'T1/cc2v3/dualcc2v3-T1.csv',
    ('T1', 'fast', 'cc2v3'):    RAW_ROOT / 'T1/cc2v3/cc2v3-T1.csv',
    # T2 (synthetic sparse weighted)
    ('T2', 'deep', 'dualdeep'): RAW_ROOT / 'T2/deepOpt/dualdeep-T2.csv',
    ('T2', 'deep', 'deepOpt'):  RAW_ROOT / 'T2/deepOpt/deepOpt-T2.csv',
    ('T2', 'fast', 'dualcc2v3'): RAW_ROOT / 'T2/cc2v3/dualcc2v3-T2.csv',
    ('T2', 'fast', 'cc2v3'):    RAW_ROOT / 'T2/cc2v3/cc2v31H_T2.csv',
    # UDG (unit-disk graphs)
    ('UDG', 'deep', 'dualdeep'): RAW_ROOT / 'UDG/deepOpt/dualdeep-UDG.csv',
    ('UDG', 'deep', 'deepOpt'):  RAW_ROOT / 'UDG/deepOpt/deepOpt-UDG.csv',
    ('UDG', 'fast', 'dualcc2v3'): RAW_ROOT / 'UDG/cc2v3/dualcc2v3-UDG.csv',
    ('UDG', 'fast', 'cc2v3'):    RAW_ROOT / 'UDG/cc2v3/cc2v3_UDG.csv',
    # BHOSLIB
    ('BHOSLIB', 'deep', 'dualdeep'): RAW_ROOT / 'BHOSLIB/deepOpt/dualdeep-BHOSLIB.csv',
    ('BHOSLIB', 'deep', 'deepOpt'):  RAW_ROOT / 'BHOSLIB/deepOpt/deepOpt-BHOSLIB.csv',
    ('BHOSLIB', 'fast', 'dualcc2v3'): RAW_ROOT / 'BHOSLIB/cc2v3/dualcc2v3-frb.csv',
    ('BHOSLIB', 'fast', 'cc2v3'):    RAW_ROOT / 'BHOSLIB/cc2v3/cc2v3-frb.csv',
    # DIMACS
    ('DIMACS', 'deep', 'dualdeep'): RAW_ROOT / 'DIMACS/deepOpt/dualdeep-dimacs.csv',
    ('DIMACS', 'deep', 'deepOpt'):  RAW_ROOT / 'DIMACS/deepOpt/deepOpt-dimacs.csv',
    ('DIMACS', 'fast', 'dualcc2v3'): RAW_ROOT / 'DIMACS/cc2v3/dualcc2v3-dimacs.csv',
    ('DIMACS', 'fast', 'cc2v3'):    RAW_ROOT / 'DIMACS/cc2v3/cc2v3-dimacs.csv',
    # DIMACS10  (note the original directory name is misspelled: DIAMCS10)
    ('DIMACS10', 'deep', 'dualdeep'): RAW_ROOT / 'DIAMCS10/deepOpt/dualdeep1H-dimacs10-GAP1.csv',
    ('DIMACS10', 'deep', 'deepOpt'):  RAW_ROOT / 'DIAMCS10/deepOpt/deep1H-dimacs10.csv',
    ('DIMACS10', 'fast', 'dualcc2v3'): RAW_ROOT / 'DIAMCS10/cc2v3/dualcc2v3-DIMACS10.csv',
    ('DIMACS10', 'fast', 'cc2v3'):    RAW_ROOT / 'DIAMCS10/cc2v3/cc2v3-DIMACS10.csv',
    # NDR
    ('NDR', 'deep', 'dualdeep'): RAW_ROOT / 'NDR/deepOpt/dualdeep1H-NDR-GAP1.csv',
    ('NDR', 'deep', 'deepOpt'):  RAW_ROOT / 'NDR/deepOpt/deep1H-NDR.csv',
    ('NDR', 'fast', 'dualcc2v3'): RAW_ROOT / 'NDR/cc2v3/dualcc2v3-ndr.csv',
    ('NDR', 'fast', 'cc2v3'):    RAW_ROOT / 'NDR/cc2v3/cc2v3-ndr.csv',
    # SNAP
    ('SNAP', 'deep', 'dualdeep'): RAW_ROOT / 'SNAP/deepOpt/dualdeepV4GAP1-SNAP-1H.csv',
    ('SNAP', 'deep', 'deepOpt'):  RAW_ROOT / 'SNAP/deepOpt/deep1H-snap.csv',
    ('SNAP', 'fast', 'dualcc2v3'): RAW_ROOT / 'SNAP/cc2v3/dualcc2v3-snap.csv',
    ('SNAP', 'fast', 'cc2v3'):    RAW_ROOT / 'SNAP/cc2v3/cc2v3-snap.csv',
}

SUMMARY = re.compile(
    r'^\s*(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+'
    r'\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+'
    r'(?:(====)\s+(\d+)|([\d.]+)\s+(\d+))\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)'
)
SIMPLE = re.compile(r'^\s*([^,\s]+)\s*,\s*([-+]?\d+(?:\.\d+)?)\s*$')
# wspace 6-column from appendix statistical tables. The columns are not the
# solver's final ``#LB`` summary, so only SUMMARY rows are treated as reliable LB.
# Examples:
#   "T2_1000_10000_0.wclq 10 112 4423 0.114688 3600"
#   "frb30-15-1.clq 10 3 4 0.00511849 3600"
#   "brock200_1.clq 10 4 13 0.00102878 3600"
WSPACE6 = re.compile(
    r'^\s*(\S+)\s+(\d+)\s+(\d+)\s+(\d+)\s+([\d.eE+-]+)\s+([\d.eE+-]+)\s*$'
)


def mean(xs):
    return sum(xs) / len(xs) if xs else ''


def median(xs):
    return stats.median(xs) if xs else ''


def norm_num(x):
    if x == '':
        return ''
    if isinstance(x, float) and x.is_integer():
        return int(x)
    return x


def parse_file(dataset, family, baseline_solver, path):
    """Return parsed records.

    Only SUMMARY rows expose the solver's LB fields unambiguously. SIMPLE and
    WSPACE6 rows are appendix table values and are kept as reported_value only;
    they must not be used in LB head-to-head comparisons.
    """
    rows = []
    if not path.exists():
        return rows
    text = path.read_text(errors='replace')
    for line_no, raw in enumerate(text.splitlines(), 1):
        line = raw.strip()
        if not line:
            continue
        m = SUMMARY.search(line)
        if m:
            inst = m.group(1)
            V = int(m.group(2)); E = int(m.group(3))
            lgap = float(m.group(4)); first_lb = int(m.group(5)); best_lb = int(m.group(6))
            if m.group(7) == '====':
                final_gap = 0.0
                best_ub = int(m.group(8))
            else:
                final_gap = float(m.group(9))
                best_ub = int(m.group(10))
            first_ub = int(m.group(11)); ugap = float(m.group(12))
            rows.append({
                'dataset': dataset, 'family': family, 'baseline_solver': baseline_solver,
                'instance': inst, 'line_no': line_no, 'format': 'summary',
                'has_lb': 1, 'V': V, 'E': E,
                'first_lb': first_lb, 'best_lb': best_lb, 'best_ub': best_ub,
                'first_ub': first_ub, 'final_gap': final_gap, 'historical_value': best_ub,
                'lgap': lgap, 'ugap': ugap,
            })
            continue
        m = SIMPLE.match(line)
        if m:
            val = float(m.group(2))
            reported_value = int(val) if val.is_integer() else val
            rows.append({
                'dataset': dataset, 'family': family, 'baseline_solver': baseline_solver,
                'instance': m.group(1), 'line_no': line_no, 'format': 'simple',
                'has_lb': 0, 'V': '', 'E': '',
                'first_lb': '', 'best_lb': '', 'best_ub': '', 'first_ub': '',
                'final_gap': '', 'historical_value': reported_value, 'lgap': '', 'ugap': '',
            })
            continue
        m = WSPACE6.match(line)
        if m:
            inst = m.group(1)
            run_or_group = int(m.group(2))
            reported_a = int(m.group(3))
            reported_value = int(m.group(4))
            gap = float(m.group(5))
            time_s = float(m.group(6))
            rows.append({
                'dataset': dataset, 'family': family, 'baseline_solver': baseline_solver,
                'instance': inst, 'line_no': line_no, 'format': 'wspace6',
                'has_lb': 0, 'V': '', 'E': '',
                'first_lb': '', 'best_lb': '', 'best_ub': '', 'first_ub': '',
                'final_gap': gap, 'historical_value': reported_value, 'lgap': '', 'ugap': '',
                'run_or_group': run_or_group, 'reported_a': reported_a, 'time_s': time_s,
            })
    return rows


def aggregate(records):
    grouped = defaultdict(list)
    for r in records:
        grouped[(r['dataset'], r['family'], r['baseline_solver'], r['instance'])].append(r)
    out = []
    for (dataset, family, baseline_solver, inst), recs in sorted(grouped.items()):
        def values(key):
            return [r[key] for r in recs if r.get(key) not in ('', None)]
        best_lbs = values('best_lb')
        first_lbs = values('first_lb')
        best_ubs = values('best_ub')
        final_gaps = values('final_gap')
        Vs = values('V'); Es = values('E')
        formats = sorted(set(r['format'] for r in recs))
        n_runs_total = len(recs)
        out.append({
            'dataset': dataset,
            'family': family,
            'baseline_solver': baseline_solver,
            'instance': inst,
            'rows': len(recs),
            'n_runs_total': n_runs_total,
            'formats': '+'.join(formats),
            'has_lb_summary': int(any(r['format'] == 'summary' for r in recs)),
            'V': Vs[0] if Vs else '',
            'E': Es[0] if Es else '',
            'first_lb_min': min(first_lbs) if first_lbs else '',
            'first_lb_mean': norm_num(mean(first_lbs)),
            'first_lb_median': norm_num(median(first_lbs)),
            'best_lb_min': min(best_lbs) if best_lbs else '',
            'best_lb_mean': norm_num(mean(best_lbs)),
            'best_lb_median': norm_num(median(best_lbs)),
            'best_lb_max': max(best_lbs) if best_lbs else '',
            'best_ub_min': min(best_ubs) if best_ubs else '',
            'best_ub_mean': norm_num(mean(best_ubs)),
            'best_ub_median': norm_num(median(best_ubs)),
            'final_gap_mean': norm_num(mean(final_gaps)),
        })
    return out


def main():
    records = []
    skipped = []
    for (dataset, family, baseline_solver), path in FILES.items():
        if not path.exists():
            skipped.append((dataset, family, baseline_solver, str(path)))
            continue
        records.extend(parse_file(dataset, family, baseline_solver, path))

    raw_path = EXP8_ROOT / 'baseline_records.csv'
    index_path = EXP8_ROOT / 'baseline_index.csv'

    if records:
        # union of keys (wspace6 adds n_runs_aggregated/time_s)
        all_keys = set()
        for r in records:
            all_keys.update(r.keys())
        # canonical order
        primary = ['dataset', 'family', 'baseline_solver', 'instance', 'line_no', 'format',
                   'has_lb', 'V', 'E', 'first_lb', 'best_lb', 'best_ub', 'first_ub',
                   'final_gap', 'historical_value', 'lgap', 'ugap', 'n_runs_aggregated', 'time_s']
        fieldnames = [k for k in primary if k in all_keys] + sorted(all_keys - set(primary))
        with raw_path.open('w', newline='') as f:
            w = csv.DictWriter(f, fieldnames=fieldnames, extrasaction='ignore')
            w.writeheader()
            w.writerows(records)
    indexed = aggregate(records)
    if indexed:
        with index_path.open('w', newline='') as f:
            fieldnames = list(indexed[0].keys())
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            w.writerows(indexed)
    print(f'wrote {index_path}  ({len(indexed)} aggregated rows)')
    print(f'wrote {raw_path}    ({len(records)} raw rows)')
    if skipped:
        print('Skipped (file missing):')
        for s in skipped:
            print('  ', s)


if __name__ == '__main__':
    main()
