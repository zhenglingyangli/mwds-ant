#!/usr/bin/env python3
import argparse, json, os, re
from pathlib import Path
CONFIGS={'deep-v6':{'solver_name':'deep-v6','solver_dir':'Dual-Deep-v6','solver_bin':'dual-deep-v6'},'fast-v19':{'solver_name':'fast-v19','solver_dir':'Dual-Fast-v19','solver_bin':'dual-fast-v19'}}
DATASETS=['T1','T2','UDG','BHOSLIB','DIMACS','DIMACS10','NDR','SNAP']; SEEDS=[1,2,3,4,5]
CUTOFF=3600; ALPHA=90; PARALLEL=5; GO_TIMEOUT=CUTOFF+120; CUTOFF_MEM=16
SLURM_PARTITION='hfacnormal01'; SLURM_MEM='64G'; SLURM_TIME='0-04:00:00'
EXP8_ROOT=Path(__file__).resolve().parents[2]
RE_SUMMARY=re.compile(r">>>\s+\S+\s+\|V\|"); RE_ROUND=re.compile(r"^\s*\d+\s+(-?\d+)\s+(-?\d+)")
def good(p):
    if not p.exists() or p.stat().st_size==0: return False
    t=p.read_text(errors='replace')
    return bool(RE_SUMMARY.search(t) or '====' in t or any(RE_ROUND.match(l) for l in t.splitlines()))
def main():
    sub=Path(__file__).resolve().parents[1].name; c=CONFIGS[sub]
    ap=argparse.ArgumentParser(); ap.add_argument('result_root',nargs='?',default='./result'); ap.add_argument('--allow-unconfirmed',action='store_true'); args=ap.parse_args()
    manifest=json.loads((EXP8_ROOT/'dataset_manifest.json').read_text()); result=Path(args.result_root); scripts=[]
    for ds in DATASETS:
        ds_path=manifest[ds]['hpc_path']
        if ds_path.startswith('TODO_CONFIRM') and not args.allow_unconfirmed: print(f'SKIP {ds}: unconfirmed path {ds_path}'); continue
        insts=[x.strip() for x in (EXP8_ROOT/'selected_instances'/f'{ds}.txt').read_text().splitlines() if x.strip()]
        for seed in SEEDS:
            dirs=list(result.glob(f"result-*-{c['solver_name']}-{ds}-s{seed}-*")) if result.exists() else []
            miss=[i for i in insts if not any(good(d/f'{i}.out') for d in dirs)]
            if not miss: continue
            tag=f"patch-{c['solver_name']}-{ds}-s{seed}"; namelist=f'namelist-{tag}.txt'; Path(namelist).write_text('\n'.join(miss)+'\n')
            script=f'jobslurm-{tag}'
            content=f"""#!/bin/sh
#SBATCH --job-name=p8_{c['solver_name'].replace('-','')[:4]}_{ds[:2]}_s{seed}
#SBATCH --partition={SLURM_PARTITION}
#SBATCH --time={SLURM_TIME}
#SBATCH --output=slurm-%j.out
#SBATCH --mem={SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={PARALLEL}
cd "$SLURM_SUBMIT_DIR"
python3 ./goSolver.py {PARALLEL} {GO_TIMEOUT} \
    ../codes/{c['solver_dir']}/{c['solver_bin']} "{ds_path}" ./result \
    --cutoff_mem {CUTOFF_MEM} \
    --name_list "{namelist}" \
    --suffix {tag} \
    {CUTOFF} {seed} {ALPHA}
"""
            Path(script).write_text(content); os.chmod(script,0o755); scripts.append(script); print(f"{c['solver_name']}/{ds}/seed{seed}: {len(miss)} missing")
    with open('submit_patch.sh','w') as f:
        f.write('#!/bin/bash\nset -e\n')
        for s in sorted(scripts): f.write(f'sbatch {s}\nsleep 0.5\n')
    os.chmod('submit_patch.sh',0o755); print(f'Generated {len(scripts)} patch scripts')
if __name__=='__main__': main()
