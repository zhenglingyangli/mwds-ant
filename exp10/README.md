# exp10: Layer-A Fair DBS vs Adaptive ACO Controller Full Matrix

## 目标

本实验只回答主算法问题：

```text
在同等 solver budget 下，DBS + adaptive ACO-style controller 是否比 DBS baseline 稳定改善
solver-side LB / UB / gap / #OPT？
```

本实验严格排除外部证书：

```text
不使用 LP dual certificate
不使用 restricted-demand infeasibility certificate
不使用 full-MILP OPT closure
不把 v084 的 SNAP OPT 计入 adaptive ACO-style controller
```

## 为什么 exp-4/exp-5 看起来好，exp-8 不好

当前判断不是简单“数据选坏了”。更可能是三件事叠加：

1. `exp-4/exp-5` 主要覆盖 T1/T2 的 1080 个实例，分布集中，且很多小规模/易闭合实例会放大平均收益。
2. `exp-8` 是 8 个 family 各选 5 个 representative/hard instances，更像压力测试；它暴露了算法在 SNAP、DIMACS、NDR、BHOSLIB 等跨族场景下的不稳定。
3. 目前的 ACO-style controller 更像有偏好的启发式增强，而不是全局全面提升设计；`v085` 已经显示 Deep 侧有小正信号，但 Fast 侧存在 UB regression outliers。

因此 exp10 不再只跑 T1/T2，而是跑：

```text
8 families * 5 selected instances * 5 seeds * 2 solver families
```

并且只比较 Layer A 主算法。

## 实验层次

### Layer A: 主算法层

进入 exp10 全量矩阵：

```text
DBS baseline
DBS + adaptive ACO-style controller
DBS neutral multi-start
```

其中 neutral multi-start 不是额外 solver variant，而是 DBS 的同等 `k` 次调用组合，用于判断收益是否只是多启动带来的。

### Layer B/C: 外部证书层

不在 exp10 中全量重跑：

```text
v017/v076/v077/v080/v082: external LB certificate
v018/v084: external exact closure
```

这些只能在 solver-only 结果生成后作为 post-search certification pipeline 另表报告。

## 当前实现状态

已实现：

```text
jobs/generate_scripts.py
jobs/auto_submit.sh
dataset_manifest.json
selected_instances/*.txt
```

未实现，暂时留空：

```text
Guarded / adaptive ACO-style controller
```

原因：guard 必须只使用当前 run 早期信号，例如 early UB、early LB gain、first-round gap、density/size；不能使用历史 per-case 胜负、known OPT 或外部证书。等 T1_RISK pilot 上 guard 规则明确后，再加入 exp10。

## 默认全量设置

```text
families = T1,T2,UDG,BHOSLIB,DIMACS,DIMACS10,NDR,SNAP
instances per family = 5
seeds = 1,2,3,4,5
solver families = deep-v6,fast-v19
methods = dbs,controller
k calls per method = 2
cutoff = 3600s
alpha = 90
parallel per job = 5
```

默认生成：

```text
2 methods * 2 solver families * 8 families * 5 seeds * 2 reps
= 320 SLURM jobs

each job = 5 selected instances in parallel
total solver calls = 1600
```

## 本地 10 核预计时间

最坏情况按所有 call 都跑满 cutoff 估算：

```text
1600 calls * 3600s / 10 cores = 160 hours ≈ 6.7 days
```

如果只做 `k=1`：

```text
800 calls * 3600s / 10 cores = 80 hours ≈ 3.3 days
```

如果先做 20s pilot：

```text
1600 calls * 20s / 10 cores ≈ 53 minutes
```

实际时间会低于最坏值，因为许多小图会提前结束；但全量 3600s 仍建议放到集群跑。

## 生成脚本

在超算仓库根目录：

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant/exp10/jobs

# smoke: 只生成 T1 seed1 k=1
python3 generate_scripts.py --datasets T1 --seeds 1 --k 1

# pilot: 8 families, 5 seeds, k=2, cutoff=20s
python3 generate_scripts.py --cutoff 20 --k 2

# full: 8 families, 5 seeds, k=2, cutoff=3600s
python3 generate_scripts.py --cutoff 3600 --k 2
```

提交：

```bash
nohup bash auto_submit.sh > auto_submit.log 2>&1 &
tail -f auto_submit.log
```

## Pre-flight checklist

```bash
cd /public/home/acs4vb4pqv/ylzl/MWDS-Ant
git pull origin main

# 1. 检查数据列表
for f in exp10/selected_instances/*.txt; do
  test "$(wc -l < "$f")" -eq 5 || { echo "bad selected list: $f"; exit 1; }
done

# 2. 检查 alpha/cutoff/memory 口径
grep -E "ALPHA|CUTOFF_MEM|DEFAULT_CUTOFF" exp10/jobs/generate_scripts.py

# 3. 编译/检查已有 solver
test -x exp-4/codes/Dual-Deep/dual-deep || { echo "missing deep DBS"; exit 1; }
test -x exp-4/codes/Dual-Deep-v6/dual-deep-v6 || { echo "missing deep ACO-style controller"; exit 1; }
test -x exp-2/codes/Dual-Fast/dual-fast || { echo "missing fast DBS"; exit 1; }
test -x exp-2/codes/Dual-Fast-v19/dual-fast-v19 || { echo "missing fast ACO-style controller"; exit 1; }

# 4. 生成 smoke 脚本，不提交
cd exp10/jobs
python3 generate_scripts.py --datasets T1 --seeds 1 --k 1
```

## 成功判据

只有满足以下条件，才能继续把 DBS + adaptive ACO-style controller 作为主算法主线：

```text
1. deep-v6 与 fast-v19 不互相矛盾；
2. total delta gap < 0，且不是单个 outlier 主导；
3. UB regression 明显减少；
4. solver-side #OPT 有新增，或 LB/gap 在多个 family 上稳定改善；
5. 对比 neutral multi-start 后仍有优势。
```

如果失败，应停止把论文主线写成 “DBS + adaptive ACO-style controller 显著提升 MWDS”，转向：

```text
hybrid search + certification pipeline
```

