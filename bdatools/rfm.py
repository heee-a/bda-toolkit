"""RFM 客户分层：最近一次消费 R、消费频率 F、消费金额 M。

按 R/F/M 得分（默认 1~5 分位）将客户划分为 8 个经典层级，
输出客户明细与分层汇总，常用于会员运营与精准营销。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .plotting import save_chart, setup_style

# 8 个经典层级：(R高?, F高?, M高?) -> 层级名
_SEGMENTS = {
    (1, 1, 1): "重要价值客户",
    (0, 1, 1): "重要保持客户",
    (1, 0, 1): "重要发展客户",
    (0, 0, 1): "重要挽留客户",
    (1, 1, 0): "一般价值客户",
    (0, 1, 0): "一般保持客户",
    (1, 0, 0): "一般发展客户",
    (0, 0, 0): "一般挽留客户",
}


def _score(series: pd.Series, q: int, reverse: bool = False) -> pd.Series:
    """分位数打分 1..q；小样本或大量并列时自动降级。"""
    ranks = series.rank(method="first")  # 保证 qcut 可切分
    n_bins = max(2, min(q, series.notna().nunique(), len(series)))
    raw = pd.qcut(ranks, q=n_bins, labels=range(1, n_bins + 1)).astype(int)
    if reverse:  # 如 recency 天数越大越差，反转得分
        raw = n_bins + 1 - raw
    return raw


def rfm_score(
    df: pd.DataFrame,
    customer_col: str = "customer_id",
    date_col: str = "order_date",
    amount_col: str = "amount",
    snapshot: pd.Timestamp | str | None = None,
    q: int = 5,
) -> pd.DataFrame:
    """计算每位客户的 RFM 数值与得分。

    Parameters
    ----------
    snapshot : 基准日期，默认取数据中最大订单日期（方便复现）
    q : 每个维度分几档，默认 5 档
    """
    s = df.copy()
    s[date_col] = pd.to_datetime(s[date_col])
    snapshot = pd.Timestamp(snapshot) if snapshot is not None else s[date_col].max()

    agg = s.groupby(customer_col).agg(
        last_purchase=(date_col, "max"),
        frequency=(date_col, "count"),
        monetary=(amount_col, "sum"),
    )
    agg["recency"] = (snapshot - agg["last_purchase"]).dt.days

    agg["R"] = _score(agg["recency"], q, reverse=True)  # 越近买，分越高
    agg["F"] = _score(agg["frequency"], q)
    agg["M"] = _score(agg["monetary"], q)

    med = {k: agg[k].median() for k in ("R", "F", "M")}
    flags = {k: (agg[k] >= med[k]).astype(int) for k in ("R", "F", "M")}
    agg["segment"] = [
        _SEGMENTS[(flags["R"][c], flags["F"][c], flags["M"][c])] for c in agg.index
    ]
    return agg.reset_index().rename(columns={customer_col: "customer"})


SEGMENT_ORDER = list(dict.fromkeys(_SEGMENTS.values()))


def segment_summary(rfm: pd.DataFrame) -> pd.DataFrame:
    """分层汇总：客户数、占比、贡献金额（来自 rfm_score 输出）。"""
    g = rfm.groupby("segment").agg(
        客户数=("customer", "count"),
        人均消费金额=("monetary", "mean"),
        消费总金额=("monetary", "sum"),
    )
    g["客户占比%"] = (g["客户数"] / g["客户数"].sum() * 100).round(2)
    g["金额占比%"] = (g["消费总金额"] / g["消费总金额"].sum() * 100).round(2)
    g = g.reindex([s for s in SEGMENT_ORDER if s in g.index])
    return g.reset_index().round(2)


def plot_segments(summary: pd.DataFrame, path: str | Path) -> Path:
    """分层结果图：客户占比 vs 金额占比对比条形图。"""
    import matplotlib.pyplot as plt
    import numpy as np

    setup_style()
    labels = summary["segment"]
    y = np.arange(len(labels))
    fig, ax = plt.subplots(figsize=(9, 5))
    ax.barh(y + 0.2, summary["客户占比%"], height=0.38, color="#4C72B0", label="客户占比%")
    ax.barh(y - 0.2, summary["金额占比%"], height=0.38, color="#DD8452", label="金额占比%")
    ax.set_yticks(y, labels)
    ax.invert_yaxis()
    ax.set_xlabel("占比 %")
    ax.set_title("RFM 客户分层：客户数占比 vs 消费金额占比")
    ax.legend()
    return save_chart(fig, path)
