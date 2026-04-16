> 20260415

## Dual-Deep v6 vs Baseline 全量实验 (复现论文配置)

### 实验设置
- **求解器**: Dual-Deep (baseline) + Dual-Deep-v6
- **cutoff**: 3600s (与论文一致)
- **seeds**: 10 (seed 1..10，与论文一致)
- **并行**: 10 核/job
- **alpha**: 1
- **内存**: 64G/job

### 数据集

| 数据集 | 实例数 | 超算路径 |
|--------|--------|----------|
| T1 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq` |
| T2 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T2_wclq` |

### SLURM 分块策略
- 按 55 实例/块分割，每块 × 1 seed × 1 solver = 1 个 SLURM job
- 2 solvers × 2 datasets × 10 chunks × 10 seeds = **400 SLURM jobs**
- 单个 job 最长 ~5.5h walltime
- 使用 auto_submit.sh 自动分批提交（每次最多 50 个）

### 分析报告 (sumup.py)
1. Gap Distribution (论文 Table 3 格式)
2. v6 vs Baseline 逐实例对比
   - 2.1 Gap / 2.2 LB / 2.3 UB 对比 (Win/Loss/Tie)
   - 2.4 Gap 改进因果分解 (LB-driven / UB-driven / Both)
   - 2.5 按实例规模分组
   - 2.6 Seed 稳定性
   - 2.7 新增最优实例
3. 详细 Gap 统计
4. Gap 收敛曲线
5. 实例难度分布
