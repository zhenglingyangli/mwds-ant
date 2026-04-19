# exp-4: Dual-Deep v6 vs Baseline（论文配置 / 2 seeds）

> **状态**：READY TO RUN（exp-6 + 本地 300s 补测已确认 v6/v10 等价，沿用 exp-3 选型的 v6）
> 20260419 — alpha=90 + cutoff=3600s 对齐论文，seeds=1,2 轻量化

## 实验设置

- **求解器**: `dual-deep` (baseline) + `dual-deep-v6`
- **cutoff**: **3600 s**（论文 ECAI-2025 Table 3 设置）
- **seeds**: **`1, 2`**（论文用 10，这里为控制 wall-time 改 2；数据已够支撑 pairwise 判优劣）
- **alpha**: **90** （solver 内部 ALPHA=1.90；**千万不要写 1**——那是 ALPHA=1.01 完全不同的算法）
- **并行**: `PARALLEL=10` 核/job，`--cutoff_mem 16GB/实例`
- **内存**: SLURM `--mem=64G`/job
- **partition**: `hfacnormal01`

## 数据集

| 数据集 | 实例数 | 超算路径 |
|--------|--------|----------|
| T1 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq` |
| T2 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T2_wclq` |

## 规模与资源

| 项 | 数值 |
|---|---|
| 实例数 | 540 (T1) + 540 (T2) = **1080** |
| 组合 | 2 solvers × 1080 inst × 2 seeds = **4320 runs** |
| Jobs | 2 solvers × 2 datasets × 10 chunks × 2 seeds = **80 jobs** |
| 单 job walltime 上限 | 55 × 3600 / 10 = **5.5 h**（小图 <1s OPT 实际更快）|
| CPU-hours 总计 | 4320 × 3600 / 10 / 3600 ≈ **432** |
| 单 job SLURM `--time` | `0-08:00:00` |
| 并发节流 | 队列最多 **50 个**同时在跑（`auto_submit.sh` 的 `BATCH_SIZE=50`）|

---

## 跑法（分批提交，每次最多 50 个在队列）

```bash
# 在超算 /public/home/acs4vb4pqv/ylzl/MWDS-Ant 下
git pull origin main

# 1) 编译（exp-4 自带 codes/）
cd exp-4/codes/Dual-Deep    && make && [ -x dual-deep ]    || { echo "baseline 编译失败"; exit 1; }
cd ../Dual-Deep-v6          && make && [ -x dual-deep-v6 ] || { echo "v6 编译失败";      exit 1; }

# 2) 生成 80 个 jobslurm-*
cd ../../jobs
python3 generate_scripts.py         # 默认 seeds=[1,2]

# 3) 后台分批提交：队列里最多常驻 50，每 5 分钟补到 50
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
tail -f auto_submit.log             # Ctrl-C 不会中断后台任务

# 监控
squeue -u $USER -h | wc -l          # 应 ≤ 50
squeue -u $USER -h -o "%T" | sort | uniq -c
```

---

## 补跑丢的实例（如有）

```bash
python3 generate_patch.py ./result
bash submit_patch.sh
```

只会为**缺失或不完整**的 `(solver, dataset, seed, instance)` 生成脚本，已完成的不会重跑。

---

## 关键代码修复（继承自 exp-2 踩坑）

| 文件 | 修复点 | 位置 |
|---|---|---|
| `goSolver.py` | stdout 丢数据 bug：`output_monitor` 只在真正 EOF 时 break，每行 flush | line 92-111 |
| `goSolver.py` | 主线程先 `output_thread.join(timeout=5)` 再 `stop_event.set()` | line 191-205 |
| `sumup.py` | TIMEOUT/MEMOUT 时从每轮中间数据恢复 best_lb/best_ub | line 136+ |
| `sumup.py` | 去重按 timestamp 取最早（不是 gap 最小），消除重复提交偏差 | line 795-801 |
| `sumup.py` | 目录名正则同时提取 seed 和 timestamp | line 168-194 |

---

## Pre-flight Checklist（超算上跑前必查）

```bash
# 在超算 /public/home/acs4vb4pqv/ylzl/MWDS-Ant 下：

# 1) SSH & 拉最新代码
ssh -T git@github.com 2>&1 | grep -q "successfully authenticated" \
    || { echo "SSH 未配；参考 exp-2 readme 配 SSH key"; exit 1; }
git pull origin main

# 2) 编译两个求解器（没有 clean 目标，直接 make）
cd exp-4/codes/Dual-Deep && make && [ -x dual-deep ] || { echo "baseline 编译失败"; exit 1; }
cd ../Dual-Deep-v6       && make && [ -x dual-deep-v6 ] || { echo "v6 编译失败";   exit 1; }

# 3) 确认关键修复还在
cd ../../jobs
grep -q "output_thread.join" goSolver.py    || { echo "goSolver stdout 修复缺失"; exit 1; }
grep -q "first_seen"         ../sumup/sumup.py \
    || { echo "sumup 去重修复缺失"; exit 1; }

# 4) 集群资源
squeue -u $USER | wc -l                     # 应 = 1（仅表头）
sinfo -p hfacnormal01 -t idle,mix --noheader | awk '{s+=$4} END{print s}'   # 可用节点

# 5) 参数核对
#    CUTOFF=3600, ALPHA=90 (!!! 千万不是 1 !!!), PARALLEL=10, MEM=64G, partition=hfacnormal01
grep -E "^CUTOFF|^ALPHA|^PARALLEL|^SLURM_MEM|^SLURM_PARTITION" generate_scripts.py
# 再和论文原始脚本比对一下：
grep ALPHA /home/ylzl/Ant-QO/code/Dual-Deep/README        # 应看到 `./dual-deep ... 90`
grep ALPHA /home/ylzl/Ant-QO/experiment-*/exp-*/run_goSolver.sh 2>/dev/null  # 全是 ALPHA=90
```

---

## 分析报告 (sumup.py)

1. Gap Distribution（论文 Table 3 格式，5 个阈值档）
2. v6 vs Baseline 逐实例对比
   - 2.1 Gap / 2.2 LB / 2.3 UB 对比 (Win/Loss/Tie)
   - 2.4 Gap 改进因果分解 (LB-driven / UB-driven / Both)
   - 2.5 按实例规模分组
   - 2.6 Seed 稳定性
   - 2.7 新增最优实例
3. 详细 Gap 统计
4. Gap 收敛曲线
5. 实例难度分布

统一 Gap 公式：`gap = (UB - LB) / LB`（和论文 Dual-Fast 列对齐；sumup.py 内部用原始 LB/UB 重算）。

## 超算 → 本地 回传

结果目录太大不要 push。只把分析报告 push 回 GitHub：

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
# .gitignore 已经 ignore exp-*/jobs/result/
git add exp-4/sumup/analysis/
git commit -m "exp-4: stage-N analysis"
git push
```

如果超算上 git commit 第一次报 "Please tell me who you are"：

```bash
git config user.email "Minerva-922@users.noreply.github.com"
git config user.name  "Minerva-922"
```

（仓库级配置，不用 `--global`）
