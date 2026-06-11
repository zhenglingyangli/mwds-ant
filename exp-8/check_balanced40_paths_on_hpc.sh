#!/usr/bin/env bash
# Check where the exp-8 balanced40 files live on HPC, without copying/packing.
#
# Usage:
#   bash exp-8/check_balanced40_paths_on_hpc.sh
#
# If paths differ from dataset_manifest.json:
#   BAL40_DATA_ROOT=/path/to/MWDS2026 bash exp-8/check_balanced40_paths_on_hpc.sh
# or:
#   BAL40_SEARCH_ROOTS=/root1:/root2 bash exp-8/check_balanced40_paths_on_hpc.sh

set -euo pipefail

EXP8="$(cd "$(dirname "$0")" && pwd)"

python3 - "$EXP8" <<'PY'
import json
import os
import sys
from pathlib import Path

exp8 = Path(sys.argv[1])
manifest = json.loads((exp8 / "dataset_manifest.json").read_text())
selected_dir = exp8 / "selected_instances"
datasets = ["T1", "T2", "UDG", "BHOSLIB", "DIMACS", "DIMACS10", "NDR", "SNAP"]

def family_roots(ds):
    roots = []
    data_root = os.environ.get("BAL40_DATA_ROOT")
    if data_root:
        mapping = {
            "T1": "T1_wclq", "T2": "T2_wclq", "UDG": "UDG_wclq",
            "BHOSLIB": "BHOSLIB", "DIMACS": "dimacs",
            "DIMACS10": "DIMACS10", "SNAP": "SNAP", "NDR": "",
        }
        roots.append(Path(data_root) / mapping[ds])
    if ds in manifest and manifest[ds].get("hpc_path"):
        roots.append(Path(manifest[ds]["hpc_path"]))
    search_roots = os.environ.get(
        "BAL40_SEARCH_ROOTS",
        "/public/home/acs4vb4pqv/benchmarks/MWDS2026:/public/home/acs4vb4pqv",
    )
    for root in [Path(x) for x in search_roots.split(":") if x]:
        roots += [
            root / {
                "T1": "T1_wclq", "T2": "T2_wclq", "UDG": "UDG_wclq",
                "BHOSLIB": "BHOSLIB", "DIMACS": "dimacs",
                "DIMACS10": "DIMACS10", "SNAP": "SNAP", "NDR": "",
            }[ds]
        ]
    out = []
    seen = set()
    for r in roots:
        if str(r) not in seen:
            seen.add(str(r)); out.append(r)
    return out

def resolve(ds, name):
    for root in family_roots(ds):
        if not root.exists():
            continue
        direct = root / name
        if direct.is_file():
            return direct
        for cur, _dirs, files in os.walk(root):
            if name in files:
                return Path(cur) / name
    return None

ok = 0
missing = []
for ds in datasets:
    names = [x.strip() for x in (selected_dir / f"{ds}.txt").read_text().splitlines() if x.strip()]
    print(f"\n[{ds}]")
    for name in names:
        p = resolve(ds, name)
        if p:
            ok += 1
            print(f"  OK      {name:28s} {p}")
        else:
            missing.append((ds, name, family_roots(ds)))
            print(f"  MISSING {name}")

print(f"\nsummary: found {ok}/40")
if missing:
    print("\nmissing details:")
    for ds, name, roots in missing:
        print(f"- {ds}/{name}")
        for r in roots:
            print(f"    searched: {r}")
    raise SystemExit(2)
PY

