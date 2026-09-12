"""转化漏斗：从行为事件表（浏览->加购->下单->支付）计算各步转化率。"""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import pandas as pd

from .plotting import save_chart, setup_style


def funnel_from_events(
    df: pd.DataFrame,
    entity_col: str = "user_id",
    step_col: "str" = "event_type",
    step_order: list[str] | None = None,
) -> pd.DataFrame:
    """从事件明细表构建漏斗。

    Parameters
    ----------
    df : 事件表，每行一条“某用户在某步骤发生”的事件
    step_order : 漏斗步骤顺序；默认按事件首次出现顺序

    Returns
    -------
    step, users, conv_from_prev_pct, conv_from_first_pct
    """
    uniq = df[[entity_col, step_col]].drop_duplicates()
    if step_order is None:
        step_order = list(dict.fromkeys(df[step_col].dropna()))

    rows = []
    for step in step_order:
        users = int(uniq.loc[uniq[step_col] == step, entity_col].nunique())
        rows.append({"step": step, "users": users})
    return _summarize(pd.DataFrame(rows))


def funnel_from_counts(counts: Mapping[str, int]) -> pd.DataFrame:
    """直接从各步骤人数 dict 构建漏斗，如 {"浏览": 10000, "下单": 2400}。"""
    rows = [{"step": k, "users": int(v)} for k, v in counts.items()]
    return _summarize(pd.DataFrame(rows))


def _summarize(steps: pd.DataFrame) -> pd.DataFrame:
    users = steps["users"]
    steps["conv_from_prev_pct"] = (users / users.shift(1) * 100).round(2)
    steps["conv_from_first_pct"] = (users / users.iloc[0] * 100).round(2) if len(users) else users
    return steps


def plot_funnel(summary: pd.DataFrame, path: str | Path) -> Path:
    """居中梯形漏斗图，标注每步人数与上一步转化率。"""
    import matplotlib.pyplot as plt
    import numpy as np

    setup_style()
    users = summary["users"].astype(float)
    widths = users / users.max() if users.max() else users
    y = np.arange(len(summary))[::-1].astype(float)

    fig, ax = plt.subplots(figsize=(9, 4.5))
    for i, (w, row) in enumerate(zip(widths, summary.to_dict("records"))):
        left = (1 - w) / 2
        ax.barh(y[i], w, left=left, height=0.62, color="#4C72B0", alpha=0.55 + 0.45 * w)
        label = f"{row['step']}  {int(row['users']):,}"
        if i > 0 and pd.notna(row.get("conv_from_prev_pct")):
            label += f"  ({row['conv_from_prev_pct']}%)"
        ax.text(0.5, y[i], label, ha="center", va="center", color="white", fontsize=11, weight="bold")
    ax.set_yticks([])
    ax.set_xticks([])
    for spine in ax.spines.values():
        spine.set_visible(False)
    ax.set_title("转化漏斗")
    return save_chart(fig, path)
