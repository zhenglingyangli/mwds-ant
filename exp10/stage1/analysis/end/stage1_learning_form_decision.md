# Stage 1 Learning Form Decision

- result: `result`
- runs: 300
- recommendation: `per_run_selection`
- planned_arm_rows: 300
- observed_solver_arm_rows: 0
- raw_files_inspected: 0
- runs_with_multiple_arm_decisions: 0
- runs_with_reward_update_terms: 0

## Counts

- modes: `{'arm_dbs_only_rep1': 34, 'arm_dbs_only_rep2': 31, 'arm_heavy_probe_rep1': 33, 'arm_heavy_probe_rep2': 21, 'arm_light_probe_rep1': 31, 'arm_light_probe_rep2': 37, 'arm_rollback_probe_rep1': 28, 'arm_rollback_probe_rep2': 35, 'arm_standard_probe_rep1': 24, 'arm_standard_probe_rep2': 26}`
- slope_decisions: `{'accept': 1}`
- guard_reasons: `{'dbs_mode': 43, 'no_early_lb_gain': 77, 'structure': 102}`

## Naming And Experiment Requirements

- use selection hyper-heuristic or SATzilla-style per-run selection; do not call this contextual bandit
- If per-run selection: train/evaluate DBS-only, random arm, v006, non-contextual mean/UCB, and ridge/linear selector on held-out family or seed folds.
- If contextual bandit: add multiple arm decisions per run plus explicit action reward updates before using bandit/RL terminology.
- In both cases: primary gate is negative-transfer control, not LB-only improvement.
