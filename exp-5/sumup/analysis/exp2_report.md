# MWDS Exp-2: Dual-Fast v19 vs Baseline Full Report

- Solvers: ['dual-fast', 'fast-v19']
- Datasets: ['T1', 'T2']
- Total rows: 4319

## 0. Data Quality & Coverage

Files lost due to fast-solving instances whose stdout was not flushed before process exit.

| Solver | Dataset | .out files | empty (0B) | header-only | parsed | lost% |
|--------|---------|-----------|------------|-------------|--------|-------|
| dual-fast | T1 | 1080 | 0 | 0 | 1080 | 0.0% |
| dual-fast | T2 | 1080 | 0 | 0 | 1080 | 0.0% |
| fast-v19 | T1 | 1080 | 0 | 0 | 1080 | 0.0% |
| fast-v19 | T2 | 1080 | 0 | 0 | 1079 | 0.0% |

> **Note**: Lost files are overwhelmingly small/easy instances (e.g. V≤100) that solve in milliseconds. These would almost certainly be optimal (gap=0). Table 1 below uses only the **common instance set** (both solvers have valid data) for fair comparison.

## 1. Gap Distribution (Table 3 Format)

- **gap\*** = per-instance best gap (min across seeds)
- **gap₀** = per-instance average gap (mean across seeds)
- Statistics computed on **common instances** only (where both solvers have valid data)

### T1

*Common instances: 540*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 1.5% | 1.5% | 1.9% | 4.4% | 26.7% |
| Paper Dual-Fast | gap₀ | 0.7% | 0.7% | 0.7% | 1.3% | 15.6% |
| dual-fast | gap* | 3.3% | 3.3% | 3.3% | 7.4% | 26.9% |
| dual-fast | gap₀ | 3.0% | 3.0% | 3.1% | 7.0% | 26.7% |
| **fast-v19** | gap* | **1.1% | 1.1% | 1.3% | 3.0% | 27.2%** |
| **fast-v19** | gap₀ | **0.9% | 0.9% | 1.1% | 3.0% | 27.2%** |

> dual-fast: 540 total instances (540 in common), seeds [1, 2] (avg 2.0 runs/inst)
> fast-v19: 540 total instances (540 in common), seeds [1, 2] (avg 2.0 runs/inst)

### T2

*Common instances: 540*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 24.6% | 24.6% | 26.9% | 34.8% | 70.4% |
| Paper Dual-Fast | gap₀ | 18.3% | 18.3% | 18.7% | 28.1% | 58.9% |
| dual-fast | gap* | 27.0% | 27.0% | 27.4% | 35.6% | 71.5% |
| dual-fast | gap₀ | 26.7% | 26.7% | 27.4% | 35.4% | 70.9% |
| **fast-v19** | gap* | **21.3% | 21.3% | 22.2% | 33.5% | 76.1%** |
| **fast-v19** | gap₀ | **21.1% | 21.1% | 22.0% | 33.0% | 75.2%** |

> dual-fast: 540 total instances (540 in common), seeds [1, 2] (avg 2.0 runs/inst)
> fast-v19: 540 total instances (540 in common), seeds [1, 2] (avg 2.0 runs/inst)

## 2. v19 vs Baseline: Pairwise Comparison

### 2.1 Gap Comparison

Per-instance avg gap across seeds. Win = v19 smaller.

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg Gap v19 | Avg Gap base |
|---------|---|---------|----------|-----|----------|-------------|-------------|
| T1 | 540 | 326 | 185 | 29 | 63.8% | 0.4805 | 0.5163 |
| T2 | 540 | 244 | 146 | 150 | 62.6% | 0.0604 | 0.0671 |

### 2.2 Lower Bound (LB) Comparison

Per-instance best LB (max across seeds). Win = v19 has larger LB (tighter bound).

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg LB v19 | Avg LB base |
|---------|---|---------|----------|-----|----------|------------|------------|
| T1 | 540 | 341 | 158 | 41 | 68.3% | 1424 | 1425 |
| T2 | 540 | 245 | 134 | 161 | 64.6% | 1053 | 1040 |

### 2.3 Upper Bound (UB/Solution Quality) Comparison

Per-instance best UB (min across seeds). Win = v19 has smaller UB (better solution).

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg UB v19 | Avg UB base |
|---------|---|---------|----------|-----|----------|------------|------------|
| T1 | 540 | 36 | 46 | 458 | 43.9% | 1669 | 1668 |
| T2 | 540 | 3 | 8 | 529 | 27.3% | 1158 | 1158 |

### 2.4 Gap Improvement Decomposition (Causal Analysis)

For each instance where v19 has a better gap, classify the source of improvement:
- **LB-driven**: v19 has better LB (tighter bound), same or worse UB
- **UB-driven**: v19 has better UB (better solution), same or worse LB
- **Both**: v19 improves both LB and UB
- **Neither**: gap is better but neither LB nor UB individually dominates (rounding)

| Dataset | v19 Wins | LB-driven | UB-driven | Both | Neither |
|---------|----------|-----------|-----------|------|---------|
| T1 | 326 | 293 (90%) | 0 (0%) | 31 (10%) | 2 (1%) |
| T2 | 244 | 236 (97%) | 0 (0%) | 2 (1%) | 6 (2%) |

### 2.5 Improvement by Instance Scale

Group instances by vertex count to identify where v19 gains its advantage.

| Dataset | Scale | n | v19 Win | Base Win | Tie | v19 Win% | Avg Δgap |
|---------|-------|---|---------|----------|-----|----------|----------|
| T1 | small (V≤200) | 191 | 120 | 50 | 21 | 70.6% | 0.0430 |
| T1 | medium (200<V≤500) | 160 | 135 | 25 | 0 | 84.4% | 0.0673 |
| T1 | large (V>500) | 100 | 67 | 33 | 0 | 67.0% | 0.0528 |
| T2 | small (V≤200) | 231 | 101 | 37 | 93 | 73.2% | 0.0062 |
| T2 | medium (200<V≤500) | 185 | 86 | 68 | 31 | 55.8% | 0.0073 |
| T2 | large (V>500) | 100 | 53 | 31 | 16 | 63.1% | 0.0102 |

### 2.6 Seed Consistency (Stability)

Standard deviation of gap across seeds — lower = more stable.

| Dataset | Solver | Avg Std(gap) | Med Std(gap) | Max Std(gap) |
|---------|--------|-------------|-------------|-------------|
| T1 | dual-fast | 0.006350 | 0.001227 | 0.131661 |
| T1 | fast-v19 | 0.008340 | 0.001381 | 0.422178 |
| T2 | dual-fast | 0.000746 | 0.000000 | 0.010337 |
| T2 | fast-v19 | 0.001669 | 0.000000 | 0.090761 |

### 2.7 Newly Optimal Instances

Instances where v19 proves optimality (gap*=0) but baseline does not.

**T1**: v19 #opt=6, base #opt=18, newly optimal by v19: **0**, lost: 12

**T2**: v19 #opt=115, base #opt=146, newly optimal by v19: **3**, lost: 34

| Instance | v19 gap* | Base gap* |
|----------|----------|----------|
| T2_100_1000_0.wclq | 0 | 0.018282 |
| T2_50_100_1.wclq | 0 | 0.031250 |
| T2_50_500_2.wclq | 0 | 0.019608 |

## 3. Detailed Gap Statistics

| Dataset | Solver | n | Avg Gap | Med Gap | Min Gap | Max Gap |
|---------|--------|---|---------|---------|---------|--------|
| T1 | dual-fast | 540 | 0.5163 | 0.3869 | 0.000000 | 1.6867 |
| T1 | fast-v19 | 540 | 0.4805 | 0.3694 | 0.000000 | 1.5814 |
| T2 | dual-fast | 540 | 0.0671 | 0.0346 | 0.000000 | 0.4635 |
| T2 | fast-v19 | 540 | 0.0604 | 0.0347 | 0.000000 | 0.4635 |

## 4. Gap Convergence Over Time

Average gap* at each checkpoint (per-instance min across seeds).

| Dataset | Solver | 10s | 1min | 5min | 10min | 30min | 60min | final |
|---------|--------|------|------|------|------|------|------|-------|
| T1 | dual-fast | 0.5300 | 0.5207 | 0.2408 | 0.1553 | 0.1721 | - | 0.5099 |
| T1 | fast-v19 | 0.4483 | 0.4485 | 0.4485 | 0.4508 | 0.3584 | - | 0.4722 |
| T2 | dual-fast | 0.0915 | 0.0905 | 0.0795 | 0.0659 | 0.0516 | - | 0.0663 |
| T2 | fast-v19 | 0.0723 | 0.0725 | 0.0734 | 0.0739 | 0.0427 | - | 0.0588 |

## 5. Instance Difficulty Breakdown

Distribution of instances by gap range (gap* metric).

### T1

| Gap Range | dual-fast | fast-v19 |
|-----------|------|------|
| optimal (gap=0) | 18 (3.3%) | 6 (1.1%) |
| near-opt (0 < gap ≤ 10⁻³) | 0 (0.0%) | 1 (0.2%) |
| small (10⁻³ < gap ≤ 10⁻²) | 22 (4.1%) | 9 (1.7%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 105 (19.4%) | 131 (24.3%) |
| large (gap > 10⁻¹) | 395 (73.1%) | 393 (72.8%) |

### T2

| Gap Range | dual-fast | fast-v19 |
|-----------|------|------|
| optimal (gap=0) | 146 (27.0%) | 115 (21.3%) |
| near-opt (0 < gap ≤ 10⁻³) | 2 (0.4%) | 5 (0.9%) |
| small (10⁻³ < gap ≤ 10⁻²) | 44 (8.1%) | 61 (11.3%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 194 (35.9%) | 230 (42.6%) |
| large (gap > 10⁻¹) | 154 (28.5%) | 129 (23.9%) |


---
*Generated by sumup.py (exp-2)*
