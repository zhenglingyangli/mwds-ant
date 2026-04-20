"""Shared style / utils for exp-4 and exp-5 analysis notebooks.

Usage in a notebook:
    import sys; sys.path.append("..")          # for exp4/exp5 notebooks
    from _style import *
"""
from __future__ import annotations

import re
from pathlib import Path

import matplotlib
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

# -------------------------------------------------------------------------
# paths
# -------------------------------------------------------------------------
ROOT = Path("/home/ylzl/WMDS26")
EXP4_CSV = ROOT / "exp-4/sumup/analysis/exp4_results.csv"
EXP5_CSV = ROOT / "exp-5/sumup/analysis/exp2_results.csv"
REPORT_DIR = ROOT / "report"

# -------------------------------------------------------------------------
# palette (aligned with Ant-QO/charts/charts_review.ipynb)
# -------------------------------------------------------------------------
BLUE = "#2563EB"
GREEN = "#16A34A"
RED = "#DC2626"
ORANGE = "#EA580C"
PURPLE = "#7C3AED"
TEAL = "#0D9488"
AMBER = "#D97706"
GRAY = "#6B7280"
LIGHT_GRAY = "#D1D5DB"

# solver -> color/label/marker
SOLVER_COLOR = {
    "dual-deep": GRAY,
    "deep-v6": GREEN,
    "dual-fast": GRAY,
    "fast-v19": BLUE,
}
SOLVER_LABEL = {
    "dual-deep": "Dual-Deep (baseline)",
    "deep-v6": "Deep-v6 (improved)",
    "dual-fast": "Dual-Fast (baseline)",
    "fast-v19": "Fast-v19 (improved)",
}
SOLVER_MARKER = {
    "dual-deep": "o",
    "deep-v6": "^",
    "dual-fast": "o",
    "fast-v19": "s",
}
DATASET_LABEL = {"T1": "T1 (dense-ish)", "T2": "T2 (sparse-ish)"}

# -------------------------------------------------------------------------
# rcParams
# -------------------------------------------------------------------------
plt.rcParams.update({
    "font.family": "DejaVu Sans",
    "font.size": 14,
    "axes.titlesize": 17,
    "axes.labelsize": 14,
    "figure.facecolor": "white",
    "axes.facecolor": "white",
    "axes.edgecolor": "#CCCCCC",
    "axes.grid": True,
    "grid.color": "#EEEEEE",
    "grid.alpha": 0.8,
    "text.color": "#222222",
})


def save_show(fig, chart_dir: Path, filename: str) -> None:
    """Tight-layout save to <chart_dir>/<filename> and plt.show()."""
    chart_dir = Path(chart_dir)
    chart_dir.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(chart_dir / filename, dpi=200, bbox_inches="tight")
    plt.show()


# -------------------------------------------------------------------------
# data loading / cleaning
# -------------------------------------------------------------------------
_INSTANCE_RX = re.compile(r"T[12]_(\d+)_(\d+)_\d+\.wclq")


def _infer_V_E(instance: str):
    """T1_50_50_3.wclq  ->  (V=50, E=50).  Returns (None, None) if no match."""
    m = _INSTANCE_RX.match(instance)
    if not m:
        return None, None
    return int(m.group(1)), int(m.group(2))


def load_exp(path: Path) -> pd.DataFrame:
    """Load one exp CSV, cross-fill V/E from instance name where they are 0 / NaN."""
    df = pd.read_csv(path)
    # Fill V / E from instance name where missing or zero
    fill_V = df["instance"].map(lambda s: _infer_V_E(s)[0])
    fill_E = df["instance"].map(lambda s: _infer_V_E(s)[1])
    df.loc[df["V"].fillna(0) <= 0, "V"] = fill_V
    df.loc[df["E"].fillna(0) <= 0, "E"] = fill_E
    # Second-pass cross-fill: within (instance), use the max V/E any row reported
    for c in ("V", "E"):
        max_per_inst = df.groupby("instance")[c].transform("max")
        df[c] = df[c].where(df[c] > 0, max_per_inst)
    df["V"] = pd.to_numeric(df["V"], errors="coerce").fillna(0).astype(int)
    df["E"] = pd.to_numeric(df["E"], errors="coerce").fillna(0).astype(int)
    return df


def per_instance(df: pd.DataFrame, solver: str) -> pd.DataFrame:
    """Aggregate seeds -> one row per (dataset, instance).

    - gap   : avg across seeds   (== gap_0 in paper notation)
    - gap_star: min across seeds (== gap* in paper notation)
    - best_lb : max across seeds
    - best_ub : min across seeds
    """
    sub = df[df["solver"] == solver]
    agg = sub.groupby(["dataset", "instance"]).agg(
        V=("V", "max"),
        E=("E", "max"),
        gap=("gap", "mean"),
        gap_star=("gap", "min"),
        best_lb=("best_lb", "max"),
        best_ub=("best_ub", "min"),
        first_lb=("first_lb", "max"),
        first_ub=("first_ub", "min"),
        n_seeds=("seed", "nunique"),
        status_any_timeout=("status", lambda s: (s == "TIMEOUT").any()),
        status_any_opt=("status", lambda s: (s == "OPT").any()),
    ).reset_index()
    return agg


TIME_COLS = ["gap_10s", "gap_60s", "gap_300s", "gap_600s", "gap_1800s", "gap_3600s"]
TIME_SECONDS = [10, 60, 300, 600, 1800, 3600]


def gap_curve(df: pd.DataFrame, solver: str, dataset: str) -> tuple[list[int], list[float]]:
    """Return (times, avg_gap_at_time) for a solver/dataset, using valid checkpoints.

    A checkpoint is considered valid when gap_Xs >= 0. For instances whose
    solver finished earlier than X seconds, checkpoint column is -1 in the CSV;
    we forward-fill those with the final `gap` value (so "finished fast with
    small gap" is properly represented at later times).
    """
    sub = df[(df["solver"] == solver) & (df["dataset"] == dataset)].copy()
    # forward-fill -1 checkpoints with final gap (per row)
    for c in TIME_COLS:
        mask = sub[c] < 0
        sub.loc[mask, c] = sub.loc[mask, "gap"]
    avgs = [sub[c].mean() for c in TIME_COLS]
    return TIME_SECONDS, avgs


# -------------------------------------------------------------------------
# comparison helpers
# -------------------------------------------------------------------------
def pairwise(agg_imp: pd.DataFrame, agg_base: pd.DataFrame,
             on_cols=("dataset", "instance"), eps: float = 1e-6) -> pd.DataFrame:
    """Merge improved vs baseline at per-instance level. Adds:
       d_gap, d_lb, d_ub, win (1/0/-1 by d_gap).
       V/E are merged as single columns (max across sides)."""
    m = agg_imp.merge(agg_base, on=list(on_cols), suffixes=("_imp", "_base"))
    # unify V/E across imp/base (they should be equal; use max to be safe)
    m["V"] = np.maximum(m["V_imp"], m["V_base"])
    m["E"] = np.maximum(m["E_imp"], m["E_base"])
    m["d_gap"] = m["gap_imp"] - m["gap_base"]
    m["d_lb"] = m["best_lb_imp"] - m["best_lb_base"]
    m["d_ub"] = m["best_ub_imp"] - m["best_ub_base"]
    m["win"] = np.where(m["d_gap"] < -eps, 1,
                        np.where(m["d_gap"] > eps, -1, 0))
    # causal bucket (gap only improves when LB tightens and/or UB tightens)
    lb_up = m["best_lb_imp"] > m["best_lb_base"] + eps
    ub_dn = m["best_ub_imp"] < m["best_ub_base"] - eps
    m["cause"] = np.select(
        [lb_up & ub_dn, lb_up & ~ub_dn, ~lb_up & ub_dn],
        ["Both", "LB-driven", "UB-driven"],
        default="Neither",
    )
    return m


def v_bucket(V) -> str:
    """Small / Medium / Large by V (node count)."""
    if V < 100:
        return "Small (V<100)"
    if V < 500:
        return "Medium (100≤V<500)"
    return "Large (V≥500)"


def density_bucket(E_over_V: float) -> str:
    """E/V density buckets (tuned for T1/T2 distributions)."""
    if E_over_V < 1.5:
        return "Sparse (E/V<1.5)"
    if E_over_V < 5:
        return "Medium (1.5≤E/V<5)"
    if E_over_V < 20:
        return "Dense (5≤E/V<20)"
    return "Very Dense (E/V≥20)"


THRESHOLDS = [("#opt", 0.0), ("≤1e-4", 1e-4), ("≤1e-3", 1e-3),
              ("≤1e-2", 1e-2), ("≤1e-1", 1e-1)]


def threshold_table(df_inst: pd.DataFrame, gap_col: str = "gap") -> pd.DataFrame:
    """Table 3 format: for each dataset, fraction of instances at each gap threshold."""
    out = []
    for ds, g in df_inst.groupby("dataset"):
        total = len(g)
        row = {"dataset": ds, "n": total}
        for label, thr in THRESHOLDS:
            if thr == 0.0:
                row[label] = (g[gap_col] <= 1e-9).sum()
            else:
                row[label] = (g[gap_col] <= thr).sum()
        out.append(row)
    return pd.DataFrame(out)


__all__ = [
    "ROOT", "EXP4_CSV", "EXP5_CSV", "REPORT_DIR",
    "BLUE", "GREEN", "RED", "ORANGE", "PURPLE", "TEAL", "AMBER", "GRAY", "LIGHT_GRAY",
    "SOLVER_COLOR", "SOLVER_LABEL", "SOLVER_MARKER", "DATASET_LABEL",
    "save_show", "load_exp", "per_instance",
    "TIME_COLS", "TIME_SECONDS", "gap_curve",
    "pairwise", "v_bucket", "density_bucket", "THRESHOLDS", "threshold_table",
    "Path", "np", "pd", "plt", "mticker", "matplotlib",
]
