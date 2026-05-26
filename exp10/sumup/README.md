# exp10 Sumup

本目录暂时只放说明。

`exp10` 的全量结果解析不应复用 `exp-4/sumup/sumup.py` 的固定 `deep-v6 vs dual-deep` 口径，也不应复用 `exp-8/sumup/sumup_lb.py` 的 historical-baseline 口径。

后续需要新增一个 Layer-A-only summarizer，输入：

```text
exp10/jobs/result/
```

输出：

```text
analysis/layer_a_runs.csv
analysis/layer_a_fair_summary.csv
analysis/layer_a_fair_aggregate.csv
analysis/per_family_summary.csv
analysis/outlier_report.md
```

核心组合规则：

```text
method_best_lb = max(best_lb across k calls)
method_best_ub = min(best_ub/verified_ub across k calls)
method_gap = method_best_ub - method_best_lb
method_solver_opt = (method_gap == 0)
```

Stage 1 的统一筛选与严格检查代码位于：

```text
exp10/stage1/jobs/goSolver_stage1.py
exp10/stage1/analysis/end/check_results.py
exp10/stage1/sumup/run_sumup.sh
```

这些脚本只比较 DBS-only 与 DBS + adaptive ACO-style controller，不引入外部 LP/MILP certificate 字段。

