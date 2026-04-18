# exp-6: 在 alpha=90 下重测版本选型

> 2026-04-18 — exp-1/exp-3 选型在错误的 alpha=1 下做的，"v19 / v6 最优"的结论**仅以噪声级差距领先**。在跑 exp-4/5 全量之前，必须先在正确的 alpha=90 下确认哪个版本真的最好，否则可能浪费上千 CPU-hours。

---

## 为什么必须做这一轮

从 `exp-1/sumup/analysis/exp1_report.md` 的 pairwise 对比（alpha=1, 300s, 5 seeds）抽取 v19 vs 其他改进版：

| v19 对手 (T1) | v19 胜 / 负 / 平 |
|---|---|
| `fast` baseline | **170 / 50 / 15** ✓ 大胜 |
| v28 | 44 / 42 / 92 — 打平 |
| poolrelink | 37 / 40 / 75 — **v19 略输** |
| pool | 54 / 39 / 113 — 略赢 |
| freqscore | 45 / 29 / 87 — 略赢 |

| v19 对手 (T2) | v19 胜 / 负 / 平 |
|---|---|
| v28 | 49 / 53 / 115 — **v28 略赢** |
| poolrelink | 38 / 41 / 122 — **poolrelink 略赢** |

Deep 家族：`exp-3` 已经表明 v6 vs v10 在 300s 上基本等效。

**也就是说**：v19 / v6 只是在 alpha=1 下"候选池的第一名"，领先 ≤ 2%。因为我们做的修改（`adaptive_alpha = ALPHA*1.5`、`MaxIteration *= (1 + alpha/100)` 等）**数学上强依赖 ALPHA**，从 1.01 跳到 1.90 时各版本的排序完全可能重排。选错 winner 的代价是 2000+ CPU-hours 的 exp-4/5 白跑。

---

## 实验设置（**只动 alpha，其它全部对齐 exp-1**）

| 项 | exp-1 (原选型) | exp-6 (本次) |
|---|---|---|
| alpha | `1` ❌ | **`90`** ✓ |
| cutoff | 300 s | **30 s**（T1 在 alpha=90 下早收敛，见下） |
| seeds | 5 | **2** |
| 数据 | DIMACS + T1 + T2 | **T1 每 6 个取 1 个共 90 实例**（均匀抽样） |
| parallel | 10 | **10**（单 job 内并发实例数） |
| --cutoff_mem | （未传） | **16 GB** |
| 参赛版本 | 9 | 9（同一批，见下） |

**为什么 30s 足够**（从 exp-1 (alpha=1, 300s) 的数据外推）：
- `exp1_report.md` 第 3 节里每个 solver 的 gap_10s ≈ gap_30s ≈ gap_60s（差 ≤ 0.001），T1 在 10s 就进入平台期，30-300s 基本无改进
- alpha=90 下算法扩张更激进（`MaxIteration *= (1 + 90/100) = 1.9x`、Beta 每轮 90% 扩），收敛比 alpha=1 更快——30s @ alpha=90 ≈ 60s+ @ alpha=1
- 选型只需"能区分谁好"，不需要等每个实例收敛到极致

**关于小图平局的风险**：T1 小图（V=50/100）在 alpha=90 下 <1s 就 === optimal，所有版本打平。每对 solver 最大可对比数 = 90 insts × 2 seeds = 180 条，实际去掉全平的小图后估计 ~60-100 条"有效"比较。看 `selection_report.md` 的 `Selection Recommendation` 净胜数字：
- 净胜 ≥5 且有效对比 50+ → 结论可信
- 净胜 ≤2 → 信号弱，追加 seeds：`python3 generate_scripts.py --seeds 3,4 && bash submit_all.sh`（老数据自动保留，sumup 合并）

### 参赛版本

| 家族 | Solver | 源码位置 |
|---|---|---|
| Fast | `dual-fast` (baseline) | `exp-1/codes/Dual-Fast` |
| Fast | `dual-fast-v19` | `exp-1/codes/Dual-Fast-v19` |
| Fast | `dual-fast-v28` | `exp-1/codes/Dual-Fast-v28` |
| Fast | `exp5-freqscore` | `exp-1/codes/Exp5-FreqScore` |
| Fast | `exp6-poolrelink` | `exp-1/codes/Exp6-PoolRelink` |
| Fast | `exp9-freq-pool` | `exp-1/codes/Exp9-Freq-Pool` |
| Deep | `dual-deep` (baseline) | `exp-1/codes/Dual-Deep` |
| Deep | `dual-deep-v6` | `exp-1/codes/Dual-Deep-v6` |
| Deep | `dual-deep-v10` | `exp-3/codes/Dual-Deep-v10` |

### 资源估算

- Job 数：9 solver × 1 chunk × 2 seeds = **18 jobs**（<< 200 上限）
- 单 job cpus-per-task：10
- 单 job walltime 上限：90 × 30 / 10 = **4.5 min** (最坏全部 TIMEOUT)
- CPU-hours 总计：9 × 90 × 2 × 30 / 3600 = **1.35**
- Wall time：18 jobs 并行上去，快则 ~5 min 结束，排队慢则 ~15-20 min 全部完成

### T1 子集（每 6 个取 1）

`generate_scripts.py` 在 job 里动态生成 namelist：对 `T1_wclq/*.wclq` 排序后取 index 0, 6, 12, …, 534 共 90 个。这样：
- 覆盖所有 |V|, |E| 组合（按文件名排序天然按 V, E 聚类）
- 和 exp-1 / exp-4 / exp-5 用的同一个目录，随时可交叉验证
- 不挑"容易赢"的子集

---

## 跑法

### 超算上

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
git pull origin main

# 编译 9 个 solver（exp-1/codes 里的 6 个 + exp-3 里的 v10；deep/v6 也用 exp-1 版）
for dir in exp-1/codes/Dual-Fast exp-1/codes/Dual-Fast-v19 \
           exp-1/codes/Dual-Fast-v28 exp-1/codes/Exp5-FreqScore \
           exp-1/codes/Exp6-PoolRelink exp-1/codes/Exp9-Freq-Pool \
           exp-1/codes/Dual-Deep exp-1/codes/Dual-Deep-v6 \
           exp-3/codes/Dual-Deep-v10 ; do
    echo "=== $dir ==="
    (cd "$dir" && make) || exit 1
done

# Pre-flight（alpha=90、cutoff=30、cutoff_mem=16）
cd exp-6/jobs
grep "^ALPHA"       generate_scripts.py | grep -q "= 90" || { echo "alpha 写错"; exit 1; }
grep "^CUTOFF "     generate_scripts.py | grep -q "= 30" || { echo "cutoff 写错"; exit 1; }
grep "^CUTOFF_MEM"  generate_scripts.py | grep -q "= 16" || { echo "cutoff_mem 写错"; exit 1; }

# 生成 + 提交
python3 generate_scripts.py      # 默认就是 T1 1/6 subset + 2 seeds
bash submit_all.sh               # 18 < 200，直接全提
squeue -u $USER | wc -l
```

### 跑完后分析

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp-6/sumup
bash run_sumup.sh
less analysis/selection_report.md
```

产出：

1. **Per-solver 总榜**：每个版本的 avg gap / #opt / gap≤0.01 比例（T1 子集 90 实例）
2. **Pairwise 胜负表**：9 × 9 的 wins/losses/ties 矩阵，一眼看清相对强弱
3. **家族内排名**：fast 家族 6 个排序 + deep 家族 3 个排序，指明"真 winner"

---

## 分支决策

| exp-6 选型结果 | 下一步 |
|---|---|
| fast winner 仍是 **v19**，deep winner 仍是 **v6** | exp-4/5 继续按 pilot 2 seeds 开跑；exp-4/5 现已暂停 |
| fast winner 变 v28 / poolrelink / pool / freqscore | exp-5 的 `SOLVERS` 换成新 winner；exp-5 pilot 重新生成 |
| deep winner 变 v10 | exp-4 的 `SOLVERS` 换成 `dual-deep-v10`；exp-4 pilot 重新生成 |
| 两个家族都出现意外赢家 | exp-4 / exp-5 都换 solver 重来 |

**关于 TIMEOUT**：30s + T1 子集下，大图（V=800/1000, 尤其 E=10000）几乎肯定全部 TIMEOUT。sumup.py 已含从中间 round 恢复 LB/UB 的逻辑（exp-2 踩过这个坑），TIMEOUT 实例照样会进 pairwise 比较（**这正是选型需要的——谁在 30s 内把 LB 推得更高**）。若某实例所有 9 个 solver 都 TIMEOUT 且 LB/UB 都是 0，它在报告里会被 gap<0 过滤掉。

**关于 exp-1 report 的 "gap_120s < final" 异常**：这是 `exp-1/sumup/sumup.py` 的 **sample bias bug**——convergence table 的 `gap_Xs` 只对"有 round 满足 `total_time >= X`"的实例取均值，而 `final` 是全量，两列实例集合不一致。**不是算法异常，也不代表 120s 比 300s 表现更好**。exp-6 的 `sumup.py` 改用 per-instance pairwise（同一实例同一 seed 对比），完全规避这个 bug。
