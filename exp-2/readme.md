> 20260413

## Dual-Fast v19 全量实验 (复现论文配置)

### 实验设置
- **求解器**: Dual-Fast-v19 (单一版本，与论文 Table 3 的 Dual-Fast 原版对比)
- **cutoff**: 3600s (与论文一致)
- **seeds**: 10 (seed 1..10，与论文一致)
- **并行**: 10 核/job
- **alpha**: 1

### 数据集选择

| 数据集 | 实例数 | 超算路径 | 选择理由 |
|--------|--------|----------|----------|
| T1 | 540 | `standard_wclq/T1_wclq` | 最难基准，原版仅 26.7% gap≤0.1，改进空间大 |
| T2 | 540 | `standard_wclq/T2_wclq` | 中等难度，展示收敛速度优势 |
| UDG | 120 | `standard_wclq/UDG_wclq` | 简单基准，验证"无退化"，运行成本极低 |

> 如果超算上有 Real-World 数据 (NDR/65, DIMACS10/31)，强烈建议加入：
> NDR 的 LB 改进潜力最大 (6.2%→80%)，最能体现 v19 的核心优势。

### SLURM 分块策略
- 大数据集 (T1/T2) 按 ~55 实例分块，每块 × 1 seed = 1 个 SLURM job
- T1: 10 chunks × 10 seeds = 100 jobs (~5.5h/job)
- T2: 10 chunks × 10 seeds = 100 jobs (~5.5h/job)
- UDG: 2 chunks × 10 seeds = 20 jobs (~2.2h/job)
- 总计: ~220 SLURM jobs
- 使用 goSolver.py --name_list 选择实例子集

### 结果对比
- 使用与论文 Table 3 完全相同的指标：
  - gap* = 每个实例在所有 seed 中的最佳 gap (min)
  - gap_0 = 每个实例在所有 seed 中的平均 gap (mean)
  - 阈值: #opt, ≤10⁻⁴, ≤10⁻³, ≤10⁻², ≤10⁻¹
- gap 定义: (UB - LB) / LB (统一)
