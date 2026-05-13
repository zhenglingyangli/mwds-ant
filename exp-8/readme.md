# exp-8: Eight-Dataset LB Improvement Study

This experiment runs only `deep-v6` and `fast-v19` on 8 datasets × 5 selected instances × 5 seeds. Historical baselines come from `Technical Appendix-2814` and are indexed in `baseline_index.csv`.

Known paths:
- Data root: `/public/home/acs4vb4pqv/benchmarks/MWDS2026`
- T1: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/T1_wclq`
- T2: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/T2_wclq`
- UDG: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/UDG_wclq`
- BHOSLIB: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/BHOSLIB`
- DIMACS: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/dimacs`
- DIMACS10: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/DIMACS10`
- NDR: `/public/home/acs4vb4pqv/benchmarks/MWDS2026` (recursive search covers `NDR`, `NDR_BIG`, and `NDR_BIG_BIG`)
- SNAP: `/public/home/acs4vb4pqv/benchmarks/MWDS2026/SNAP`

Update `dataset_manifest.json` before submitting jobs for datasets whose path is still `TODO_CONFIRM_ON_HPC/...`.

Recommended cluster entrypoint:

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
git pull origin main

# Preflight only: validates dataset paths, selected instance files, compilation,
# and parser smoke tests, then generates 80 SLURM scripts without submitting.
bash exp-8/run_on_hpc.sh --no-submit

# Full run: repeats preflight, then asks you to type RUN before submission.
bash exp-8/run_on_hpc.sh
```
