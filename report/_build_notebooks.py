"""Build three analysis notebooks programmatically.

Run once:   cd report && python3 _build_notebooks.py

Emits:
    report/main.ipynb
    report/exp4/analysis.ipynb
    report/exp5/analysis.ipynb
"""
from __future__ import annotations

from pathlib import Path

import nbformat
from nbformat.v4 import new_code_cell, new_markdown_cell, new_notebook

HERE = Path(__file__).resolve().parent


# =============================================================================
# shared setup cell (used by exp4 / exp5 notebooks)
# =============================================================================

EXP_SETUP = """\
import sys
sys.path.insert(0, '..')
from _style import *

CHART_DIR = Path('charts')
CHART_DIR.mkdir(exist_ok=True)

# EXP_NAME is defined below per notebook
CSV_PATH = EXP4_CSV if EXP_NAME == 'exp4' else EXP5_CSV
IMP_NAME = 'deep-v6' if EXP_NAME == 'exp4' else 'fast-v19'
BASE_NAME = 'dual-deep' if EXP_NAME == 'exp4' else 'dual-fast'
IMP_COLOR = GREEN if EXP_NAME == 'exp4' else BLUE
BASE_COLOR = GRAY
TAG = 'v6' if EXP_NAME == 'exp4' else 'v19'

df = load_exp(CSV_PATH)
print(f'loaded {len(df)} rows, solvers={df.solver.unique().tolist()}')

imp = per_instance(df, IMP_NAME)
base = per_instance(df, BASE_NAME)
merged = pairwise(imp, base)
print(f'per-instance: imp={len(imp)}  base={len(base)}  merged={len(merged)}')
print('win:', merged.win.value_counts().to_dict())
print('cause:', merged.cause.value_counts().to_dict())
"""


# =============================================================================
# chart cell templates (each returns source code as a string)
# =============================================================================

def chart_01_headline():
    """4-01 / 5-01: Avg + Median gap bar."""
    return '''\
# ## 4-01 / 5-01 — Avg + Median Gap Bar
# ---
# 数据源：当前 exp 的 per-instance 聚合（imp vs base）
# 字段：gap (seed-avg) -> per-dataset avg 和 median
# 视觉：每 dataset 两 bar pair（avg 实心 / median 斜纹）；上方标 Δ% (imp − base) / base * 100

fig, ax = plt.subplots(figsize=(9, 5))
datasets = ['T1', 'T2']
x = np.arange(len(datasets)) * 1.6
w = 0.32

avg_imp = [imp[imp.dataset == d]['gap'].mean() for d in datasets]
avg_base = [base[base.dataset == d]['gap'].mean() for d in datasets]
med_imp = [imp[imp.dataset == d]['gap'].median() for d in datasets]
med_base = [base[base.dataset == d]['gap'].median() for d in datasets]

ax.bar(x - 1.5*w, avg_base, w, label=f'{BASE_NAME} avg',
       color=BASE_COLOR, edgecolor='black', linewidth=1)
ax.bar(x - 0.5*w, avg_imp, w, label=f'{IMP_NAME} avg',
       color=IMP_COLOR, edgecolor='black', linewidth=1)
ax.bar(x + 0.5*w, med_base, w, label=f'{BASE_NAME} median',
       color=BASE_COLOR, edgecolor='black', linewidth=1, hatch='//', alpha=0.8)
ax.bar(x + 1.5*w, med_imp, w, label=f'{IMP_NAME} median',
       color=IMP_COLOR, edgecolor='black', linewidth=1, hatch='//', alpha=0.8)

# Δ% annotations on avg bars
for i, d in enumerate(datasets):
    pct = (avg_imp[i] - avg_base[i]) / avg_base[i] * 100 if avg_base[i] else 0
    ytop = max(avg_base[i], avg_imp[i]) * 1.08 + 0.002
    ax.annotate(f'Δavg {pct:+.1f}%', (x[i] - w, ytop), ha='center',
                fontsize=12, color=RED if pct < 0 else GREEN, fontweight='bold')
    pct_m = (med_imp[i] - med_base[i]) / max(med_base[i], 1e-9) * 100
    ytop_m = max(med_base[i], med_imp[i]) * 1.08 + 0.002
    ax.annotate(f'Δmed {pct_m:+.1f}%', (x[i] + w, ytop_m), ha='center',
                fontsize=12, color=RED if pct_m < 0 else GREEN, fontweight='bold')

ax.set_xticks(x)
ax.set_xticklabels(datasets)
ax.set_ylabel('Gap = (UB-LB)/LB')
ax.set_title(f'{IMP_NAME} vs {BASE_NAME} — Avg / Median Gap')
ax.set_ylim(0, max(max(avg_base), max(avg_imp)) * 1.22)
ax.legend(loc='upper right', frameon=True, fontsize=11)
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, f'{TAG}-01-avg-median-gap.png')
'''


def chart_02_threshold():
    """4-02 / 5-02: Table 3 threshold bar + CDF."""
    return '''\
# ## 4-02 / 5-02 — Threshold Distribution (Table 3 format) + Gap CDF
# ---
# 左：每档 (#opt / ≤1e-4 / ≤1e-3 / ≤1e-2 / ≤1e-1) 的实例比例
# 右：逐实例 gap 的累计分布函数 (CDF，log x 轴)

fig, axes = plt.subplots(1, 2, figsize=(14, 5))

# --- 左：阈值分档比例 ---
ax = axes[0]
labels = [t[0] for t in THRESHOLDS]
x = np.arange(len(labels))
w = 0.36
for d_idx, d in enumerate(['T1', 'T2']):
    t_imp = threshold_table(imp[imp.dataset == d])
    t_base = threshold_table(base[base.dataset == d])
    n = t_imp['n'].iloc[0]
    pct_imp = [t_imp[l].iloc[0] / n * 100 for l in labels]
    pct_base = [t_base[l].iloc[0] / n * 100 for l in labels]
    offset = -w/2 + d_idx * w
    ax.bar(x + offset - 0.01, pct_base, w*0.45, label=f'{BASE_NAME} {d}',
           color=BASE_COLOR, edgecolor='black', linewidth=0.5,
           alpha=0.55 if d == 'T2' else 1.0)
    ax.bar(x + offset + w*0.48, pct_imp, w*0.45, label=f'{IMP_NAME} {d}',
           color=IMP_COLOR, edgecolor='black', linewidth=0.5,
           alpha=0.55 if d == 'T2' else 1.0)
ax.set_xticks(x)
ax.set_xticklabels(labels)
ax.set_ylabel('% instances')
ax.set_title('Threshold distribution')
ax.legend(fontsize=10, loc='upper left')
ax.set_axisbelow(True)

# --- 右：gap CDF (log x) ---
ax2 = axes[1]
for d, ls in zip(['T1', 'T2'], ['-', '--']):
    for sv, col in [(base, BASE_COLOR), (imp, IMP_COLOR)]:
        vals = sv[sv.dataset == d]['gap'].values
        vals = np.sort(np.clip(vals, 1e-6, None))
        ys = np.arange(1, len(vals)+1) / len(vals) * 100
        name = BASE_NAME if sv is base else IMP_NAME
        ax2.step(vals, ys, where='post', linestyle=ls,
                 color=col, linewidth=2, label=f'{name} {d}')
ax2.set_xscale('log')
ax2.set_xlabel('gap  (log)')
ax2.set_ylabel('% of instances with gap ≤ x')
ax2.set_title('Per-instance gap CDF')
ax2.legend(fontsize=10, loc='lower right')
ax2.set_axisbelow(True)

save_show(fig, CHART_DIR, f'{TAG}-02-threshold-cdf.png')
'''


def chart_03_winloss():
    """4-03 / 5-03: Win/Tie/Loss pie T1+T2."""
    return '''\
# ## 4-03 / 5-03 — Per-instance Win / Tie / Loss
# ---
# tie 阈值：|d_gap| <= 1e-6  (见 _style.pairwise)
fig, axes = plt.subplots(1, 2, figsize=(12, 5.5))
for ax, d in zip(axes, ['T1', 'T2']):
    sub = merged[merged.dataset == d]
    w = (sub.win == 1).sum()
    t = (sub.win == 0).sum()
    l = (sub.win == -1).sum()
    n = len(sub)
    colors = [IMP_COLOR, LIGHT_GRAY, RED]
    labels = [f'Win {w}\\n({w/n*100:.1f}%)',
              f'Tie {t}\\n({t/n*100:.1f}%)',
              f'Loss {l}\\n({l/n*100:.1f}%)']
    ax.pie([w, t, l], labels=labels, colors=colors, startangle=90,
           wedgeprops=dict(edgecolor='white', linewidth=2),
           textprops=dict(fontsize=12))
    ax.set_title(f'{d}  (n={n})')

fig.suptitle(f'{IMP_NAME} vs {BASE_NAME} — per-instance outcomes', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-03-win-tie-loss.png')
'''


def chart_04_dgap_hist():
    """4-04 / 5-04: Δgap histogram."""
    return '''\
# ## 4-04 / 5-04 — Per-instance Δgap Histogram
# ---
# x = gap_imp − gap_base  (负 = 改进赢)
# 按 dataset 双色堆叠；对称截断到 ±max(|d_gap|) * 0.99 防异常极值拉宽

fig, ax = plt.subplots(figsize=(10, 5))
dvals = merged['d_gap'].values
lim = np.quantile(np.abs(dvals), 0.98) if len(dvals) else 1
bins = np.linspace(-lim, lim, 41)

for d, col, al in [('T1', IMP_COLOR, 0.75), ('T2', PURPLE, 0.55)]:
    sub = merged[merged.dataset == d]
    ax.hist(np.clip(sub['d_gap'], -lim, lim), bins=bins, color=col,
            alpha=al, edgecolor='white', linewidth=0.5, label=f'{d}  (n={len(sub)})')

ax.axvline(0, color=GRAY, linestyle='--', linewidth=1.5)
ax.text(-lim*0.95, ax.get_ylim()[1]*0.9, f'← {IMP_NAME} better', color=GREEN, fontsize=12)
ax.text(lim*0.2, ax.get_ylim()[1]*0.9, f'{BASE_NAME} better →', color=RED, fontsize=12)

ax.set_xlabel(f'Δgap = gap({IMP_NAME}) − gap({BASE_NAME})')
ax.set_ylabel('instances')
ax.set_title(f'Per-instance Δgap distribution  (T1+T2, n={len(merged)})')
ax.legend(fontsize=11)
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, f'{TAG}-04-dgap-histogram.png')
'''


def chart_05_lb_scatter():
    """4-05 / 5-05: LB scatter."""
    return '''\
# ## 4-05 / 5-05 — LB Scatter: imp vs baseline
# ---
# 点色按 V 分级；对角线参考；右下方 = imp LB 更紧（加权更大 = 更接近 opt，赢）
# 用 log-log 防 50-250 小实例被大实例压扁

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharex=False, sharey=False)

for ax, d in zip(axes, ['T1', 'T2']):
    sub = merged[merged.dataset == d].copy()
    sub = sub[(sub['best_lb_base'] > 0) & (sub['best_lb_imp'] > 0)]
    sizes = np.clip(sub['V'] / 2, 8, 120)
    colors = [GREEN if v > 500 else (ORANGE if v > 100 else BLUE) for v in sub['V']]
    ax.scatter(sub['best_lb_base'], sub['best_lb_imp'],
               s=sizes, c=colors, alpha=0.55, edgecolor='black', linewidth=0.4)
    # diagonal
    lo = min(sub['best_lb_base'].min(), sub['best_lb_imp'].min()) * 0.9
    hi = max(sub['best_lb_base'].max(), sub['best_lb_imp'].max()) * 1.1
    ax.plot([lo, hi], [lo, hi], color=GRAY, linestyle='--', linewidth=1)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(f'{BASE_NAME} best_lb')
    ax.set_ylabel(f'{IMP_NAME} best_lb')
    wins = (sub['best_lb_imp'] > sub['best_lb_base']).sum()
    ties = (sub['best_lb_imp'] == sub['best_lb_base']).sum()
    loss = (sub['best_lb_imp'] < sub['best_lb_base']).sum()
    ax.set_title(f'{d}  LB win/tie/loss = {wins}/{ties}/{loss}')
    ax.set_axisbelow(True)
# legend for color bins
for ax in axes:
    ax.scatter([], [], c=BLUE, s=40, alpha=0.6, label='V<100')
    ax.scatter([], [], c=ORANGE, s=70, alpha=0.6, label='100≤V≤500')
    ax.scatter([], [], c=GREEN, s=110, alpha=0.6, label='V>500')
axes[0].legend(loc='upper left', fontsize=10)
fig.suptitle(f'Best LB — {IMP_NAME} (y) vs {BASE_NAME} (x).  Above diag = imp tighter LB = win', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-05-lb-scatter.png')
'''


def chart_06_ub_scatter():
    """4-06 / 5-06: UB scatter."""
    return '''\
# ## 4-06 / 5-06 — UB Scatter: imp vs baseline
# ---
# 下方 = imp UB 更小（赢）；点多贴近对角线 = "UB 几乎没动"，结合 LB scatter 印证"LB 主导"

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5), sharex=False, sharey=False)
for ax, d in zip(axes, ['T1', 'T2']):
    sub = merged[merged.dataset == d].copy()
    sub = sub[(sub['best_ub_base'] > 0) & (sub['best_ub_imp'] > 0)]
    sizes = np.clip(sub['V'] / 2, 8, 120)
    colors = [GREEN if v > 500 else (ORANGE if v > 100 else BLUE) for v in sub['V']]
    ax.scatter(sub['best_ub_base'], sub['best_ub_imp'],
               s=sizes, c=colors, alpha=0.55, edgecolor='black', linewidth=0.4)
    lo = min(sub['best_ub_base'].min(), sub['best_ub_imp'].min()) * 0.9
    hi = max(sub['best_ub_base'].max(), sub['best_ub_imp'].max()) * 1.1
    ax.plot([lo, hi], [lo, hi], color=GRAY, linestyle='--', linewidth=1)
    ax.set_xscale('log'); ax.set_yscale('log')
    ax.set_xlabel(f'{BASE_NAME} best_ub')
    ax.set_ylabel(f'{IMP_NAME} best_ub')
    wins = (sub['best_ub_imp'] < sub['best_ub_base']).sum()
    ties = (sub['best_ub_imp'] == sub['best_ub_base']).sum()
    loss = (sub['best_ub_imp'] > sub['best_ub_base']).sum()
    ax.set_title(f'{d}  UB win/tie/loss = {wins}/{ties}/{loss}')
    ax.set_axisbelow(True)
fig.suptitle(f'Best UB — {IMP_NAME} (y) vs {BASE_NAME} (x).  Below diag = imp smaller UB = win', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-06-ub-scatter.png')
'''


def chart_07_lbub_pct():
    """4-07 / 5-07: LB/UB improvement % bar."""
    return '''\
# ## 4-07 / 5-07 — Avg ΔLB% vs Avg ΔUB%  (dual-axis equivalent)
# ---
# 同一图两组柱：ΔLB / LB_base * 100%  (正 = imp LB 更紧 → 想大)
#              ΔUB / UB_base * 100%  (负 = imp UB 更小 → 想小)
# 期望：ΔLB% >> 0, ΔUB% ≈ 0  →  改进主因是 LB

fig, ax = plt.subplots(figsize=(9, 5))
datasets = ['T1', 'T2']
x = np.arange(len(datasets)) * 1.4
w = 0.42

lb_pct = []
ub_pct = []
for d in datasets:
    sub = merged[merged.dataset == d]
    sub = sub[(sub['best_lb_base'] > 0) & (sub['best_ub_base'] > 0)]
    lb_pct.append(((sub['best_lb_imp'] - sub['best_lb_base']) / sub['best_lb_base']).mean() * 100)
    ub_pct.append(((sub['best_ub_imp'] - sub['best_ub_base']) / sub['best_ub_base']).mean() * 100)

b1 = ax.bar(x - w/2, lb_pct, w, label='avg ΔLB %  (↑ better)',
            color=IMP_COLOR, edgecolor='black', linewidth=0.8)
b2 = ax.bar(x + w/2, ub_pct, w, label='avg ΔUB %  (↓ better)',
            color=ORANGE, edgecolor='black', linewidth=0.8, alpha=0.9)
for b, v in zip(b1, lb_pct):
    ax.annotate(f'{v:+.2f}%', (b.get_x() + b.get_width()/2, v), ha='center',
                va='bottom' if v >= 0 else 'top', fontsize=11, fontweight='bold')
for b, v in zip(b2, ub_pct):
    ax.annotate(f'{v:+.2f}%', (b.get_x() + b.get_width()/2, v), ha='center',
                va='bottom' if v >= 0 else 'top', fontsize=11, fontweight='bold')

ax.axhline(0, color='black', linewidth=0.6)
ax.set_xticks(x); ax.set_xticklabels(datasets)
ax.set_ylabel(f'% change relative to {BASE_NAME}')
ax.set_title(f'LB vs UB — where does the improvement come from?')
ax.legend(fontsize=11, loc='upper right')
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, f'{TAG}-07-lb-ub-pct.png')
'''


def chart_08_by_V():
    """4-08 / 5-08: Improvement by V scale."""
    return '''\
# ## 4-08 / 5-08 — Improvement by V (node count) scale
# ---
# 3 档：Small(V<100) / Medium(100≤V<500) / Large(V≥500)
# bar = win%；折线 = avg Δgap（负 = imp 赢越多）

merged['Vbucket'] = merged['V'].apply(v_bucket)
order = ['Small (V<100)', 'Medium (100≤V<500)', 'Large (V≥500)']

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
for ax, d in zip(axes, ['T1', 'T2']):
    sub = merged[merged.dataset == d]
    win_pct, avg_dgap, counts = [], [], []
    for b in order:
        s = sub[sub.Vbucket == b]
        counts.append(len(s))
        win_pct.append((s.win == 1).mean() * 100 if len(s) else 0)
        avg_dgap.append(s.d_gap.mean() if len(s) else 0)
    x = np.arange(len(order))
    ax.bar(x, win_pct, color=IMP_COLOR, edgecolor='black', linewidth=0.8,
           alpha=0.85, label=f'{IMP_NAME} win %')
    ax.set_xticks(x); ax.set_xticklabels(order, rotation=0, fontsize=10)
    ax.set_ylabel(f'{IMP_NAME} win % (bars)')
    ax.set_ylim(0, 105)
    for xi, wp, n in zip(x, win_pct, counts):
        ax.annotate(f'{wp:.1f}%\\n(n={n})', (xi, wp + 2), ha='center', fontsize=10)
    ax2 = ax.twinx()
    ax2.plot(x, avg_dgap, marker='o', color=RED, linewidth=2, label='avg Δgap')
    ax2.axhline(0, color=GRAY, linestyle=':')
    ax2.set_ylabel('avg Δgap (line, ↓ better)', color=RED)
    ax2.tick_params(axis='y', colors=RED)
    ax.set_title(f'{d}')
    ax.set_axisbelow(True)

fig.suptitle('Improvement by scale (V)', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-08-improvement-by-V.png')
'''


def chart_09_by_density():
    """4-09 / 5-09: Improvement by E/V density."""
    return '''\
# ## 4-09 / 5-09 — Improvement by E/V density
# ---
# 密度 = E/V；分桶后折线 avg Δgap 看 "我们的方法在哪种图上最有用"

merged['EV'] = merged['E'] / merged['V'].replace(0, np.nan)
merged['dbucket'] = merged['EV'].apply(lambda x: density_bucket(x) if pd.notna(x) else 'Unknown')
order = ['Sparse (E/V<1.5)', 'Medium (1.5≤E/V<5)', 'Dense (5≤E/V<20)', 'Very Dense (E/V≥20)']

fig, ax = plt.subplots(figsize=(11, 5.5))
x = np.arange(len(order))
w = 0.38
for i, d in enumerate(['T1', 'T2']):
    sub = merged[merged.dataset == d]
    avg_dg = [sub[sub.dbucket == b]['d_gap'].mean() if (sub.dbucket == b).any() else np.nan
              for b in order]
    counts = [(sub.dbucket == b).sum() for b in order]
    col = IMP_COLOR if d == 'T1' else PURPLE
    bars = ax.bar(x + (-w/2 if d == 'T1' else w/2), avg_dg, w, color=col,
                  edgecolor='black', alpha=0.85, label=f'{d}')
    for xi, v, n, b in zip(x, avg_dg, counts, bars):
        if pd.notna(v):
            off = (w/2 if d == 'T2' else -w/2)
            ax.annotate(f'n={n}', (xi + off, v), ha='center',
                        va='top' if v < 0 else 'bottom', fontsize=9)

ax.axhline(0, color='black', linewidth=0.8)
ax.set_xticks(x); ax.set_xticklabels(order, rotation=15, fontsize=10)
ax.set_ylabel('avg Δgap (↓ better)')
ax.set_title(f'Improvement by graph density — {IMP_NAME} vs {BASE_NAME}')
ax.legend(fontsize=11)
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, f'{TAG}-09-improvement-by-density.png')
'''


def chart_10_convergence():
    """4-10 / 5-10: convergence curves."""
    return '''\
# ## 4-10 / 5-10 — Convergence Curves (gap vs time)
# ---
# 用 CSV 中 gap_{10,60,300,600,1800,3600}s 列；
# 若某行该时刻 checkpoint 为 -1（提前结束或未记录），用最终 gap 前向填充
# 语义：平均到某个时刻全部实例（含已结束）当前最好 gap

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, d in zip(axes, ['T1', 'T2']):
    ts_imp, avg_imp = gap_curve(df, IMP_NAME, d)
    ts_base, avg_base = gap_curve(df, BASE_NAME, d)
    ax.plot(ts_base, avg_base, marker='o', color=BASE_COLOR, linewidth=2.2,
            label=BASE_NAME)
    ax.plot(ts_imp, avg_imp, marker='s', color=IMP_COLOR, linewidth=2.2,
            label=IMP_NAME)
    ax.set_xscale('log')
    ax.set_xlabel('time (s)')
    ax.set_ylabel('avg gap')
    ax.set_title(f'{d}')
    ax.legend(fontsize=11)
    ax.set_axisbelow(True)

fig.suptitle(f'Convergence — avg gap over time', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-10-convergence.png')
'''


def chart_11_time2quality():
    """4-11 / 5-11: time-to-quality CDF."""
    return '''\
# ## 4-11 / 5-11 — Time-to-Quality CDF
# ---
# 在时刻 t 有多少比例的实例 gap ≤ threshold 了？
# 用 2 个阈值：1e-2 和 1e-3，对两个 solver 各画一对

THRESH_A = 1e-2
THRESH_B = 1e-3

fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, d in zip(axes, ['T1', 'T2']):
    for sv_name, col, ls_list in [(BASE_NAME, BASE_COLOR, ['-','--']),
                                   (IMP_NAME, IMP_COLOR, ['-','--'])]:
        sub = df[(df.solver == sv_name) & (df.dataset == d)].copy()
        for c in TIME_COLS:
            mask = sub[c] < 0
            sub.loc[mask, c] = sub.loc[mask, 'gap']
        for thr, lbl, lsi in [(THRESH_A, 'gap≤1e-2', 0), (THRESH_B, 'gap≤1e-3', 1)]:
            frac_t = [(sub[c] <= thr).mean() * 100 for c in TIME_COLS]
            ax.plot(TIME_SECONDS, frac_t, marker='o', color=col,
                    linestyle=ls_list[lsi], linewidth=2,
                    label=f'{sv_name} {lbl}')
    ax.set_xscale('log')
    ax.set_xlabel('time (s)')
    ax.set_ylabel('% instances satisfying threshold')
    ax.set_title(f'{d}')
    ax.set_ylim(0, 105)
    ax.legend(fontsize=9)
    ax.set_axisbelow(True)

fig.suptitle('Time-to-Quality CDF', y=1.02)
save_show(fig, CHART_DIR, f'{TAG}-11-time-to-quality.png')
'''


def chart_12_seed_stability():
    """4-12 / 5-12: seed stability box plot."""
    return '''\
# ## 4-12 / 5-12 — Seed Stability (std of gap across seeds)
# ---
# 每个 (solver, dataset, instance) 在 2 seeds 上算 std(gap)；箱图看分布
# std 越小 = 算法越稳定

rows = []
for (sv, d, inst), g in df.groupby(['solver', 'dataset', 'instance']):
    if g['seed'].nunique() >= 2:
        rows.append({'solver': sv, 'dataset': d, 'std': g['gap'].std(ddof=0)})
stab = pd.DataFrame(rows)

fig, ax = plt.subplots(figsize=(10, 5))
order_sv = [(BASE_NAME, BASE_COLOR), (IMP_NAME, IMP_COLOR)]
data_box, labels_box, colors_box = [], [], []
for d in ['T1', 'T2']:
    for sv, col in order_sv:
        s = stab[(stab.solver == sv) & (stab.dataset == d)]['std'].values
        data_box.append(s)
        labels_box.append(f'{sv}\\n{d}\\nn={len(s)}')
        colors_box.append(col)

bp = ax.boxplot(data_box, labels=labels_box, patch_artist=True, widths=0.6,
                showfliers=True, medianprops=dict(color='black', linewidth=2))
for patch, col in zip(bp['boxes'], colors_box):
    patch.set_facecolor(col); patch.set_alpha(0.7)
ax.set_ylabel('std(gap) across 2 seeds')
ax.set_title('Seed stability')
ax.set_yscale('symlog', linthresh=1e-5)
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, f'{TAG}-12-seed-stability.png')
'''


def causal_pie_cell():
    return '''\
# ## Causal Pie — where does the gap improvement come from?
# ---
# 用 merged.cause：LB-driven / UB-driven / Both / Neither
fig, ax = plt.subplots(figsize=(7, 6))
cats = ['LB-driven', 'Both', 'UB-driven', 'Neither']
sizes = [int((merged.cause == c).sum()) for c in cats]
colors = [IMP_COLOR, PURPLE, ORANGE, LIGHT_GRAY]
total = sum(sizes)
labels = [f'{c}\\n{s}  ({s/total*100:.1f}%)' for c, s in zip(cats, sizes)]
ax.pie(sizes, labels=labels, colors=colors, startangle=90,
       wedgeprops=dict(edgecolor='white', linewidth=2),
       textprops=dict(fontsize=12))
ax.set_title(f'Causal decomposition — {IMP_NAME} vs {BASE_NAME}  (T1+T2, n={total})')
save_show(fig, CHART_DIR, f'{TAG}-causal-pie.png')
'''


def timeout_subset_cell():
    return '''\
# ## TIMEOUT / Hard-instance subset
# ---
# 只看 status 有 TIMEOUT 的实例（baseline 或 imp 任一方超时）
# 结论模板：这些"难例"上改进是否仍然存在？
hard_inst = set()
for sv in [IMP_NAME, BASE_NAME]:
    sub = df[(df.solver == sv) & (df.status == 'TIMEOUT')]
    hard_inst.update(zip(sub['dataset'], sub['instance']))
print(f'hard (TIMEOUT) instances: {len(hard_inst)}')

if hard_inst:
    mask = merged.apply(lambda r: (r['dataset'], r['instance']) in hard_inst, axis=1)
    hm = merged[mask]
    print('subset size:', len(hm))
    print(hm.groupby('dataset').agg(
        base_avg_gap=('gap_base', 'mean'),
        imp_avg_gap=('gap_imp', 'mean'),
        win_pct=('win', lambda x: (x == 1).mean() * 100),
    ).round(4))
else:
    print('no TIMEOUT instances in this experiment')
'''


def newly_optimal_cell():
    return '''\
# ## Newly optimal instances
# ---
# imp 解到最优 (gap=0) 而 base 没有；列 instance 级清单便于写报告

eps = 1e-9
new_opt = merged[(merged['gap_imp'] <= eps) & (merged['gap_base'] > eps)]
lost_opt = merged[(merged['gap_imp'] > eps) & (merged['gap_base'] <= eps)]

print(f'Newly-optimal (imp solves, base doesn\\'t): {len(new_opt)}')
print(new_opt[['dataset','instance','V','E','best_lb_imp','best_ub_imp',
               'best_lb_base','best_ub_base','d_gap']].to_string(index=False))

print(f'\\nLost-optimal (base solves, imp doesn\\'t): {len(lost_opt)}')
print(lost_opt[['dataset','instance','V','E','best_lb_imp','best_ub_imp',
                'best_lb_base','best_ub_base','d_gap']].to_string(index=False))
'''


# =============================================================================
# exp4 / exp5 notebook assembly (symmetric)
# =============================================================================

def build_exp_notebook(exp_name: str, title: str, out_path: Path):
    nb = new_notebook()
    cells = []

    cells.append(new_markdown_cell(
        f'# {title}\n\n'
        f'分析 `{exp_name}` 的 paper-config 全量实验结果。\n\n'
        f'- baseline vs 改进版：`{exp_name}` = '
        f'{"dual-deep vs deep-v6" if exp_name == "exp4" else "dual-fast vs fast-v19"}\n'
        f'- 每张图按维度 D1..D8 拆分（见 `report/` 的 plan）\n'
        f'- 所有图自动落到 `./charts/`'
    ))

    cells.append(new_code_cell(f'EXP_NAME = "{exp_name}"\n' + EXP_SETUP))

    chart_funcs = [
        ('## D1 总体效果', [chart_01_headline, chart_02_threshold]),
        ('## D2 逐实例胜负', [chart_03_winloss, chart_04_dgap_hist]),
        ('## D3 LB / UB 分解', [chart_05_lb_scatter, chart_06_ub_scatter, chart_07_lbub_pct]),
        ('## D4 规模效应 (V)', [chart_08_by_V]),
        ('## D5 密度效应 (E/V)', [chart_09_by_density]),
        ('## D6 时序演化', [chart_10_convergence, chart_11_time2quality]),
        ('## D7 种子稳定性', [chart_12_seed_stability]),
        ('## D3 因果总结', [causal_pie_cell]),
        ('## D8 难例子集 (TIMEOUT)', [timeout_subset_cell]),
        ('## D9 Newly / Lost optimal', [newly_optimal_cell]),
    ]
    for heading, fns in chart_funcs:
        cells.append(new_markdown_cell(heading))
        for fn in fns:
            cells.append(new_code_cell(fn()))

    nb['cells'] = cells
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open('w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print(f'wrote {out_path}')


# =============================================================================
# main (cross-exp) notebook
# =============================================================================

MAIN_SETUP = """\
import sys
sys.path.insert(0, '.')
from _style import *

CHART_DIR = Path('charts')
CHART_DIR.mkdir(exist_ok=True)

df4 = load_exp(EXP4_CSV)
df5 = load_exp(EXP5_CSV)

imp4 = per_instance(df4, 'deep-v6')
base4 = per_instance(df4, 'dual-deep')
m4 = pairwise(imp4, base4)

imp5 = per_instance(df5, 'fast-v19')
base5 = per_instance(df5, 'dual-fast')
m5 = pairwise(imp5, base5)

print('exp-4 merged:', len(m4), 'exp-5 merged:', len(m5))
"""

MAIN_M01 = '''\
# ## M-01 — Headline avg + median gap (4 solvers × 2 datasets)
fig, ax = plt.subplots(figsize=(12, 5.5))

pairs = [
    ('dual-deep', 'deep-v6',  df4,  'deep',  GREEN),
    ('dual-fast', 'fast-v19', df5,  'fast',  BLUE),
]
x = np.arange(4) * 1.5  # 4 group positions (deepT1 deepT2 fastT1 fastT2)
w = 0.32
xs_base = []; xs_imp = []
group_pos = [0, 1, 2, 3]
labels = []
max_avg = 0
for bn, imn, dfx, fam, col in pairs:
    for i, d in enumerate(['T1', 'T2']):
        idx = (0 if fam == 'deep' else 2) + i
        sub_imp = dfx[(dfx.solver == imn) & (dfx.dataset == d)]
        sub_base = dfx[(dfx.solver == bn) & (dfx.dataset == d)]
        avg_b = sub_base.groupby('instance')['gap'].mean().mean()
        avg_i = sub_imp.groupby('instance')['gap'].mean().mean()
        med_b = sub_base.groupby('instance')['gap'].mean().median()
        med_i = sub_imp.groupby('instance')['gap'].mean().median()
        max_avg = max(max_avg, avg_b, avg_i)
        ax.bar(x[idx] - 1.5*w, avg_b, w, color=GRAY, edgecolor='black', linewidth=0.8)
        ax.bar(x[idx] - 0.5*w, avg_i, w, color=col, edgecolor='black', linewidth=0.8)
        ax.bar(x[idx] + 0.5*w, med_b, w, color=GRAY, edgecolor='black', linewidth=0.8, hatch='//', alpha=0.85)
        ax.bar(x[idx] + 1.5*w, med_i, w, color=col, edgecolor='black', linewidth=0.8, hatch='//', alpha=0.85)
        pct = (avg_i - avg_b) / max(avg_b, 1e-12) * 100
        yt = max(avg_b, avg_i) * 1.08 + 0.002
        ax.annotate(f'{pct:+.1f}%', (x[idx] - w, yt), ha='center', fontsize=11,
                    color=RED if pct < 0 else GREEN, fontweight='bold')
        labels.append(f'{fam}\\n{d}')

ax.set_xticks(x); ax.set_xticklabels(labels)
ax.set_ylabel('gap (avg solid / median hatched)')
ax.set_title('Headline — average & median gap, improvement vs baseline')
ax.set_ylim(0, max_avg * 1.22)
legend_handles = [
    plt.Rectangle((0,0), 1, 1, color=GRAY, label='baseline avg'),
    plt.Rectangle((0,0), 1, 1, color=GREEN, label='deep-v6 avg'),
    plt.Rectangle((0,0), 1, 1, color=BLUE,  label='fast-v19 avg'),
    plt.Rectangle((0,0), 1, 1, color=GRAY, hatch='//', alpha=0.6, label='baseline median'),
]
ax.legend(handles=legend_handles, fontsize=10, loc='upper right')
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, 'M-01-headline.png')
'''

MAIN_M02 = '''\
# ## M-02 — Table 3 format heatmap (all 4 solvers)
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
thresh_labels = [t[0] for t in THRESHOLDS]
for ax, d in zip(axes, ['T1', 'T2']):
    mat = []
    row_labels = []
    for (agg, name) in [(base4, 'dual-deep'), (imp4, 'deep-v6'),
                         (base5, 'dual-fast'), (imp5, 'fast-v19')]:
        tb = threshold_table(agg[agg.dataset == d])
        n = tb['n'].iloc[0]
        mat.append([tb[l].iloc[0] / n * 100 for l in thresh_labels])
        row_labels.append(name)
    arr = np.array(mat)
    im = ax.imshow(arr, aspect='auto', cmap='YlGn', vmin=0, vmax=100)
    for i in range(arr.shape[0]):
        for j in range(arr.shape[1]):
            ax.text(j, i, f'{arr[i,j]:.0f}', ha='center', va='center',
                    fontsize=11, color='black' if arr[i,j] < 60 else 'white')
    ax.set_xticks(range(len(thresh_labels))); ax.set_xticklabels(thresh_labels)
    ax.set_yticks(range(len(row_labels))); ax.set_yticklabels(row_labels)
    ax.set_title(f'{d} — % instances at each threshold')
    fig.colorbar(im, ax=ax, fraction=0.04)
fig.suptitle('Table-3-style threshold heatmap  (color = % instances at ≤ x)', y=1.02)
save_show(fig, CHART_DIR, 'M-02-threshold-heatmap.png')
'''

MAIN_M03 = '''\
# ## M-03 — Win/Tie/Loss 2×2 pie
fig, axes = plt.subplots(2, 2, figsize=(11, 10))
cells_cfg = [
    (m4, 'T1', 'deep-v6 vs dual-deep · T1', GREEN),
    (m4, 'T2', 'deep-v6 vs dual-deep · T2', GREEN),
    (m5, 'T1', 'fast-v19 vs dual-fast · T1', BLUE),
    (m5, 'T2', 'fast-v19 vs dual-fast · T2', BLUE),
]
for ax, (m, d, ttl, col) in zip(axes.flat, cells_cfg):
    sub = m[m.dataset == d]
    w = (sub.win == 1).sum(); t = (sub.win == 0).sum(); l = (sub.win == -1).sum()
    n = len(sub)
    labels = [f'Win {w}\\n({w/n*100:.1f}%)',
              f'Tie {t}\\n({t/n*100:.1f}%)',
              f'Loss {l}\\n({l/n*100:.1f}%)']
    ax.pie([w, t, l], labels=labels, colors=[col, LIGHT_GRAY, RED], startangle=90,
           wedgeprops=dict(edgecolor='white', linewidth=2), textprops=dict(fontsize=11))
    ax.set_title(f'{ttl}  (n={n})', fontsize=13)
fig.suptitle('Per-instance Win / Tie / Loss — all 4 quadrants', y=1.01)
save_show(fig, CHART_DIR, 'M-03-win-tie-loss.png')
'''

MAIN_M04 = '''\
# ## M-04 — Causal decomposition stacked bar
fig, ax = plt.subplots(figsize=(11, 5.5))
cats = ['LB-driven', 'Both', 'UB-driven', 'Neither']
colors = [GREEN, PURPLE, ORANGE, LIGHT_GRAY]
labels_x = ['deep T1', 'deep T2', 'fast T1', 'fast T2']

groups_data = []
for m, d in [(m4, 'T1'), (m4, 'T2'), (m5, 'T1'), (m5, 'T2')]:
    sub = m[m.dataset == d]
    counts = [int((sub.cause == c).sum()) for c in cats]
    n = sum(counts)
    groups_data.append([v/n*100 for v in counts])

arr = np.array(groups_data)
bottoms = np.zeros(len(labels_x))
for i, (c, col) in enumerate(zip(cats, colors)):
    ax.bar(labels_x, arr[:, i], bottom=bottoms, color=col,
           edgecolor='white', linewidth=1, label=c)
    for j, v in enumerate(arr[:, i]):
        if v > 4:
            ax.text(j, bottoms[j] + v/2, f'{v:.0f}%', ha='center', va='center',
                    fontsize=11, color='white' if c != 'Neither' else 'black',
                    fontweight='bold')
    bottoms += arr[:, i]

ax.set_ylabel('% of instances')
ax.set_ylim(0, 105)
ax.set_title('Causal decomposition — what caused the gap change?')
ax.legend(fontsize=11, loc='upper right')
ax.set_axisbelow(True)
save_show(fig, CHART_DIR, 'M-04-causal-decomposition.png')
'''

MAIN_M05 = '''\
# ## M-05 — Performance Profile (Dolan-Moré style)
# τ=1 时的值 = 在 "每个 instance 上它是最好的" 实例比例
# τ→∞ 时 = 1 (最终都 ≤ τ × best)

fig, axes = plt.subplots(1, 2, figsize=(13, 5.5))
for ax, d in zip(axes, ['T1', 'T2']):
    imp_gap4 = imp4[imp4.dataset == d].set_index('instance')['gap']
    base_gap4 = base4[base4.dataset == d].set_index('instance')['gap']
    imp_gap5 = imp5[imp5.dataset == d].set_index('instance')['gap']
    base_gap5 = base5[base5.dataset == d].set_index('instance')['gap']
    # align instances present in *all* (for per-family pairs we just need family pair).
    # We'll plot deep family (2 series) and fast family (2 series) independently.
    for sv_name, series, col in [('dual-deep', base_gap4, GRAY),
                                  ('deep-v6',  imp_gap4,  GREEN),
                                  ('dual-fast', base_gap5, GRAY),
                                  ('fast-v19',  imp_gap5,  BLUE)]:
        # pair with its own family's best for performance profile
        if sv_name in ('dual-deep', 'deep-v6'):
            pair = pd.concat([base_gap4, imp_gap4], axis=1, join='inner')
            pair.columns = ['a', 'b']
            best = pair.min(axis=1)
            r = (series.reindex(pair.index) / best.replace(0, np.nan)).dropna()
        else:
            pair = pd.concat([base_gap5, imp_gap5], axis=1, join='inner')
            pair.columns = ['a', 'b']
            best = pair.min(axis=1)
            r = (series.reindex(pair.index) / best.replace(0, np.nan)).dropna()
        # Special case: both zero -> both optimal -> ratio = 1 (solved)
        # We pre-filter: best==0 rows -> if series==0 ratio=1 else =inf
        both_zero = (best == 0) & (series.reindex(pair.index) == 0)
        if sv_name in ('dual-deep','deep-v6'):
            r = series.reindex(pair.index).copy()
            ratios = []
            for inst, val in r.items():
                b = best.loc[inst]
                if b == 0 and val == 0: ratios.append(1.0)
                elif b == 0: ratios.append(np.inf)
                else: ratios.append(val / b)
            r = pd.Series(ratios, index=r.index)
        else:
            r = series.reindex(pair.index).copy()
            ratios = []
            for inst, val in r.items():
                b = best.loc[inst]
                if b == 0 and val == 0: ratios.append(1.0)
                elif b == 0: ratios.append(np.inf)
                else: ratios.append(val / b)
            r = pd.Series(ratios, index=r.index)
        taus = np.logspace(0, 3, 200)
        y = [(r <= t).mean() * 100 for t in taus]
        marker = 's' if sv_name in ('deep-v6','fast-v19') else 'o'
        ls = '--' if sv_name.startswith('dual-') else '-'
        ax.plot(taus, y, color=col, linestyle=ls, linewidth=2, label=sv_name)
    ax.set_xscale('log')
    ax.set_xlabel('τ   (performance ratio)')
    ax.set_ylabel('% instances with gap ≤ τ × best-in-family')
    ax.set_title(f'{d}')
    ax.set_ylim(0, 102)
    ax.legend(fontsize=10, loc='lower right')
    ax.set_axisbelow(True)
fig.suptitle('Performance profiles — within each family', y=1.02)
save_show(fig, CHART_DIR, 'M-05-performance-profile.png')
'''

MAIN_M06 = '''\
# ## M-06 — Convergence curves, 4 solvers
fig, axes = plt.subplots(1, 2, figsize=(13, 5))
for ax, d in zip(axes, ['T1', 'T2']):
    for sv, col, marker in [('dual-deep', GRAY, 'o'),
                             ('deep-v6',  GREEN, 's'),
                             ('dual-fast', GRAY, 'd'),
                             ('fast-v19',  BLUE,  '^')]:
        dfx = df4 if sv in ('dual-deep','deep-v6') else df5
        ts, ys = gap_curve(dfx, sv, d)
        ls = '--' if sv.startswith('dual-') else '-'
        ax.plot(ts, ys, color=col, linestyle=ls, linewidth=2.2, marker=marker,
                label=sv)
    ax.set_xscale('log')
    ax.set_xlabel('time (s)')
    ax.set_ylabel('avg gap')
    ax.set_title(d)
    ax.legend(fontsize=10)
    ax.set_axisbelow(True)
fig.suptitle('Convergence curves — all 4 solvers', y=1.02)
save_show(fig, CHART_DIR, 'M-06-convergence.png')
'''


def build_main_notebook(out_path: Path):
    nb = new_notebook()
    cells = []
    cells.append(new_markdown_cell(
        '# Main Report — Cross-Experiment Analysis\n\n'
        '把 exp-4 (deep) 和 exp-5 (fast) 两条改进线放在同一幅报告里对比：'
        '双柱 / 阈值热图 / 胜负 2×2 / 因果堆叠 / Performance Profile / 收敛曲线。'
    ))
    cells.append(new_code_cell(MAIN_SETUP))
    cells.append(new_markdown_cell('## D1 总体 + 阈值'))
    cells.append(new_code_cell(MAIN_M01))
    cells.append(new_code_cell(MAIN_M02))
    cells.append(new_markdown_cell('## D2 逐实例胜负'))
    cells.append(new_code_cell(MAIN_M03))
    cells.append(new_markdown_cell('## D3 因果分解'))
    cells.append(new_code_cell(MAIN_M04))
    cells.append(new_markdown_cell('## D1 (多维) Performance Profile'))
    cells.append(new_code_cell(MAIN_M05))
    cells.append(new_markdown_cell('## D6 时序'))
    cells.append(new_code_cell(MAIN_M06))
    nb['cells'] = cells
    with out_path.open('w', encoding='utf-8') as f:
        nbformat.write(nb, f)
    print(f'wrote {out_path}')


# =============================================================================
# main
# =============================================================================
if __name__ == '__main__':
    build_exp_notebook('exp4',
                       'Exp-4 Analysis  —  Dual-Deep (baseline) vs Deep-v6',
                       HERE / 'exp4' / 'analysis.ipynb')
    build_exp_notebook('exp5',
                       'Exp-5 Analysis  —  Dual-Fast (baseline) vs Fast-v19',
                       HERE / 'exp5' / 'analysis.ipynb')
    build_main_notebook(HERE / 'main.ipynb')
