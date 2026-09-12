"""用户留存分析：同期群（cohort）留存矩阵，观察各月新增客户的后续复购情况。"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from .plotting import save_chart, setup_style


def cohort_retention(
    df: pd.DataFrame,
    customer_col: str = "customer_id",
    date_col: str = "order_date",
    period: str = "M",
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """计算同期群留存率矩阵。

    Parameters
    ----------
    period : 统计周期，M=月留存（默认），W=周留存，Q=季留存

    Returns
    -------
    (retention, sizes)
    retention : 行=首购月份，列=第 N 期，值=留存率（0~1）
    sizes     : 每个同期群的客户数
    """
    s = df.copy()
    s[date_col] = pd.to_datetime(s[date_col])
    s["order_period"] = s[date_col].dt.to_period(period)
    s["cohort"] = s.groupby(customer_col)["order_period"].transform("min")
    diff = s["order_period"] - s["cohort"]  # Period 之差 = 期数偏移
    s["period_index"] = (
        diff.astype("int64") if diff.dtype.kind in "iu" else diff.map(lambda x: getattr(x, "n", x))
    )

    active = s.groupby(["cohort", "period_index"])[customer_col].nunique().unstack(fill_value=0)
    sizes = active.iloc[:, 0].rename("客户数").to_frame()
    retention = active.div(sizes["客户数"], axis=0).round(4)
    return retention, sizes


def plot_cohort(retention: pd.DataFrame, path: str | Path) -> Path:
    """留存热力图（浅色=流失多，深色=留存高）。"""
    import matplotlib.pyplot as plt

    setup_style()
    fig, ax = plt.subplots(figsize=(10, max(4, 0.5 * len(retention) + 2)))
    data = retention.values
    im = ax.imshow(data, cmap="Blues", vmin=0, vmax=max(0.05, float(data.max())))

    labels = [str(i) for i in retention.index]
    ax.set_xticks(range(retention.shape[1]), [f"第{i}期" for i in retention.columns])
    ax.set_yticks(range(len(labels)), labels)
    ax.set_xlabel("距首次购买")
    ax.set_ylabel("同期群")
    ax.grid(False)
    for i in range(data.shape[0]):
        for j in range(data.shape[1]):
            ax.text(j, i, f"{data[i, j]:.0%}", ha="center", va="center",
                    color="white" if data[i, j] > data.max() * 0.6 else "black", fontsize=8)
    ax.set_title("同期群留存率")
    fig.colorbar(im, ax=ax, shrink=0.8, format="%.0%")
    return save_chart(fig, path)
