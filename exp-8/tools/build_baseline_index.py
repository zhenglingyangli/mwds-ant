#!/usr/bin/env python3
"""Build a historical baseline index from Technical Appendix-2814 raw-data."""

import csv
import re
import statistics as stats
from collections import defaultdict
from pathlib import Path

EXP8_ROOT = Path(__file__).resolve().parents[1]
RAW_ROOT = EXP8_ROOT.parent / 'Technical Appendix-2814' / 'Technical Appendix-2814' / 'experiments' / 'raw-data'

FILES = {
    ('T1', 'deep'): RAW_ROOT / 'T1/deepOpt/dualdeep-T1.csv',
    ('T1', 'fast'): RAW_ROOT / 'T1/cc2v3/dualcc2v3-T1.csv',
    ('T2', 'deep'): RAW_ROOT / 'T2/deepOpt/dualdeep-T2.csv',
    ('T2', 'fast'): RAW_ROOT / 'T2/cc2v3/dualcc2v3-T2.csv',
    ('UDG', 'deep'): RAW_ROOT / 'UDG/deepOpt/dualdeep-UDG.csv',
    ('UDG', 'fast'): RAW_ROOT / 'UDG/cc2v3/dualcc2v3-UDG.csv',
    ('BHOSLIB', 'deep'): RAW_ROOT / 'BHOSLIB/deepOpt/dualdeep-BHOSLIB.csv',
    ('BHOSLIB', 'fast'): RAW_ROOT / 'BHOSLIB/cc2v3/dualcc2v3-frb.csv',
    ('DIMACS', 'deep'): RAW_ROOT / 'DIMACS/deepOpt/dualdeep-dimacs.csv',
    ('DIMACS', 'fast'): RAW_ROOT / 'DIMACS/cc2v3/dualcc2v3-dimacs.csv',
    ('DIMACS10', 'deep'): RAW_ROOT / 'DIAMCS10/deepOpt/dualdeep1H-dimacs10-GAP1.csv',
    ('DIMACS10', 'fast'): RAW_ROOT / 'DIAMCS10/cc2v3/dualcc2v3-DIMACS10.csv',
    ('NDR', 'deep'): RAW_ROOT / 'NDR/deepOpt/dualdeep1H-NDR-GAP1.csv',
    ('NDR', 'fast'): RAW_ROOT / 'NDR/cc2v3/dualcc2v3-ndr.csv',
    ('SNAP', 'deep'): RAW_ROOT / 'SNAP/deepOpt/dualdeepV4GAP1-SNAP-1H.csv',
    ('SNAP', 'fast'): RAW_ROOT / 'SNAP/cc2v3/dualcc2v3-snap.csv',
}

SUMMARY = re.compile(
    r'^\s*(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+'
    r'\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+'
    r'(?:(====)\s+(\d+)|([\d.]+)\s+(\d+))\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)'
)
SIMPLE = re.compile(r'^\s*([^,\s]+)\s*,\s*([-+]?\d+(?:\.\d+)?)')


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


def parse_file(dataset, family, path):
    rows = []
    if not path.exists():
        return rows
    for line_no, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
        line = line.strip()
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
                'dataset': dataset, 'family': family, 'instance': inst, 'line_no': line_no,
                'format': 'summary', 'has_lb': 1, 'V': V, 'E': E,
                'first_lb': first_lb, 'best_lb': best_lb, 'best_ub': best_ub,
                'first_ub': first_ub, 'final_gap': final_gap, 'historical_value': best_ub,
                'lgap': lgap, 'ugap': ugap,
            })
            continue
        m = SIMPLE.search(line)
        if m:
            val = float(m.group(2))
            rows.append({
                'dataset': dataset, 'family': family, 'instance': m.group(1), 'line_no': line_no,
                'format': 'simple', 'has_lb': 0, 'V': '', 'E': '',
                'first_lb': '', 'best_lb': '', 'best_ub': '', 'first_ub': '',
                'final_gap': '', 'historical_value': val, 'lgap': '', 'ugap': '',
            })
    return rows


def aggregate(records):
    grouped = defaultdict(list)
    for r in records:
        grouped[(r['dataset'], r['family'], r['instance'])].append(r)
    out = []
    for (dataset, family, inst), recs in sorted(grouped.items()):
        def values(key):
            return [r[key] for r in recs if r[key] != '']
        best_lbs = values('best_lb')
        first_lbs = values('first_lb')
        best_ubs = values('best_ub')
        final_gaps = values('final_gap')
        hist_vals = values('historical_value')
        Vs = values('V'); Es = values('E')
        formats = sorted(set(r['format'] for r in recs))
        out.append({
            'dataset': dataset,
            'family': family,
            'baseline_solver': 'dualdeep' if family == 'deep' else 'dualcc2v3',
            'instance': inst,
            'repeats': len(recs),
            'formats': '+'.join(formats),
            'has_lb_summary': int(bool(best_lbs)),
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
            'final_gap_mean': mean(final_gaps),
            'historical_value_min': min(hist_vals) if hist_vals else '',
            'historical_value_mean': norm_num(mean(hist_vals)),
            'historical_value_median': norm_num(median(hist_vals)),
        })
    return out


def main():
    records = []
    for (dataset, family), path in FILES.items():
        records.extend(parse_file(dataset, family, path))
    raw_path = EXP8_ROOT / 'baseline_records.csv'
    index_path = EXP8_ROOT / 'baseline_index.csv'
    if records:
        with raw_path.open('w', newline='') as f:
            fieldnames = list(records[0].keys())
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader(); w.writerows(records)
    indexed = aggregate(records)
    with index_path.open('w', newline='') as f:
        fieldnames = list(indexed[0].keys()) if indexed else []
        w = csv.DictWriter(f, fieldnames=fieldnames)
        w.writeheader(); w.writerows(indexed)
    print(f'wrote {index_path} ({len(indexed)} rows)')
    print(f'wrote {raw_path} ({len(records)} rows)')


if __name__ == '__main__':
    main()
