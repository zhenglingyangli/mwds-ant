# Stage 1 Controller Audit Protocol

This note records the concrete protocol for the next Stage-1 pass. It is scoped
to run-level controller analysis; it does not change node-level Ant-Q, UB local
search, parsers, or instance lists.

## Failure Audit

Run after Stage-1 results are available:

```bash
cd WMDS26/exp10/stage1/analysis/end
python3 audit_stage1_failures.py \
  --result ../../sumup/result \
  --output stage1_failure_audit.md
```

The audit separates:

- early stopping: parsed solver output with fewer than three LB rounds;
- timeout or parse failure: non-zero exit or missing summary line;
- no LB space: runs with parsed output and `lb_gain=0`;
- controller regressions: LB loss, UB regression, #OPT regression, or LB gain
  that does not convert to gap improvement.

## Literature Mapping

The related-work mapping is recorded in `LITERATURE_MAPPING.md`. Its main rule
is terminological: a single run-level arm choice is selection hyper-heuristic or
SATzilla-style per-run selection; contextual bandit naming requires repeated
decisions and explicit online reward updates.

## Probe Logging

`jobs/goSolver_stage1.py` now extracts online controller fields already printed
by the solver:

- `controller_version`, `controller_density`, `structure_blocks_aq`;
- `aq_arm`, `aq_action`, `aq_first_gap`, `aq_probe_frac`;
- `aq_slope_decision`, `dbs_lb_slope`, `aq_lb_slope`, `aq_probe_gain`,
  `aq_ub_drift`;
- `aq_guard_reason`.

These fields are written to `layer_a_runs.csv` so offline analysis can compare
DBS slope, AQ probe slope, UB drift, and the controller's final accept/reject
decision without reading raw `.out` files manually.

## Randomized Arm Logging

Generate a randomized logging plan before training any learned controller:

```bash
cd WMDS26/exp10/stage1/jobs
python3 generate_randomized_arm_plan.py \
  --datasets T1,T2,UDG,BHOSLIB,DIMACS,NDR \
  --seeds 1,2,3 \
  --reps 2 \
  --output ../sumup/randomized_arm_plan.csv
```

Then pass that plan to the Stage-1 runner:

```bash
python3 generate_scripts.py \
  --candidates v006 \
  --datasets T1,T2,UDG,BHOSLIB,DIMACS,NDR \
  --seeds 1,2,3 \
  --reps 2 \
  --cutoff 20 \
  --arm-plan ../sumup/randomized_arm_plan.csv
```

The default arms are `dbs_only`, `light_probe`, `standard_probe`,
`heavy_probe`, and `rollback_probe`. They are encoded as environment overrides
using existing solver switches, so the pilot can collect arm-conditioned logs
without changing the Ant-Q formula.

## Holdout Validation

Validate controller candidates by family and seed folds:

```bash
cd WMDS26/exp10/stage1/analysis/end
python3 validate_stage1_holdout.py \
  --result ../../sumup/result \
  --baseline-candidate v006 \
  --output stage1_holdout_validation.md
```

A fold only passes when it has positive total LB delta, negative total gap
delta, no #OPT regression, and no large UB outlier. Candidate deltas are also
reported against `v006`, because v006 is the strong hand-written controller
baseline.

## Learning Form Decision

After results exist, decide whether the evidence supports one-shot selection or
contextual bandit terminology:

```bash
cd WMDS26/exp10/stage1/analysis/end
python3 choose_learning_form.py \
  --result ../../sumup/result \
  --inspect-raw \
  --output stage1_learning_form_decision.md
```

The script checks whether the logs contain multiple arm decisions and explicit
reward/update traces. If not, the controller should be named as per-run
selection or hand-written gating, not contextual bandit.
