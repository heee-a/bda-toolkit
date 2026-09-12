"""销售趋势分析：期间汇总、环比/同比增长率、移动平均、趋势图。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .plotting import save_chart, setup_style

# 每种统计周期对应的“去年同期”回退步数
_PERIOD_STEPS = {"D": 365, "W": 52, "M": 12, "Q": 4, "Y": 1}


def _validate_freq(freq: str) -> str:
    f = freq.upper()
    if f not in _PERIOD_STEPS:
        raise ValueError(f"freq 需为 {sorted(_PERIOD_STEPS)} 之一，收到: {freq}")
    return f


def period_summary(
    df: pd.DataFrame,
    date_col: str = "order_date",
    value_col: str = "amount",
    freq: str = "M",
) -> pd.DataFrame:
    """按统计周期汇总销售额，并计算环比(MoM)与同比(YoY)增长率。

    Returns
    -------
    DataFrame: period, total, mom_pct, yoy_pct（百分比数值，如 12.3 表示 12.3%）
    """
    freq = _validate_freq(freq)
    s = df.copy()
    s[date_col] = pd.to_datetime(s[date_col])
    s["period"] = s[date_col].dt.to_period(freq)
    totals = s.groupby("period")[value_col].sum().sort_index()
    out = totals.rename("total").reset_index()
    out["period"] = out["period"].astype(str)

    steps = _PERIOD_STEPS[freq]
    idx = totals.index
    prev1 = pd.Series({p: totals.get(p - 1) for p in idx})   # 环比：上一期
    prev_y = pd.Series({p: totals.get(p - steps) for p in idx})  # 同比：去年同期
    out["mom_pct"] = ((totals.values / prev1.values) - 1).round(4) * 100
    out["yoy_pct"] = ((totals.values / prev_y.values) - 1).round(4) * 100
    return out


def moving_average(
    df: pd.DataFrame,
    date_col: str = "order_date",
    value_col: str = "amount",
    freq: str = "D",
    window: int = 7,
) -> pd.DataFrame:
    """按日/周等周期汇总后计算移动平均，平滑短期波动看趋势。"""
    freq = _validate_freq(freq)
    s = df.copy()
    s[date_col] = pd.to_datetime(s[date_col])
    s["period"] = s[date_col].dt.to_period(freq)
    totals = s.groupby("period")[value_col].sum().sort_index()
    out = totals.rename("total").reset_index()
    out["period"] = out["period"].astype(str)
    out[f"ma{window}"] = totals.rolling(window, min_periods=max(1, window // 3)).mean().round(2).values
    return out


def plot_trend(summary: pd.DataFrame, path: str | Path, title: str = "销售额趋势") -> Path:
    """销售额趋势图：柱状为期间销售额，折线为环比增长率。"""
    import matplotlib.pyplot as plt

    setup_style()
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = summary["period"].astype(str)
    ax1.bar(x, summary["total"], color="#4C72B0", alpha=0.85, label="销售额")
    ax1.set_ylabel("销售额")
    ax1.tick_params(axis="x", rotation=45)

    if "mom_pct" in summary.columns:
        ax2 = ax1.twinx()
        ax2.plot(x, summary["mom_pct"], color="#DD8452", marker="o", label="环比%")
        ax2.axhline(0, color="gray", lw=0.8, ls="--")
        ax2.set_ylabel("环比增长率 %")
        ax2.grid(False)

    ax1.set_title(title)
    fig.tight_layout()
    return save_chart(fig, path)
