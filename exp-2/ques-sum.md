现在我已经通读了 [exp2 完整过程](050151ca-fe2d-4ce9-bce0-e2c0d01498cb)。结合这个对话里踩过的所有坑，下面是**全量跑之前必须注意的事项清单**，按严重程度从高到低排列。

---

## 一、致命陷阱（必须提前修掉/验证，否则数据报废）

### 0. alpha 参数写错，所有 exp-1/exp-2/exp-4 baseline 都跑错了（⚠️ 最新发现，必须全部重跑）
- **症状**：我们 `generate_scripts.py` 里写的 `ALPHA = 1`，solver 内部算出 `ALPHA = 1.01`（每轮扩张 1%）；而原版 `Ant-QO/code/Dual-*/README`、`run_goSolver.sh` 一律是 `alpha=90`，内部 `ALPHA=1.90`（每轮扩张 90%）。这是**算法完全不同档**的两种状态。
- **直接后果**：exp-2 里 dual-fast 基线和论文 Table 3 对不上，很大概率就是这个——论文是 1.90，我们是 1.01。
- **已修复**：exp-1 / exp-2 / exp-4 的 `generate_scripts.py` 全部改成 `ALPHA = 90`。
- **复查命令**：`grep ALPHA exp-*/jobs/generate_scripts.py` 应该全部是 `90`，且 `Ant-QO/experiment-*/exp-*/run_goSolver.sh` 的 `ALPHA=90` 作为对照。
- **影响范围**：**exp-2 已跑的 22480 个 `.out` 全部需要重跑**；exp-4 还没跑正好用新参数。

### 1. goSolver.py 的 stdout 丢失 bug（exp2 里最严重的问题）
- **症状**：fast-v19 T1 seed1 应有 540 个 `.out`，实际只有 93 个有 `>>>` 总结行；另有 475 个**空文件**。越快的 solver 丢得越狠（v19 比 dual-fast 丢得更多）。
- **根因**：`output_monitor` 线程里有一段 `if stop_event.is_set() and process.poll() is not None: break`，主线程在进程结束后 set stop_event，导致**剩余缓冲区里的 stdout 还没读完就被 break 掉**。
- **全量跑前必须确认**：
  - 拉到的是修复后的版本（commit 含 `fix(goSolver+sumup): fix stdout data loss & dedup bias`）
  - `output_monitor` 只在 `line == ''`（真正 EOF）时退出，**每写一行都 flush**
  - 主线程**先** `output_thread.join()`，**再** set stop_event

### 2. dual-fast baseline 被强杀导致 `>>>` 行丢失
- **症状**：dual-fast T1 有 5881 条 TIMEOUT，但报告里只有 56/540 实例有 gap 数据。
- **根因**：`GO_TIMEOUT = cutoff + 60/120s` 到期时 goSolver 直接 kill 子进程，baseline 内部的超时自检来不及打印 `>>>` 总结行。
- **修复**：sumup.py 的 `parse_out_file` 在 Status=TIMEOUT/MEMOUT 时，**从每轮中间数据里恢复 best_lb（max）、best_ub（min）**，然后补 `gap = (UB-LB)/LB`。确认这个 fallback 逻辑已经在用。
- **建议**：`GO_TIMEOUT` 给足余量（至少 cutoff + 300s），让 baseline 自己走完打印总结行。

### 3. Dual-Fast baseline 权重读取 bug（如果 baseline 需要重编）
- **症状**：baseline 读出 `max node weight = 200`，v19 读出 `49`——不是一个图，完全无法公平比较。
- **根因**：`cc42.h` 里 `#ifdef WCLQ … #else …`，编译时没定义 WCLQ 宏就走 fallback 随机权重。
- **修复**：改成运行时检测 `if(tempstr1[0]=='v')`；同时把 `vertex = (int **)malloc((edge_num*2+1000)*...)` 改为 `malloc(vertex_num*sizeof(int*))`。

### 4. 论文 Table 3 用 `gap*`（min across seeds），runs 不均 → 对比完全失真
- **症状**：exp2 里 dual-fast 有 41 个实例跑了 20 次，v19 有 264 个实例只跑了 6-8 次。`gap*` 被多 seed 多机会偷偷拉低。
- **根因**：初始手动提交 + 后来的 `auto_submit.sh` 重复提交、+ 补跑未去重。
- **全量跑前必须保证**：
  - **sumup.py 去重逻辑必须是"按 timestamp 取最早一次"**（commit 里已修，原本是"取 gap 最小"，那个等于在帮 dual-fast 作弊）
  - 每个 `(solver, dataset, seed, instance)` **严格 1 条记录**，report 里打印 `pre_dedup → post_dedup` 数量核对

---

## 二、超算资源/调度类（踩过的坑）

### 5. `AssocGrpSubmitJobsLimit` — 同时最多 200 个 job
- **症状**：`sbatch: error: group max submit job limit exceeded 200 (used:200 + requested:1)`
- **generate_scripts.py 当前一次会生成 400 个 job**（2 solver × 2 dataset × 10 chunks × 10 seeds），一次 `bash submit_all.sh` 必然超限。
- **对策**：
  - 用 `auto_submit.sh`（已提交数 < 180 时才提交新的，每 300s 轮询一次）
  - **全量跑前再核一遍 `sinfo -p hfacnormal01 -t idle,mix` 和 `sacctmgr show assoc`**，避免 submit limit 变化
  - `nohup bash auto_submit.sh > auto_submit.log 2>&1 &` 后别关 screen

### 6. `#SBATCH --partition=` 要先确认名字
- 集群没有 `normal`，三个分区是 `hfacnormal01/02/04`。exp2 里用的是 `hfacnormal01`（节点最多）。
- **全量跑前**执行 `sinfo -s` 核一遍分区名，顺便看 `idle+mix` 节点数决定并发策略。

### 7. SSH key 的坑
- 超算的 SSH key **每台登录节点看上去一样但需要重新在 GitHub 挂 key**；exp2 里发现之前挂的那把 key 被删了（指纹都对不上）。
- **全量跑前**：登超算先 `ssh -T git@github.com`，确认是 `Hi Minerva-922! You've successfully authenticated`，再动手 `git pull`。
- Makefile **没有 `clean` 目标**，不要 `make clean && make`，直接 `make` 就行。

### 8. `git pull` 路径问题
- 超算上仓库被 clone 到了 `/public/home/acs4vb4pqv/ylzl/MWDS-Ant`，**不是** `WMDS26`。脚本里 cd 到 `WMDS26/exp-2/...` 会直接 `cd: 没有那个文件或目录`。
- 全量跑前用 `readlink -f` 或 `pwd` 核一下路径，别盲复制上次的指令。

---

## 三、sumup / 数据分析层（exp2 反复翻车）

### 9. 解析 22480 个 .out 文件的性能
- `sumup.py` 扫描全部结果默认阻塞终端很久（exp2 里用户等不及 Ctrl+C 了）。
- **务必 `nohup python3 sumup.py ... > sumup_run.log 2>&1 &`** 放后台。
- 如果 result 文件多，`Path.read_text()` 会慢——文件数超过 5 万建议改成流式读。

### 10. result 目录别 push 到 git
- `.gitignore` 要保留 `exp-*/jobs/result/` 这一行，只 push `exp-*/sumup/analysis/`。
- 超算第一次 commit 会报 `Please tell me who you are` —— 记得在仓库级别 `git config user.email "Minerva-922@users.noreply.github.com"`（不用 `--global`）。

### 11. 解析器对目录名正则要健壮
- 目录名格式：`result-{bin}-{dataset_dir}-{suffix}-c{chunk}-s{seed}-{timestamp}`。exp2 最初正则只抓到最后两段，把 solver 解析成 `fast-T1` 这种垃圾值。
- 全量跑前抽样 3-5 个 result 目录，检查 `extract_solver_dataset_seed` 的返回值，**solver 名必须是 `dual-fast` / `fast-v19` / `dual-deep` / `deep-v6` 这种**，不能混入数据集名。

### 12. Gap 定义要统一
- 论文/fast-baseline 用 `(UB-LB)/LB`，deep 内部输出的是 `(UB-LB)/UB` —— **跨 solver 对比前必须用 CSV 里的原始 LB/UB 重算一份统一 gap**。
- 报告里标清楚用的是哪个公式，并给出 `#opt / ≤10⁻⁴ / ≤10⁻³ / ≤10⁻² / ≤10⁻¹` 五档以对齐论文 Table 3。

### 13. "公共实例" 子集
- 跨 solver pairwise 对比必须取**两边都成功**的交集（exp2 里 T1 最后只有 539/513 实例可比）。
- 报告开头显式打印每个 solver 的成功实例数 + 交集大小，别让差异被掩盖。

---

## 四、实验设计/配置（不是 bug 但影响结论可信度）

### 14. cutoff & seeds
- 论文用 **3600s × 10 seeds**；exp2 也用了这个配置。全量跑前确认 `CUTOFF=3600`、`SEEDS=range(1,11)`。
- 时间估算：每 job = 1 solver × 1 dataset_chunk × 1 seed × 10 并行 × 3600s ≈ 单 job **1~1.5h**（实际，不是最坏 5.5h）。
- 400 job × 每个 1.5h / 100 并行 ≈ **6 小时墙钟**；受 200 job 提交上限影响，整体大概 10-12 小时。

### 15. 内存/CPU
- `--mem=64G`、`--cpus-per-task=10`、`PARALLEL=10` 配合。T1/T2 实例（V≤1000）实际用不了 2G，留 64G 只为大图防 OOM。
- 不要贪心调大 `PARALLEL`，节点 128 核能装 12 个 job，10 核/job 已经是甜蜜点。

### 16. 数据集选择
- **先只跑 T1+T2**（standard_wclq 路径），别混 UDG/NDR/SNAP/DIMACS10——exp2 里发现这些目录格式不一致（有 `.clq` 不是 `.wclq`），会触发 baseline 的 fallback 随机权重，污染数据。
- 要跑这些数据前先 `head -5` 确认第一行有 `p edge/p wclq` 和 `v` 权重行。

---

## 五、可以直接抄的"全量跑 Checklist"

推荐写成 `pre_flight.sh` 在超算上跑一遍：

```bash
set -e
# 1. git & SSH
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
ssh -T git@github.com 2>&1 | grep -q "successfully authenticated" || { echo "SSH fail"; exit 1; }
git pull origin main

# 2. 确认修复版 goSolver/sumup
grep -q "output_thread.join" exp-2/jobs/goSolver.py || { echo "goSolver 未修复"; exit 1; }
grep -q "first_seen" exp-2/sumup/sumup.py || { echo "sumup 未修复"; exit 1; }

# 3. 编译
cd exp-2/codes/Dual-Fast && make && [ -x dual-fast ]
cd ../Dual-Fast-v19    && make && [ -x dual-fast-v19 ]

# 4. 确认 baseline 权重正确
./dual-fast /public/home/acs4vb4pqv/benchmarks/mwds/standard_wclq/T1_wclq/T1_50_50_0.wclq 3 1 90 \
    | grep -q "maximum node weight is 49" || { echo "baseline 权重 bug 未修"; exit 1; }

# 5. 资源检查
squeue -u $USER | wc -l     # 应 ≤ 1（只有表头）
sinfo -p hfacnormal01 -t idle,mix --noheader | awk '{s+=$4} END{print s}'  # 可用节点数

# 6. 配置检查
cd ../../jobs
grep -E "CUTOFF|SEEDS|ALPHA|PARALLEL|SLURM_MEM|SLURM_PARTITION" generate_scripts.py
# 应为 CUTOFF=3600, SEEDS=range(1,11), ALPHA=90 (!!! 不是 1 !!!),
#      PARALLEL=10, MEM=64G, partition=hfacnormal01

# 7. 生成 + 后台自动提交
python3 generate_scripts.py
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
```

---

## 一句话总结

**exp2 数据质量问题 ≈ 80% 来自 goSolver stdout 丢失 + sumup 去重偏差 + 重复提交 + alpha 参数写错**；**工程类卡点 ≈ 20% 来自 SSH key / partition 名 / 200 job 上限**。全量跑前把第 0/1/2/4 条确认过，后面 sumup 分析就不会反复翻车。

> **2026-04-18 update**：发现 `ALPHA=1` 是延续 exp-1 的历史错误（一直以为"传 1"就行），真正和论文一致的是 `ALPHA=90`。exp-2 已跑的全量结果必须重跑才能作为有效对照；exp-4 尚未开跑，改好后开始第一次真正对齐论文设置的实验。