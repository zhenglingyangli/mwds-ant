# MWDS Exp-2: Dual-Fast v19 vs Baseline Full Report

- Solvers: ['dual-fast', 'fast-v19']
- Datasets: ['T1', 'T2']
- Total rows: 17832

## 0. Data Quality & Coverage

Files lost due to fast-solving instances whose stdout was not flushed before process exit.

| Solver | Dataset | .out files | empty (0B) | header-only | parsed | lost% |
|--------|---------|-----------|------------|-------------|--------|-------|
| dual-fast | T1 | 6280 | 13 | 8 | 6184 | 0.3% |
| dual-fast | T2 | 5400 | 252 | 242 | 4650 | 9.1% |
| fast-v19 | T1 | 5400 | 24 | 31 | 4300 | 1.0% |
| fast-v19 | T2 | 5400 | 451 | 320 | 3545 | 14.3% |

> **Note**: Lost files are overwhelmingly small/easy instances (e.g. V≤100) that solve in milliseconds. These would almost certainly be optimal (gap=0). Table 1 below uses only the **common instance set** (both solvers have valid data) for fair comparison.

## 1. Gap Distribution (Table 3 Format)

- **gap\*** = per-instance best gap (min across seeds)
- **gap₀** = per-instance average gap (mean across seeds)
- Statistics computed on **common instances** only (where both solvers have valid data)

### T1

*Common instances: 539*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 1.5% | 1.5% | 1.9% | 4.4% | 26.7% |
| Paper Dual-Fast | gap₀ | 0.7% | 0.7% | 0.7% | 1.3% | 15.6% |
| dual-fast | gap* | 3.2% | 3.2% | 3.2% | 7.1% | 27.6% |
| dual-fast | gap₀ | 3.0% | 3.0% | 3.0% | 5.8% | 27.1% |
| **fast-v19** | gap* | **0.9% | 0.9% | 1.3% | 3.5% | 28.4%** |
| **fast-v19** | gap₀ | **0.9% | 0.9% | 0.9% | 3.2% | 28.0%** |

> dual-fast: 540 total instances (539 in common), seeds [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] (avg 9.9 runs/inst)
> fast-v19: 539 total instances (539 in common), seeds [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] (avg 8.0 runs/inst)

### T2

*Common instances: 513*

| Solver | metric | #opt | ≤10⁻⁴ | ≤10⁻³ | ≤10⁻² | ≤10⁻¹ |
|--------|--------|------|--------|--------|--------|--------|
| Paper Dual-Fast | gap* | 24.6% | 24.6% | 26.9% | 34.8% | 70.4% |
| Paper Dual-Fast | gap₀ | 18.3% | 18.3% | 18.7% | 28.1% | 58.9% |
| dual-fast | gap* | 23.2% | 23.2% | 23.8% | 33.3% | 71.3% |
| dual-fast | gap₀ | 22.8% | 22.8% | 23.4% | 32.9% | 70.4% |
| **fast-v19** | gap* | **17.7% | 17.7% | 18.7% | 30.6% | 77.2%** |
| **fast-v19** | gap₀ | **17.3% | 17.3% | 18.5% | 30.0% | 75.8%** |

> dual-fast: 534 total instances (513 in common), seeds [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] (avg 8.7 runs/inst)
> fast-v19: 515 total instances (513 in common), seeds [1, 2, 3, 4, 5, 6, 7, 8, 9, 10] (avg 6.9 runs/inst)

## 2. v19 vs Baseline: Pairwise Comparison

### 2.1 Gap Comparison

Per-instance avg gap across seeds. Win = v19 smaller.

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg Gap v19 | Avg Gap base |
|---------|---|---------|----------|-----|----------|-------------|-------------|
| T1 | 539 | 400 | 117 | 22 | 77.4% | 0.4521 | 0.5152 |
| T2 | 513 | 251 | 142 | 120 | 63.9% | 0.0602 | 0.0683 |

### 2.2 Lower Bound (LB) Comparison

Per-instance best LB (max across seeds). Win = v19 has larger LB (tighter bound).

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg LB v19 | Avg LB base |
|---------|---|---------|----------|-----|----------|------------|------------|
| T1 | 539 | 403 | 106 | 30 | 79.2% | 1431 | 1426 |
| T2 | 513 | 246 | 116 | 151 | 68.0% | 1103 | 1085 |

### 2.3 Upper Bound (UB/Solution Quality) Comparison

Per-instance best UB (min across seeds). Win = v19 has smaller UB (better solution).

| Dataset | n | v19 Win | Base Win | Tie | v19 Win% | Avg UB v19 | Avg UB base |
|---------|---|---------|----------|-----|----------|------------|------------|
| T1 | 539 | 7 | 28 | 504 | 20.0% | 1671 | 1671 |
| T2 | 513 | 0 | 7 | 506 | 0.0% | 1209 | 1209 |

### 2.4 Gap Improvement Decomposition (Causal Analysis)

For each instance where v19 has a better gap, classify the source of improvement:
- **LB-driven**: v19 has better LB (tighter bound), same or worse UB
- **UB-driven**: v19 has better UB (better solution), same or worse LB
- **Both**: v19 improves both LB and UB
- **Neither**: gap is better but neither LB nor UB individually dominates (rounding)

| Dataset | v19 Wins | LB-driven | UB-driven | Both | Neither |
|---------|----------|-----------|-----------|------|---------|
| T1 | 400 | 390 (98%) | 1 (0%) | 4 (1%) | 5 (1%) |
| T2 | 251 | 243 (97%) | 0 (0%) | 0 (0%) | 8 (3%) |

### 2.5 Improvement by Instance Scale

Group instances by vertex count to identify where v19 gains its advantage.

| Dataset | Scale | n | v19 Win | Base Win | Tie | v19 Win% | Avg Δgap |
|---------|-------|---|---------|----------|-----|----------|----------|
| T1 | small (V≤200) | 233 | 181 | 31 | 21 | 85.4% | 0.0595 |
| T1 | medium (200<V≤500) | 158 | 146 | 12 | 0 | 92.4% | 0.0896 |
| T1 | large (V>500) | 99 | 70 | 29 | 0 | 70.7% | 0.0666 |
| T2 | small (V≤200) | 228 | 107 | 41 | 80 | 72.3% | 0.0055 |
| T2 | medium (200<V≤500) | 179 | 88 | 71 | 20 | 55.3% | 0.0082 |
| T2 | large (V>500) | 98 | 55 | 29 | 14 | 65.5% | 0.0145 |

### 2.6 Seed Consistency (Stability)

Standard deviation of gap across seeds — lower = more stable.

| Dataset | Solver | Avg Std(gap) | Med Std(gap) | Max Std(gap) |
|---------|--------|-------------|-------------|-------------|
| T1 | dual-fast | 0.005900 | 0.002314 | 0.045457 |
| T1 | fast-v19 | 0.006576 | 0.003090 | 0.092361 |
| T2 | dual-fast | 0.000720 | 0.000000 | 0.008892 |
| T2 | fast-v19 | 0.001496 | 0.000924 | 0.043112 |

### 2.7 Newly Optimal Instances

Instances where v19 proves optimality (gap*=0) but baseline does not.

**T1**: v19 #opt=5, base #opt=17, newly optimal by v19: **0**, lost: 12

**T2**: v19 #opt=91, base #opt=119, newly optimal by v19: **2**, lost: 30

| Instance | v19 gap* | Base gap* |
|----------|----------|----------|
| T2_100_1000_0.wclq | 0 | 0.009058 |
| T2_50_500_2.wclq | 0 | 0.019608 |

## 3. Detailed Gap Statistics

| Dataset | Solver | n | Avg Gap | Med Gap | Min Gap | Max Gap |
|---------|--------|---|---------|---------|---------|--------|
| T1 | dual-fast | 540 | 0.5160 | 0.3710 | 0.000000 | 1.6884 |
| T1 | fast-v19 | 539 | 0.4521 | 0.3233 | 0.000000 | 1.5238 |
| T2 | dual-fast | 534 | 0.0656 | 0.0335 | 0.000000 | 0.3946 |
| T2 | fast-v19 | 515 | 0.0600 | 0.0379 | 0.000000 | 0.3199 |

## 4. Gap Convergence Over Time

Average gap* at each checkpoint (per-instance min across seeds).

| Dataset | Solver | 10s | 1min | 5min | 10min | 30min | 60min | final |
|---------|--------|------|------|------|------|------|------|-------|
| T1 | dual-fast | 0.5466 | 0.5310 | 0.5336 | 0.5512 | 0.4816 | - | 0.5058 |
| T1 | fast-v19 | 0.4451 | 0.4451 | 0.4451 | 0.4455 | 0.4306 | - | 0.4420 |
| T2 | dual-fast | 0.0951 | 0.0908 | 0.0879 | 0.0881 | 0.0796 | - | 0.0645 |
| T2 | fast-v19 | 0.0719 | 0.0724 | 0.0743 | 0.0741 | 0.0665 | 0.0708 | 0.0579 |

## 5. Instance Difficulty Breakdown

Distribution of instances by gap range (gap* metric).

### T1

| Gap Range | dual-fast | fast-v19 |
|-----------|------|------|
| optimal (gap=0) | 17 (3.1%) | 5 (0.9%) |
| near-opt (0 < gap ≤ 10⁻³) | 0 (0.0%) | 2 (0.4%) |
| small (10⁻³ < gap ≤ 10⁻²) | 21 (3.9%) | 12 (2.2%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 111 (20.6%) | 134 (24.9%) |
| large (gap > 10⁻¹) | 391 (72.4%) | 386 (71.6%) |

### T2

| Gap Range | dual-fast | fast-v19 |
|-----------|------|------|
| optimal (gap=0) | 140 (26.2%) | 92 (17.9%) |
| near-opt (0 < gap ≤ 10⁻³) | 3 (0.6%) | 5 (1.0%) |
| small (10⁻³ < gap ≤ 10⁻²) | 49 (9.2%) | 61 (11.8%) |
| medium (10⁻² < gap ≤ 10⁻¹) | 195 (36.5%) | 240 (46.6%) |
| large (gap > 10⁻¹) | 147 (27.5%) | 117 (22.7%) |


---
*Generated by sumup.py (exp-2)*
