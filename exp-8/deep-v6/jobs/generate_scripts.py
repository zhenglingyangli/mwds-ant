#!/usr/bin/env python3
import argparse, json, os
from pathlib import Path
CONFIGS={'deep-v6':{'solver_name':'deep-v6','solver_dir':'Dual-Deep-v6','solver_bin':'dual-deep-v6'},'fast-v19':{'solver_name':'fast-v19','solver_dir':'Dual-Fast-v19','solver_bin':'dual-fast-v19'}}
DATASETS=['T1','T2','UDG','BHOSLIB','DIMACS','DIMACS10','NDR','SNAP']
DEFAULT_SEEDS=[1,2,3,4,5]
CUTOFF=3600; ALPHA=90; PARALLEL=5; GO_TIMEOUT=CUTOFF+120; CUTOFF_MEM=16
SLURM_PARTITION='hfacnormal01'; SLURM_MEM='64G'; SLURM_TIME='0-04:00:00'
EXP8_ROOT=Path(__file__).resolve().parents[2]
MANIFEST=EXP8_ROOT/'dataset_manifest.json'; SELECTED_DIR=EXP8_ROOT/'selected_instances'
def parse_seeds(text):
    vals=[]
    for part in text.split(','):
        part=part.strip()
        if not part: continue
        if '-' in part:
            a,b=part.split('-',1); vals.extend(range(int(a),int(b)+1))
        else: vals.append(int(part))
    return sorted(set(vals))
def cfg():
    sub=Path(__file__).resolve().parents[1].name
    if sub not in CONFIGS: raise SystemExit(f'Unknown subexperiment {sub}')
    return sub, CONFIGS[sub]
def load_paths(mode, allow, datasets):
    data=json.loads(MANIFEST.read_text()); out={}
    for ds in datasets:
        info=data[ds]
        p=info.get(f'{mode}_path') or (info.get('hpc_path') if mode=='local' else None)
        if not p: raise SystemExit(f'No {mode}_path for {ds}')
        if p.startswith('TODO_CONFIRM') and not allow: raise SystemExit(f'{ds} path is unconfirmed: {p}')
        out[ds]=p
    return out
def main():
    sub,c=cfg(); ap=argparse.ArgumentParser(); ap.add_argument('--datasets',default=','.join(DATASETS)); ap.add_argument('--seeds',default=','.join(map(str,DEFAULT_SEEDS))); ap.add_argument('--path-mode',choices=['hpc','local'],default='hpc'); ap.add_argument('--allow-unconfirmed',action='store_true'); args=ap.parse_args()
    seeds=parse_seeds(args.seeds); datasets=[x.strip() for x in args.datasets.split(',') if x.strip()]
    paths=load_paths(args.path_mode,args.allow_unconfirmed,datasets)
    solver=f"../codes/{c['solver_dir']}/{c['solver_bin']}"; generated=[]
    for ds in datasets:
        if ds not in DATASETS: raise SystemExit(f'Unknown dataset {ds}')
        if not (SELECTED_DIR/f'{ds}.txt').exists(): raise SystemExit(f'Missing selected list for {ds}')
        for seed in seeds:
            suffix=f"{c['solver_name']}-{ds}-s{seed}"; script=f'jobslurm-{suffix}'
            content=f"""#!/bin/sh
#SBATCH --job-name=e8_{c['solver_name'].replace('-','')[:6]}_{ds[:2]}_s{seed}
#SBATCH --partition={SLURM_PARTITION}
#SBATCH --time={SLURM_TIME}
#SBATCH --output=slurm-%j.out
#SBATCH --mem={SLURM_MEM}
#SBATCH --nodes=1
#SBATCH --cpus-per-task={PARALLEL}
echo "-----------------------------------------------------------"
echo "hostname       = $(hostname)"
echo "SLURM_JOBID    = $SLURM_JOBID"
echo "SLURM_NODELIST = $SLURM_NODELIST"
echo "-----------------------------------------------------------"
cd "$SLURM_SUBMIT_DIR"
DATASET_DIR="{paths[ds]}"
NAMELIST="../../selected_instances/{ds}.txt"
if [ ! -d "$DATASET_DIR" ]; then
    echo "ERROR: dataset path does not exist: $DATASET_DIR"
    exit 2
fi
python3 ./goSolver.py {PARALLEL} {GO_TIMEOUT} \
    {solver} "$DATASET_DIR" ./result \
    --cutoff_mem {CUTOFF_MEM} \
    --name_list "$NAMELIST" \
    --suffix {suffix} \
    {CUTOFF} {seed} {ALPHA}
echo "=== DONE: {suffix} ==="
"""
            Path(script).write_text(content); os.chmod(script,0o755); generated.append(script)
    with open('submit_all.sh','w') as f:
        f.write('#!/bin/bash\nset -e\n')
        for s in sorted(generated): f.write(f'sbatch {s}\nsleep 0.5\n')
        f.write(f"echo '=== {len(generated)} jobs submitted for {sub} ==='\n")
    os.chmod('submit_all.sh',0o755); print(f'Generated {len(generated)} scripts for {sub}')
if __name__=='__main__': main()
