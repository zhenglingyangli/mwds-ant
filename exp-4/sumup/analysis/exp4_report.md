# MWDS Exp-4: Dual-Deep v6 vs Baseline Full Report

- Solvers: ['deep-v6', 'dual-deep']
- Datasets: ['T1', 'T2']
- Total rows: 4287

## 0. Data Quality & Coverage

Files lost due to fast-solving instances whose stdout was not flushed before process exit.

| Solver | Dataset | .out files | empty (0B) | header-only | parsed | lost% |
|--------|---------|-----------|------------|-------------|--------|-------|
| deep-v6 | T1 | 1080 | 0 | 0 | 1075 | 0.0% |
| deep-v6 | T2 | 1080 | 0 | 0 | 1052 | 0.0% |
| dual-deep | T1 | 1080 | 0 | 0 | 1080 | 0.0% |
| dual-deep | T2 | 1080 | 0 | 0 | 1080 | 0.0% |

> **Note**: Lost files are overwhelmingly small/easy instances (e.g. V≤100) that solve in milliseconds. These would almost certainly be optimal (gap=0). Table 1 below uses only the **common instance set** (both solvers have valid data) for fair comparison.

## 1. Gap Distribution (Table 3 Format)

- **gap\*** = per-instance best gap (min across seeds)
- **gap₀** = per-instance average gap (mean across seeds)
- Statistics computed on **common instances** only (where both solvers have valid data)

### T1

*Common instances: 525*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 1.5% | 1.5% | 1.9% | 4.4% | 26.7% |
| Paper Dual-Fast | gap₀ | 0.7% | 0.7% | 0.7% | 1.3% | 15.6% |
| **deep-v6** | gap* | **1.3% | 1.3% | 1.3% | 2.7% | 28.2%** |
| **deep-v6** | gap₀ | **1.3% | 1.3% | 1.3% | 2.7% | 27.8%** |
| dual-deep | gap* | 1.0% | 1.0% | 1.1% | 2.3% | 24.4% |
| dual-deep | gap₀ | 1.0% | 1.0% | 1.1% | 2.3% | 24.4% |

> deep-v6: 529 total instances (525 in common), seeds [1, 2] (avg 2.0 runs/inst)
> dual-deep: 528 total instances (525 in common), seeds [1, 2] (avg 2.0 runs/inst)

### T2

*Common instances: 535*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 24.6% | 24.6% | 26.9% | 34.8% | 70.4% |
| Paper Dual-Fast | gap₀ | 18.3% | 18.3% | 18.7% | 28.1% | 58.9% |
| **deep-v6** | gap* | **26.2% | 26.2% | 26.5% | 32.0% | 74.8%** |
| **deep-v6** | gap₀ | **25.8% | 25.8% | 26.4% | 32.0% | 74.2%** |
| dual-deep | gap* | 25.6% | 25.6% | 26.0% | 29.9% | 63.0% |
| dual-deep | gap₀ | 25.6% | 25.6% | 26.0% | 29.9% | 63.0% |

> deep-v6: 535 total instances (535 in common), seeds [1, 2] (avg 2.0 runs/inst)
> dual-deep: 540 total instances (535 in common), seeds [1, 2] (avg 2.0 runs/inst)

## 2. v6 vs Baseline: Pairwise Comparison

### 2.1 Gap Comparison

Per-instance avg gap across seeds. Win = v6 smaller.

| Dataset | n | v6 Win | Base Win | Tie | v6 Win% | Avg Gap v6 | Avg Gap base |
|---------|---|--------|----------|-----|---------|------------|-------------|
| T1 | 525 | 457 | 6 | 62 | 98.7% | 0.4785 | 0.6251 |
| T2 | 535 | 318 | 5 | 212 | 98.5% | 0.0613 | 0.0901 |

### 2.2 Lower Bound (LB) Comparison

Per-instance best LB (max across seeds). Win = v6 has larger LB (tighter bound).

| Dataset | n | v6 Win | Base Win | Tie | v6 Win% | Avg LB v6 | Avg LB base |
|---------|---|--------|----------|-----|---------|-----------|------------|
| T1 | 525 | 448 | 0 | 77 | 100.0% | 1457 | 1408 |
| T2 | 535 | 318 | 0 | 217 | 100.0% | 1060 | 1003 |

### 2.3 Upper Bound (UB/Solution Quality) Comparison

Per-instance best UB (min across seeds). Win = v6 has smaller UB (better solution).

| Dataset | n | v6 Win | Base Win | Tie | v6 Win% | Avg UB v6 | Avg UB base |
|---------|---|--------|----------|-----|---------|-----------|------------|
| T1 | 525 | 28 | 28 | 469 | 50.0% | 1713 | 1713 |
| T2 | 535 | 1 | 2 | 532 | 33.3% | 1166 | 1166 |

### 2.4 Gap Improvement Decomposition (Causal Analysis)

For each instance where v6 has a better gap, classify the source of improvement:
- **LB-driven**: v6 has better LB (tighter bound), same or worse UB
- **UB-driven**: v6 has better UB (better solution), same or worse LB
- **Both**: v6 improves both LB and UB
- **Neither**: gap is better but neither LB nor UB individually dominates (rounding)

| Dataset | v6 Wins | LB-driven | UB-driven | Both | Neither |
|---------|---------|-----------|-----------|------|---------|
| T1 | 457 | 425 (93%) | 6 (1%) | 22 (5%) | 4 (1%) |
| T2 | 318 | 316 (99%) | 0 (0%) | 1 (0%) | 1 (0%) |

### 2.5 Improvement by Instance Scale

Group instances by vertex count to identify where v6 gains its advantage.

| Dataset | Scale | n | v6 Win | Base Win | Tie | v6 Win% | Avg Δgap |
|---------|-------|---|--------|----------|-----|---------|----------|
| T1 | small (V≤200) | 235 | 197 | 1 | 37 | 99.5% | 0.1153 |
| T1 | medium (200<V≤500) | 190 | 170 | 1 | 19 | 99.4% | 0.1639 |
| T1 | large (V>500) | 100 | 90 | 4 | 6 | 95.7% | 0.1871 |
| T2 | small (V≤200) | 245 | 129 | 2 | 114 | 98.5% | 0.0163 |
| T2 | medium (200<V≤500) | 190 | 124 | 2 | 64 | 98.4% | 0.0292 |
| T2 | large (V>500) | 100 | 65 | 1 | 34 | 98.5% | 0.0586 |

### 2.6 Seed Consistency (Stability)

Standard deviation of gap across seeds — lower = more stable.

| Dataset | Solver | Avg Std(gap) | Med Std(gap) | Max Std(gap) |
|---------|--------|-------------|-------------|-------------|
| T1 | deep-v6 | 0.006226 | 0.002253 | 0.078183 |
| T1 | dual-deep | 0.000451 | 0.000000 | 0.017156 |
| T2 | deep-v6 | 0.001204 | 0.000000 | 0.016369 |
| T2 | dual-deep | 0.000004 | 0.000000 | 0.001046 |

### 2.7 Newly Optimal Instances

Instances where v6 proves optimality (gap*=0) but baseline does not.

**T1**: v6 #opt=7, base #opt=5, newly optimal by v6: **2**, lost: 0

| Instance | v6 gap* | Base gap* |
|----------|---------|----------|
| T1_150_150_5.wclq | 0 | 0.000673 |
| T1_50_50_3.wclq | 0 | 0.018975 |

**T2**: v6 #opt=140, base #opt=137, newly optimal by v6: **3**, lost: 0

| Instance | v6 gap* | Base gap* |
|----------|---------|----------|
| T2_100_1000_0.wclq | 0 | 0.045028 |
| T2_50_1000_4.wclq | 0 | 0.028846 |
| T2_50_750_7.wclq | 0 | 0.133333 |

## 3. Detailed Gap Statistics

| Dataset | Solver | n | Avg Gap | Med Gap | Min Gap | Max Gap |
|---------|--------|---|---------|---------|---------|--------|
| T1 | deep-v6 | 529 | 0.4784 | 0.3339 | 0.000000 | 1.6131 |
| T1 | dual-deep | 528 | 0.6262 | 0.4453 | 0.000000 | 2.0698 |
| T2 | deep-v6 | 535 | 0.0613 | 0.0382 | 0.000000 | 0.3348 |
| T2 | dual-deep | 540 | 0.0895 | 0.0466 | 0.000000 | 0.4677 |

## 4. Gap Convergence Over Time

Average gap* at each checkpoint (per-instance min across seeds).

| Dataset | Solver | 10s | 1min | 5min | 10min | 30min | 60min | final |
|---------|--------|------|------|------|------|------|------|-------|
| T1 | deep-v6 | 0.4829 | 0.4829 | 0.4839 | 0.4849 | 0.4849 | 0.1304 | 0.4722 |
| T1 | dual-deep | 0.0018 | 0.0018 | 0.0008 | 0.0008 | 0.0007 | 0.0007 | 0.6257 |
| T2 | deep-v6 | 0.0777 | 0.0789 | 0.0793 | 0.0798 | 0.0804 | 0.0145 | 0.0602 |
| T2 | dual-deep | 0.0032 | 0.0032 | 0.0031 | 0.0032 | 0.0032 | 0.0034 | 0.0895 |

## 5. Instance Difficulty Breakdown

Distribution of instances by gap range (gap* metric).

### T1

| Gap Range | deep-v6 | dual-deep |
|-----------|------|------|
| optimal (gap=0) | 7 (1.3%) | 5 (0.9%) |
| near-opt (0 < gap ≤ 10⁻³) | 0 (0.0%) | 1 (0.2%) |
| small (10⁻³ < gap ≤ 10⁻²) | 7 (1.3%) | 6 (1.1%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 134 (25.3%) | 116 (22.0%) |
| large (gap > 10⁻¹) | 381 (72.0%) | 400 (75.8%) |

### T2

| Gap Range | deep-v6 | dual-deep |
|-----------|------|------|
| optimal (gap=0) | 140 (26.2%) | 137 (25.4%) |
| near-opt (0 < gap ≤ 10⁻³) | 2 (0.4%) | 2 (0.4%) |
| small (10⁻³ < gap ≤ 10⁻²) | 29 (5.4%) | 21 (3.9%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 229 (42.8%) | 182 (33.7%) |
| large (gap > 10⁻¹) | 135 (25.2%) | 198 (36.7%) |


---
*Generated by sumup.py (exp-4)*
