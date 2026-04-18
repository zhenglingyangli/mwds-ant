# exp-4: Dual-Deep v6 vs Baseline 全量实验

> **⚠ PAUSED 2026-04-18**: 先跑 `exp-6` 在 alpha=90 下验证 deep 家族 winner（v6 vs v10 vs baseline）。
> 当时 exp-3 的结论（"v6 略优于 v10"）是在错误的 alpha=1 下做的，alpha=90 下排序可能翻。
> 拿到 exp-6 的 `selection_report.md` 后再决定 SOLVERS 是保留 `deep-v6` 还是换成 `deep-v10`。
> 在此之前**不要**跑 `submit_all.sh` / `auto_submit.sh`。

> 20260418 — 采纳 exp-2 踩坑后的修复版本

## 实验设置

- **求解器**: `dual-deep` (baseline) + `dual-deep-v6`
- **cutoff**: 3600s（与论文 ECAI-2025 Table 3 一致）
- **seeds**: 10 (seed 1..10)；**支持分阶段跑**（见下）
- **alpha**: **90** （solver 内部转成 ALPHA=1.90；和 `Ant-QO/code/Dual-*/README` 示例、所有 `Ant-QO/experiment-*/exp-*/run_goSolver.sh` 一致。**不要写 1**——那会变成 ALPHA=1.01 完全不同的算法行为，且和论文对不上。）
- **并行**: 10 核/job，`PARALLEL=10`
- **内存**: 64G/job
- **partition**: `hfacnormal01`

## 数据集

| 数据集 | 实例数 | 超算路径 |
|--------|--------|----------|
| T1 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq` |
| T2 | 540 | `/public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T2_wclq` |

---

## 两阶段跑法（推荐）

集群上限 `AssocGrpSubmitJobsLimit=200`，一次性提交 400 个会被拒。
即便用 `auto_submit.sh` 分批，也建议先跑少量 seed 验证结果方向。

### 阶段 1：2 seeds 试跑

```bash
# 只生成 seed 1, 2 的 SLURM 脚本（2 solver × 2 dataset × 10 chunks × 2 seeds = 80 个）
python3 generate_scripts.py --seeds 1,2
bash submit_all.sh     # 80 个，一次提交即可（不超 200 上限）
```

这 80 个 job 预计 ~5~8 小时跑完。看一下 v6 vs baseline 在 Gap/LB/UB 上的方向是否符合预期：

```bash
cd ../sumup
python3 sumup.py ../jobs/result --output_dir ./analysis
```

### 阶段 2：补齐剩余 8 seeds

**代码、ALPHA、CUTOFF、PARALLEL 都不能改**，否则新老数据不可比。

```bash
cd ../jobs
# 清掉旧的 jobslurm-* 和 submit_all.sh（不会动 result/ 目录）
rm -f jobslurm-* submit_all.sh namelist-*.txt

# 只生成 seed 3..10 的脚本
python3 generate_scripts.py --seeds 3-10
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
tail -f auto_submit.log
```

新结果保存在 `result/` 下新的 `result-*-s3-*` ~ `result-*-s10-*` 子目录里，`sumup.py` 扫到后会自动和阶段 1 合并。

### 阶段 3：补跑丢的实例（如有）

如果发现 `.out` 文件有空文件/只含 header（理论上 goSolver 修过之后不再发生，但保险起见）：

```bash
python3 generate_patch.py ./result
bash submit_patch.sh
```

只会为**缺失或不完整**的 `(solver, dataset, seed, instance)` 生成脚本，已完成的实例不会重跑。

---

## 全量一次跑（不推荐）

如果你确信 2 seeds 的试跑已经没问题，可以直接：

```bash
python3 generate_scripts.py                # 生成 400 个
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
```

`auto_submit.sh` 的 `BATCH_SIZE=180`，每 5 分钟检查一次队列，队列少于 180 时补齐，不会触发 200 上限。

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
