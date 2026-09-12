"""ABC / 帕累托分析：找出贡献 80% 收入的关键少数品类/商品/客户。"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from .plotting import save_chart, setup_style


def abc_analysis(
    df: pd.DataFrame,
    item_col: str = "category",
    value_col: str = "amount",
    thresholds: tuple[float, float] = (0.7, 0.9),
) -> pd.DataFrame:
    """按累计占比划分 ABC 三类。

    A 类：累计贡献 <= 70%；B 类：70%~90%；C 类：其余。
    返回按销售额降序的明细表：total, share_pct, cum_pct, class。
    """
    g = df.groupby(item_col)[value_col].sum().sort_values(ascending=False)
    if g.sum() == 0:
        raise ValueError(f"{value_col} 合计为 0，无法做 ABC 分析")
    out = pd.DataFrame(
        {
            item_col: g.index,
            "total": g.values,
            "share_pct": (g.values / g.sum() * 100).round(2),
        }
    )
    out["cum_pct"] = out["share_pct"].cumsum().round(2)
    t1, t2 = thresholds
    out["class"] = np.where(out["cum_pct"] <= t1 * 100, "A", np.where(out["cum_pct"] <= t2 * 100, "B", "C"))
    return out


def class_summary(abc: pd.DataFrame, item_col: str = "category") -> pd.DataFrame:
    """A/B/C 三类的汇总：项数、销售占比。"""
    g = abc.groupby("class").agg(
        项数=(item_col, "count"),
        销售额=("total", "sum"),
    )
    g["销售额占比%"] = (g["销售额"] / g["销售额"].sum() * 100).round(2)
    return g.reindex(["A", "B", "C"]).reset_index().round(2)


def plot_pareto(abc: pd.DataFrame, item_col: str, path: str | Path) -> Path:
    """帕累托图：柱状为各单品/品类销售额，折线为累计占比，标出 80% 分界线。"""
    import matplotlib.pyplot as plt

    setup_style()
    fig, ax1 = plt.subplots(figsize=(10, 5))
    x = abc[item_col].astype(str)
    colors = {"A": "#C44E52", "B": "#4C72B0", "C": "#8C8C8C"}
    ax1.bar(x, abc["total"], color=[colors[c] for c in abc["class"]])
    ax1.set_ylabel("销售额")
    ax1.tick_params(axis="x", rotation=45)

    ax2 = ax1.twinx()
    ax2.plot(x, abc["cum_pct"], color="#DD8452", marker="o", lw=1.5)
    ax2.axhline(80, color="gray", ls="--", lw=0.8)
    ax2.set_ylabel("累计占比 %")
    ax2.set_ylim(0, 105)
    ax2.grid(False)

    ax1.set_title(f"{item_col} 帕累托分析（红=A 蓝=B 灰=C）")
    fig.tight_layout()
    return save_chart(fig, path)
