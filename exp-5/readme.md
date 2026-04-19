# exp-5: Dual-Fast v19 vs Baseline（论文配置 / 2 seeds）

> **状态**：READY TO RUN（exp-6 已确认 v19 仍是 fast 家族合适代表——虽然 5 个改进版在 alpha=90 下几乎等价，v19 avg gap 0.4651 略低，和 exp-1 结论一致）
> 20260419 — alpha=90 + cutoff=3600s 对齐论文，seeds=1,2 轻量化（替代 exp-2 的错误 alpha=1 run）

---

## 为什么要 exp-5

exp-2 做的事情完全正确，除了一个**关键参数**：

| 项 | 论文/原版脚本 | exp-2（错）| exp-5（对）|
|---|---|---|---|
| alpha (argv[4]) | `90` → 内部 ALPHA=1.90 | `1` → 1.01 | **90** → 1.90 |
| --cutoff_mem | 16 GB (见 `Ant-QO/experiment-1/exp-1/run_goSolver.sh`) | 未传 | **16** GB |
| cutoff | 3600 s | 3600 s | **3600 s** |
| seeds | 10 | 10 | **2**（为控制 wall-time；exp-6 + exp-1 数据已给出方向）|

`ALPHA` 控制每轮搜索的"扩张倍率"：1.01 = 每轮 +1%，1.90 = 每轮 +90%。两种设置下算法行为完全不同，所以 exp-2 的 22480 个 `.out` 文件和论文 Table 3 没法比，也不能作为 v19 改进的有效基线。exp-5 是用对配置重跑一次。

---

## 实验设置

- **求解器**: `dual-fast` (baseline) + `dual-fast-v19`（二进制复用 `exp-2/codes/`，源码已修 wclq 权重 bug）
- **cutoff**: **3600 s**（论文一致）
- **seeds**: **`1, 2`**（论文用 10；这里为控制 wall-time 改 2；exp-6 + exp-1 已给出选型方向）
- **alpha**: **90**（**不要写 1**）
- **每实例内存上限**: **16 GB**（`goSolver.py --cutoff_mem 16`）
- **SLURM job 级内存**: 64 G（10 个 solver 并行，每个 T1/T2 实例实际 <2 GB，16 GB cap 只是防失控）
- **SLURM job 级 CPU**: 10 核，`PARALLEL=10`
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
| 单 job walltime 上限 | 55 × 3600 / 10 = **5.5 h**（小图 <1s OPT 实际更快） |
| CPU-hours 总计 | 4320 × 3600 / 10 / 3600 ≈ **432** |
| SLURM `--time` | `0-08:00:00` |
| 并发节流 | 队列最多 **50 个**同时在跑（`auto_submit.sh` 的 `BATCH_SIZE=50`）|

---

## 跑法（分批提交，每次最多 50 个在队列）

### 1) 在超算上编译（只需一次）

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
git pull origin main

cd exp-2/codes/Dual-Fast     && make && [ -x dual-fast ]     || { echo "baseline 编译失败"; exit 1; }
cd ../Dual-Fast-v19          && make && [ -x dual-fast-v19 ] || { echo "v19 编译失败";      exit 1; }
```

### 2) 生成 80 个 jobslurm-*

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp-5/jobs
python3 generate_scripts.py         # 默认 seeds=[1,2]
```

### 3) 后台分批提交：队列里最多常驻 50，每 5 分钟补到 50

```bash
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
tail -f auto_submit.log             # Ctrl-C 不会中断后台任务

# 监控
squeue -u $USER -h | wc -l          # 应 ≤ 50
squeue -u $USER -h -o "%T" | sort | uniq -c
```

### 3) 跑完后分析

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp-5/sumup
nohup bash run_sumup.sh > sumup_run.log 2>&1 &
tail -f sumup_run.log
less analysis/exp2_report.md       # 用的是 exp-2 的 sumup.py 模板
```

### 4) 补跑丢的实例（应该极少发生）

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp-5/jobs
python3 generate_patch.py ./result
bash submit_patch.sh
```

---

## 关键修复（沿用 exp-2 经验）

| 文件 | 位置 | 修复 |
|---|---|---|
| `goSolver.py` | `output_monitor` 仅在真 EOF break，每行 flush | exp-2 血的教训 |
| `goSolver.py` | 主线程先 `output_thread.join(timeout=5)` 再 `stop_event.set()` | 不丢 stdout |
| `goSolver.py` | TIMEOUT/MEMOUT 时追加 `>>> Status TIMEOUT/MEMOUT` 行 | sumup 能抓到 |
| `exp-2/sumup/sumup.py` | TIMEOUT 时从中间 round 恢复 best_lb/best_ub | 不丢 LB/UB |
| `exp-2/sumup/sumup.py` | 去重按 timestamp 取**最早**（不是 gap 最好） | 消除重复提交偏差 |
| `generate_scripts.py` | **ALPHA=90**（不是 1！） | 对齐论文 |
| `generate_scripts.py` | `--cutoff_mem 16` | 对齐原版 experiment-1 |
| `Dual-Fast/cc42.h` | `if(tempstr1[0]=='v')` 运行时检测 wclq | 不再依赖 `-DWCLQ` 宏 |

---

## Pre-flight Checklist（超算上开跑前一定要过一遍）

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant

# 1) SSH 能通 GitHub
ssh -T git@github.com 2>&1 | grep -q "successfully authenticated" \
    || { echo "SSH 断了，按 exp-2/ques-sum.md 的 SSH 教程重配"; exit 1; }
git pull origin main

# 2) 两个 solver 都编译好
[ -x exp-2/codes/Dual-Fast/dual-fast ]         || { echo "baseline 未编译"; exit 1; }
[ -x exp-2/codes/Dual-Fast-v19/dual-fast-v19 ] || { echo "v19 未编译";      exit 1; }

# 3) 关键修复还在
grep -q "output_thread.join"  exp-5/jobs/goSolver.py  || { echo "goSolver 修复丢了"; exit 1; }
grep -q "first_seen"          exp-2/sumup/sumup.py    || { echo "sumup 修复丢了";   exit 1; }

# 4) alpha 必须是 90
grep "^ALPHA"     exp-5/jobs/generate_scripts.py | grep -q "= 90" \
    || { echo "alpha 又写错了！必须是 90"; exit 1; }
grep "cutoff_mem" exp-5/jobs/generate_scripts.py | grep -q "CUTOFF_MEM" \
    || { echo "--cutoff_mem 没传"; exit 1; }

# 5) 队列空闲
squeue -u $USER | wc -l     # 应 = 1（仅表头）
sinfo -p hfacnormal01 -t idle,mix --noheader | awk '{s+=$4} END{print s}'

# 6) baseline wclq 权重正确（非 200）
exp-2/codes/Dual-Fast/dual-fast \
    /public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq/T1_50_50_0.wclq 3 1 90 \
    | grep -q "maximum node weight is 49" \
    || { echo "wclq 权重 bug 回来了！"; exit 1; }

# 7) 确认 solver 打印的 ALPHA 是 1.90 而非 1.01
exp-2/codes/Dual-Fast/dual-fast \
    /public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq/T1_50_50_0.wclq 3 1 90 \
    | grep "#alpha" | grep -q "1.900" \
    || { echo "ALPHA 不是 1.90！检查 generate_scripts.py"; exit 1; }

echo "=== Pre-flight PASS ==="
```

---

## exp-5 目录结构

```
exp-5/
├── readme.md               # 本文件
├── jobs/
│   ├── generate_scripts.py # 生成 SLURM 脚本（支持 --seeds 分阶段）
│   ├── generate_patch.py   # 补跑缺失/损坏的实例
│   ├── goSolver.py         # 修复版（stdout 不丢、内存监控）
│   ├── auto_submit.sh      # 批量提交（BATCH_SIZE=180 < 200 上限）
│   └── result/             # 跑完生成，不 push 到 git
└── sumup/
    ├── run_sumup.sh        # 调 exp-2 的 sumup.py 做分析
    └── analysis/           # 跑完生成
```

（`codes/` 不在 exp-5 下——solver 源码和二进制复用 `exp-2/codes/`，避免重复。）

---

## 和 exp-4 的关系

| | exp-4 | exp-5 |
|---|---|---|
| 目标 | Dual-Deep v6 vs 原版 | Dual-Fast v19 vs 原版 |
| alpha | 90 | 90 |
| cutoff | 3600 s | 3600 s |
| seeds | 1, 2 | 1, 2 |
| --cutoff_mem | 16 GB | 16 GB |
| Jobs | 80 | 80 |
| 依赖其他目录 | 无（codes 自带）| 复用 exp-2/codes |

两个实验互相独立，一起提交共 **160 job < 200 上限**，可以并行跑完。
