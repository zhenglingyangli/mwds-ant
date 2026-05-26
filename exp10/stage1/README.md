# exp10 Stage 1: DBS + Adaptive ACO Controller Screen

## Purpose

Stage 1 only evaluates Layer-A search behavior:

```text
DBS baseline
vs
DBS + adaptive ACO-style controller
```

The controller does not replace DBS. It only changes in-run search control, such
as LB-side ordering, guards, slope acceptance, or bandit arm selection.

External LP/MILP certificates, known OPT values, and final exact closure are not
used in this stage.

## Candidates

The default candidates are copied controller branches under `code/`:

```text
v005 = online-safe controller
v006 = online slope controller
v007 = contextual bandit controller
v009 = tuned bandit controller
```

Each candidate is evaluated as:

```text
dbs
dbs_aco_<candidate>
```

where both modes use the same candidate binary and differ by `MWDS_AQ_MODE`.

## Directory Layout

```text
stage1/
├── README.md
├── code/
│   ├── deep/
│   │   ├── baseline/
│   │   ├── deepv6/
│   │   ├── v005/
│   │   ├── v006/
│   │   ├── v007/
│   │   └── v009/
│   └── fast/
│       ├── baseline/
│       ├── fastv19/
│       ├── v005/
│       ├── v006/
│       ├── v007/
│       └── v009/
├── jobs/
│   ├── candidates.json
│   ├── generate_scripts.py
│   ├── auto_submit.sh
│   └── goSolver_stage1.py
├── sumup/
│   ├── run_sumup.sh
│   └── result/                 # generated after jobs run; per-candidate raw/CSV outputs
└── analysis/
    ├── begin/
    │   ├── test_smoke.sh
    │   └── fixtures/           # tiny fixture CSVs for begin checks
    └── end/
        └── check_results.py    # strict result gates after jobs finish
```

The split follows the exp-5 convention: `code/` is self-contained source,
`jobs/` generates/submits/runs solver jobs, `sumup/` invokes result checking,
and generated outputs stay under `sumup/result` or `analysis/end`.

## Recommended HPC Flow

Build copied solver code first:

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp10/stage1
for d in code/deep/v005 code/deep/v006 code/deep/v007 code/deep/v009 \
         code/fast/v005 code/fast/v006 code/fast/v007 code/fast/v009; do
  make -C "$d" || exit 1
done
```

Generate a small smoke job:

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp10/stage1
cd jobs
python3 generate_scripts.py \
  --candidates v005 \
  --datasets T1 \
  --seeds 1 \
  --reps 1 \
  --cutoff 20 \
  --workers 20 \
  --path-mode hpc
```

Submit:

```bash
bash auto_submit.sh
```

After jobs finish, check:

```bash
cd ../sumup
bash run_sumup.sh
```

## Local Tool Smoke Test

This first checks fixture CSVs, compiles the copied v005 Deep/Fast code, and runs
a tiny real local T1 smoke if the local T1 path is available.

```bash
cd exp10/stage1/analysis/begin
bash test_smoke.sh
```

## Promotion Rule

Stage 1 is not "LB only". A candidate should pass:

```text
parse_failures = 0
same run count for DBS and controller
total_delta_LB > 0
LB wins > LB losses
total_delta_gap < 0
no large UB regression outlier
#OPT delta >= 0
```

Deep and Fast should be ranked separately before any combined decision.
