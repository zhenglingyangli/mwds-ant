#!/usr/bin/env bash
# Pack the exp-8 balanced 8x5 dataset on HPC.
#
# Intended workflow:
#   1. On local: commit/push this script.
#   2. On HPC repo: git pull.
#   3. On HPC repo: bash exp-8/pack_balanced40_from_hpc.sh
#   4. On HPC repo: git add exp-8/balanced40_package && git commit && git push
#   5. On local: git pull, then run exp-8/unpack_balanced40_local.sh
#
# Notes:
# - The selected instances are exp-8/selected_instances/*.txt.
# - Dataset paths are read from exp-8/dataset_manifest.json.
# - If the HPC data root differs, set BAL40_DATA_ROOT or BAL40_SEARCH_ROOTS.
# - The final archive is split into 90MB chunks to avoid GitHub's 100MB limit.

set -euo pipefail

EXP8="$(cd "$(dirname "$0")" && pwd)"
OUT="$EXP8/balanced40_package"
WORK="$OUT/work"
DATA="$WORK/data"
MANIFEST="$EXP8/dataset_manifest.json"
SELECTED="$EXP8/selected_instances"
TS="$(date +%Y%m%d_%H%M%S)"
ARCHIVE="$OUT/balanced40_data_${TS}.tar.gz"
SPLIT_PREFIX="$ARCHIVE.part-"
CHUNK_SIZE="${BAL40_CHUNK_SIZE:-90m}"

mkdir -p "$OUT" "$DATA"
rm -rf "$WORK"
mkdir -p "$DATA"

echo "============================================================"
echo "Pack balanced40 data"
echo "  exp-8     : $EXP8"
echo "  manifest  : $MANIFEST"
echo "  output    : $OUT"
echo "  chunk size: $CHUNK_SIZE"
echo "============================================================"

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || {
    echo "ERROR: missing command: $1" >&2
    exit 2
  }
}

require_cmd python3
require_cmd tar
require_cmd sha256sum
require_cmd split

python3 - "$EXP8" "$WORK" <<'PY'
import json
import os
import shutil
import sys
from pathlib import Path

exp8 = Path(sys.argv[1])
work = Path(sys.argv[2])
data = work / "data"
manifest = json.loads((exp8 / "dataset_manifest.json").read_text())
selected_dir = exp8 / "selected_instances"

datasets = ["T1", "T2", "UDG", "BHOSLIB", "DIMACS", "DIMACS10", "NDR", "SNAP"]

def family_roots(ds):
    roots = []
    # 1. Explicit root override: /.../MWDS2026
    data_root = os.environ.get("BAL40_DATA_ROOT")
    if data_root:
        mapping = {
            "T1": "T1_wclq",
            "T2": "T2_wclq",
            "UDG": "UDG_wclq",
            "BHOSLIB": "BHOSLIB",
            "DIMACS": "dimacs",
            "DIMACS10": "DIMACS10",
            "SNAP": "SNAP",
            # NDR is recursive from root because it may live in NDR/NDR_BIG/NDR_BIG_BIG.
            "NDR": "",
        }
        roots.append(Path(data_root) / mapping[ds])

    # 2. Path recorded in exp-8/dataset_manifest.json.
    if ds in manifest and manifest[ds].get("hpc_path"):
        roots.append(Path(manifest[ds]["hpc_path"]))

    # 3. Fallback search roots.
    search_roots = os.environ.get(
        "BAL40_SEARCH_ROOTS",
        "/public/home/acs4vb4pqv/benchmarks/MWDS2026:/public/home/acs4vb4pqv",
    )
    for root in [Path(x) for x in search_roots.split(":") if x]:
        if ds == "T1":
            roots.append(root / "T1_wclq")
        elif ds == "T2":
            roots.append(root / "T2_wclq")
        elif ds == "UDG":
            roots.append(root / "UDG_wclq")
        elif ds == "BHOSLIB":
            roots.append(root / "BHOSLIB")
        elif ds == "DIMACS":
            roots.append(root / "dimacs")
        elif ds == "DIMACS10":
            roots.append(root / "DIMACS10")
        elif ds == "SNAP":
            roots.append(root / "SNAP")
        elif ds == "NDR":
            roots.append(root)

    # Keep order, remove duplicates.
    out = []
    seen = set()
    for r in roots:
        key = str(r)
        if key not in seen:
            seen.add(key)
            out.append(r)
    return out

def resolve(ds, name):
    for root in family_roots(ds):
        if not root.exists():
            continue
        direct = root / name
        if direct.is_file():
            return direct
        # NDR and uncertain HPC layouts: recursive fallback.
        for cur, _dirs, files in os.walk(root):
            if name in files:
                return Path(cur) / name
    return None

resolved = []
missing = []
for ds in datasets:
    names = [
        x.strip()
        for x in (selected_dir / f"{ds}.txt").read_text().splitlines()
        if x.strip()
    ]
    if len(names) != 5:
        raise SystemExit(f"{ds}: expected 5 selected instances, got {len(names)}")
    (data / ds).mkdir(parents=True, exist_ok=True)
    for name in names:
        src = resolve(ds, name)
        if src is None:
            missing.append((ds, name, [str(x) for x in family_roots(ds)]))
            continue
        dst = data / ds / name
        shutil.copy2(src, dst)
        resolved.append((ds, name, str(src), str(dst), dst.stat().st_size))

if missing:
    print("ERROR: missing selected instances:")
    for ds, name, roots in missing:
        print(f"  - {ds}/{name}")
        for r in roots:
            print(f"      searched: {r}")
    raise SystemExit(2)

(work / "resolved_instances.tsv").write_text(
    "family\tname\tsource_path\tpackage_path\tsize_bytes\n"
    + "\n".join("\t".join(map(str, row)) for row in resolved)
    + "\n"
)

package_manifest = {
    "comment": "exp-8 balanced 8x5 dataset copied from HPC",
    "source_exp8": str(exp8),
    "instances": [
        {
            "family": ds,
            "name": name,
            "source_path": src,
            "package_path": f"data/{ds}/{name}",
            "size_bytes": size,
        }
        for ds, name, src, _dst, size in resolved
    ],
}
(work / "package_manifest.json").write_text(json.dumps(package_manifest, indent=2))

print(f"resolved and copied {len(resolved)} files")
print(f"work dir: {work}")
PY

echo
echo "Creating archive: $ARCHIVE"
tar -C "$WORK" -czf "$ARCHIVE" data package_manifest.json resolved_instances.tsv
sha256sum "$ARCHIVE" > "$ARCHIVE.sha256"

echo
echo "Splitting archive into <= $CHUNK_SIZE chunks"
rm -f "$SPLIT_PREFIX"*
split -b "$CHUNK_SIZE" -d -a 3 "$ARCHIVE" "$SPLIT_PREFIX"
sha256sum "$SPLIT_PREFIX"* > "$ARCHIVE.parts.sha256"

cat > "$OUT/README.md" <<EOF
# balanced40 package

Generated on HPC by \`exp-8/pack_balanced40_from_hpc.sh\`.

Files:

- \`$(basename "$ARCHIVE")\`: full archive (may exceed GitHub per-file limit)
- \`$(basename "$ARCHIVE").sha256\`: checksum for full archive
- \`$(basename "$ARCHIVE").parts.sha256\`: checksums for split parts
- \`$(basename "$SPLIT_PREFIX")000...\`: 90MB split parts for git push

Recommended git payload:

\`\`\`bash
git add exp-8/balanced40_package/README.md \\
        exp-8/balanced40_package/$(basename "$ARCHIVE").part-* \\
        exp-8/balanced40_package/$(basename "$ARCHIVE").parts.sha256
git commit -m "Add balanced40 data package chunks"
git push
\`\`\`

On local after pull:

\`\`\`bash
bash exp-8/unpack_balanced40_local.sh
\`\`\`
EOF

echo
echo "Package complete:"
ls -lh "$OUT" | sed 's/^/  /'
echo
echo "If you want to push through GitHub, add the split parts, not the full tar.gz."
