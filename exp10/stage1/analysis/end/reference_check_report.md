# Stage 1 Reference Check

- selected: v006 (controller) from result/v006
- reference_root: reference_result
- references: reference,baseline
- reference_mode: dbs
- datasets: BHOSLIB,DIMACS,NDR,T1,T2,UDG

## v006 vs reference

Summary:
- deep-v6: rows=75, total_delta_lb=-35, total_delta_gap=23, lb_wins/ties/losses=13/51/11, gap_wins/ties/losses=20/44/11, max_ub_regression=2
- fast-v19: rows=75, total_delta_lb=-296, total_delta_gap=295, lb_wins/ties/losses=3/58/14, gap_wins/ties/losses=4/55/16, max_ub_regression=2

## v006 vs baseline

Summary:
- deep-v6: rows=75, total_delta_lb=2636, total_delta_gap=-2625, lb_wins/ties/losses=24/51/0, gap_wins/ties/losses=24/51/0, max_ub_regression=8
- fast-v19: rows=75, total_delta_lb=-374, total_delta_gap=-27670116110564327044, lb_wins/ties/losses=6/54/15, gap_wins/ties/losses=9/51/15, max_ub_regression=5

## Warnings
- none

## Result
- FAILURE: v006 vs reference/deep-v6: total_delta_lb <= 0 (-35)
- FAILURE: v006 vs reference/deep-v6: total_delta_gap >= 0 (23)
- FAILURE: v006 vs reference/fast-v19: total_delta_lb <= 0 (-296)
- FAILURE: v006 vs reference/fast-v19: total_delta_gap >= 0 (295)
- FAILURE: v006 vs baseline/fast-v19: total_delta_lb <= 0 (-374)

