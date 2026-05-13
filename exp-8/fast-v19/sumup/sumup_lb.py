#!/usr/bin/env python3
import argparse, csv, re, statistics as stats
from collections import defaultdict
from pathlib import Path
CONFIGS={'deep-v6':{'solvers':{'deep-v6'},'family':'deep','prefix':'exp8_deep'},'fast-v19':{'solvers':{'fast-v19'},'family':'fast','prefix':'exp8_v19'}}
SUB=Path(__file__).resolve().parents[1].name; CFG=CONFIGS[SUB]; EXP8_ROOT=Path(__file__).resolve().parents[2]; BASELINE_INDEX=EXP8_ROOT/'baseline_index.csv'
RE_SUMMARY=re.compile(r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+([\d.]+)\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)")
RE_OPTIMAL=re.compile(r">>>\s+(\S+)\s+\|V\|\s+(\d+)\s+\|E\|\s+(\d+)\s+\(#LB\s+([\d.]+)\s+(\d+)\s+--->\s+(\d+)\s+====\s+(\d+)\s+<---\s+(\d+)\s+([\d.]+)\s+#UB\)")
RE_TIMEOUT=re.compile(r">>>\s+Benchmark\s+(\S+)\s+Status\s+(TIMEOUT|MEMOUT)")
RE_ROUND_FULL=re.compile(r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s+([\d.]+)\s*$")
RE_ROUND_SHORT=re.compile(r"^\s*(\d+)\s+(-?\d+)\s+(-?\d+)\s+(-?\d+)\s+([\d.]+)\s*$")
def gap(ub,lb): return (ub-lb)/lb if ub and lb and lb>0 else -1.0
def parse_out(p):
    text=p.read_text(errors='replace'); lines=text.splitlines(); rounds=[]
    for line in lines:
        m=RE_ROUND_FULL.match(line)
        if m: rounds.append({'lb':int(m.group(2)),'best_lb':int(m.group(3)),'ub_lb':int(m.group(4)),'best_ub':int(m.group(7))}); continue
        m=RE_ROUND_SHORT.match(line)
        if m: rounds.append({'lb':int(m.group(2)),'best_lb':int(m.group(3)),'ub_lb':int(m.group(4)),'best_ub':0})
    for line in reversed(lines):
        m=RE_SUMMARY.search(line)
        if m:
            first_lb=int(m.group(5)); best_lb=int(m.group(6)); best_ub=int(m.group(8)); first_ub=int(m.group(9))
            return {'instance':m.group(1),'V':int(m.group(2)),'E':int(m.group(3)),'first_lb':first_lb,'best_lb':best_lb,'first_ub':first_ub,'best_ub':best_ub,'gap':gap(best_ub,best_lb),'status':'OK','n_rounds':len(rounds)}
        m=RE_OPTIMAL.search(line)
        if m:
            first_lb=int(m.group(5)); best_lb=int(m.group(6)); best_ub=int(m.group(7)); first_ub=int(m.group(8))
            return {'instance':m.group(1),'V':int(m.group(2)),'E':int(m.group(3)),'first_lb':first_lb,'best_lb':best_lb,'first_ub':first_ub,'best_ub':best_ub,'gap':0.0,'status':'OPT','n_rounds':len(rounds)}
        m=RE_TIMEOUT.search(line)
        if m and rounds:
            best_lb=max(r['best_lb'] for r in rounds); first_lb=rounds[0]['lb']; ubc=[r['best_ub'] for r in rounds if r['best_ub']>0] or [r['ub_lb'] for r in rounds if r['ub_lb']>0]; best_ub=min(ubc) if ubc else 0
            return {'instance':m.group(1),'V':0,'E':0,'first_lb':first_lb,'best_lb':best_lb,'first_ub':rounds[0]['ub_lb'],'best_ub':best_ub,'gap':gap(best_ub,best_lb),'status':m.group(2),'n_rounds':len(rounds)}
    return None
def parse_dir(d):
    name=d.name; m=re.search(r'-(\d{14})$',name); ts=m.group(1) if m else ''; solver=next((s for s in sorted(CFG['solvers'],key=len,reverse=True) if f'-{s}-' in name),None); ds=next((x for x in ['DIMACS10','BHOSLIB','DIMACS','SNAP','UDG','NDR','T1','T2'] if f'-{x}-' in name or f'-{x}_' in name),'unknown'); m=re.search(r'-s(\d+)-\d{14}$',name); seed=int(m.group(1)) if m else 0; return solver,ds,seed,ts
def load_baseline():
    out={}
    if BASELINE_INDEX.exists():
        for r in csv.DictReader(BASELINE_INDEX.open()):
            if r['family']==CFG['family']: out[(r['dataset'],r['instance'])]=r
    return out
def scan(root):
    rows=[]; root=Path(root)
    if not root.exists(): return rows
    for d in sorted(root.iterdir()):
        if not d.is_dir() or not d.name.startswith('result-'): continue
        solver,ds,seed,ts=parse_dir(d)
        if solver not in CFG['solvers']: continue
        for f in sorted(d.glob('*.out')):
            rec=parse_out(f)
            if rec: rec.update({'solver':solver,'dataset':ds,'seed':seed,'timestamp':ts,'lb_gain':rec['best_lb']-rec['first_lb']}); rows.append(rec)
    return rows
def mean(xs): return sum(xs)/len(xs) if xs else ''
def median(xs): return stats.median(xs) if xs else ''
def stdev(xs): return stats.stdev(xs) if len(xs)>1 else (0 if xs else '')
def aggregate(rows,baseline):
    g=defaultdict(list)
    for r in rows: g[(r['dataset'],r['instance'])].append(r)
    out=[]
    for (ds,inst),recs in sorted(g.items()):
        lbs=[r['best_lb'] for r in recs]; gains=[r['lb_gain'] for r in recs]; gaps=[r['gap'] for r in recs if r['gap']>=0]; b=baseline.get((ds,inst),{}); delta=''
        if b.get('best_lb_mean') not in ('',None):
            try: delta=mean(lbs)-float(b['best_lb_mean'])
            except ValueError: delta=''
        out.append({'dataset':ds,'instance':inst,'runs':len(recs),'best_lb_min':min(lbs),'best_lb_mean':mean(lbs),'best_lb_median':median(lbs),'best_lb_max':max(lbs),'best_lb_std':stdev(lbs),'lb_gain_mean':mean(gains),'lb_gain_median':median(gains),'lb_gain_std':stdev(gains),'gap_mean':mean(gaps),'gap_median':median(gaps),'baseline_repeats':b.get('repeats',''),'baseline_has_lb_summary':b.get('has_lb_summary',''),'baseline_best_lb_mean':b.get('best_lb_mean',''),'delta_best_lb_vs_baseline':delta,'baseline_value_mean':b.get('historical_value_mean','')})
    return out
def write_csv(p,rows):
    if not rows: p.write_text(''); return
    with p.open('w',newline='') as f: w=csv.DictWriter(f,fieldnames=list(rows[0].keys())); w.writeheader(); w.writerows(rows)
def report(p,rows,agg):
    lines=[f"# exp-8 {CFG['family']} LB summary",'',f'- runs parsed: {len(rows)}',f'- instances parsed: {len(agg)}','']
    if agg:
        by=defaultdict(list)
        for r in agg: by[r['dataset']].append(r)
        lines+=['| dataset | instances | avg best_lb | avg LB gain | avg gap | baseline LB comparable |','|---|---:|---:|---:|---:|---:|']
        for ds in sorted(by):
            rs=by[ds]; avg_lb=mean([float(r['best_lb_mean']) for r in rs]); avg_gain=mean([float(r['lb_gain_mean']) for r in rs]); avg_gap=mean([float(r['gap_mean']) for r in rs if r['gap_mean']!='']); comp=sum(1 for r in rs if r['baseline_best_lb_mean'] not in ('',None)); lines.append(f'| {ds} | {len(rs)} | {avg_lb:.3f} | {avg_gain:.3f} | {avg_gap:.6f} | {comp} |')
    else: lines.append('No result rows found yet.')
    p.write_text('\n'.join(lines)+'\n')
def main():
    ap=argparse.ArgumentParser(); ap.add_argument('result_root',nargs='?',default='../jobs/result'); ap.add_argument('--output_dir',default='./analysis'); args=ap.parse_args(); out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); rows=scan(args.result_root); baseline=load_baseline(); agg=aggregate(rows,baseline); write_csv(out/f"{CFG['prefix']}_lb_results.csv",rows); write_csv(out/f"{CFG['prefix']}_lb_aggregate.csv",agg); report(out/f"{CFG['prefix']}_lb_summary.md",rows,agg); print(f'wrote {out}')
if __name__=='__main__': main()
