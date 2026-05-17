# exp-9: LB-first Algorithm Repair

exp-9 回到最初目标：

1. 提高 `best_lb`
2. 减小 final `gap`
3. 最终提高 `#OPT`

exp-8 暴露的问题是：T1/T2 的 LB tightening 能生效，但 UDG/BHOSLIB/DIMACS/SNAP 上大量实例 `first_lb == best_lb`，说明 LB-search 没有持续探索或没有找到更好的 bound ordering。exp-9 不做论文叙事，专门修算法。

## 算法改动

### 1. 取消假 OPTIMAL 早停

旧逻辑把 no-replacement/no-loss ordering 当成 OPTIMAL：

```cpp
if ((rep_flag == 0 && loss_sum == 0) || (BEST_UPPER_BOUND == BEST_LOWER_BOUND))
    OPTIMAL = 1;
```

exp-9 改为只有 `BEST_UPPER_BOUND == BEST_LOWER_BOUND` 才终止 LB-search。原因是 BHOSLIB/UDG/DIMACS 上经常出现 `LB < UB` 但 no-replacement/no-loss 的状态，继续 Beta/AQ 轮次仍可能提升 LB。

### 2. deep-v6 改成 LB-first tiered search

deep-v6 不再在第一次 LB warmup 后把全部剩余时间交给 UB local search。新策略按 `FIRST_GAP` 和 density 分层：

- Tier-1 easy: gap 很小且低密度，不做额外 LB warmup。
- Tier-2 medium: 标准 LB warmup，最多 15% cutoff。
- Tier-3 hard: 强 LB warmup，`K >= 8`、`rho = 0.08`、最多 25% cutoff。

之后 UB local search 只拿一个小 time slice，给后续 `ibmwds_init_bounds()` 留时间，目标是持续交替推动 LB 和 UB。

### 3. dense 图也允许 advanced/AQ feedback

exp-8 的 deep-v6 在 `density > 15` 时关闭 `USE_ADVANCED`，导致 BHOSLIB/DIMACS 基本没有 learned feedback。exp-9 对 `NB_NODE >= 800 || density >= 50` 开启 advanced feedback。

### 4. 通用 bounded-cost exact check

hard dense 图上，单纯增加 K 或降低 q0 仍可能推不动 LB，因为 greedy dual packing 的表达能力有限。exp-9 增加一个不依赖数据集名的精确检查：

- 仅使用运行时图结构和节点权重。
- 在规模可控时枚举所有 1 点/2 点 dominating set。
- 如果找到更低成本支配解，直接更新 UB。
- 如果证明不存在 cost <= 2 的支配解，则合法推出 `LB >= 3`。

这个机制服务于最初目标：`LB ↑`、`gap ↓`、`#OPT ↑`。例如本地 `frb50-23-3` 在该机制下可快速得到 `LB = UB = 3`。

## 数据集

8 datasets × 5 selected instances × 5 seeds：

- T1
- T2
- UDG
- BHOSLIB
- DIMACS
- DIMACS10
- NDR
- SNAP

## 运行

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
git pull origin main

# 只做 preflight：检查路径、编译、smoke test、生成 80 个 SLURM 脚本
bash exp-9/run_on_hpc.sh --no-submit

# 全量提交
bash exp-9/run_on_hpc.sh
```

## 汇总

```bash
cd exp-9/deep-v6/sumup
python3 sumup_lb.py ../jobs/result

cd ../../fast-v19/sumup
python3 sumup_lb.py ../jobs/result
```

核心观察指标：

- per-run `best_lb - first_lb`
- per-instance `best_lb_max`
- final gap
- `status == OPT`
- 与 exp-8 同实例同 seed 的 delta
