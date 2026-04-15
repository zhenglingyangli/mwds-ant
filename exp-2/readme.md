> 20260414

## Dual-Fast v19 vs Baseline 全量实验 (复现论文配置)

### 实验设置
- **求解器**: Dual-Fast (baseline) + Dual-Fast-v19
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

### 分析报告 (sumup.py)


【20260414 21：05 发送】
【4.15收dual-fast-v19结果】
【不好，一次200个有点害怕， auto_submit.sh，现在改成每次最多 50 个。估计要个两三天...】

【最好今天能把dual-deep的版本测试完】