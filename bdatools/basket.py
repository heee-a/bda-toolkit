"""购物篮分析：纯 pandas 实现的关联规则挖掘（支持度/置信度/提升度）。

适合中等规模订单数据（订单内商品组合数 ≤ 数十）。只需 pandas，无额外依赖。
"""

from __future__ import annotations

from collections import Counter
from itertools import combinations
from pathlib import Path

import pandas as pd

from .plotting import save_chart, setup_style


def _transactions(df: pd.DataFrame, transaction_col: str, item_col: str) -> list[frozenset]:
    tx = (
        df[[transaction_col, item_col]]
        .dropna()
        .groupby(transaction_col)[item_col]
        .agg(lambda s: frozenset(map(str, s.unique())))
    )
    return [t for t in tx if t]


def association_rules(
    df: pd.DataFrame,
    transaction_col: str = "order_id",
    item_col: str = "product_id",
    min_support: float = 0.02,
    min_confidence: float = 0.1,
    max_items_per_tx: int | None = 50,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """挖掘频繁项集与关联规则（1-项集与 2-项集）。

    Parameters
    ----------
    min_support : 最小支持度（订单中同时出现的比例）
    min_confidence : 最小置信度
    max_items_per_tx : 每单商品种类数上限，防极端大单拖慢速度

    Returns
    -------
    (itemsets, rules)
    itemsets : itemset, support, count
    rules    : antecedent, consequent, support, confidence, lift
    """
    tx = _transactions(df, transaction_col, item_col)
    n_tx = len(tx)
    if n_tx == 0:
        raise ValueError("没有有效订单（每单至少需要 1 个商品）")

    item_cnt: Counter[str] = Counter()
    pair_cnt: Counter[tuple[str, str]] = Counter()
    for t in tx:
        items = sorted(t)[:max_items_per_tx] if max_items_per_tx else sorted(t)
        for it in items:
            item_cnt[it] += 1
        for a, b in combinations(items, 2):
            pair_cnt[(a, b)] += 1

    itemsets = pd.DataFrame(
        [
            {"itemset": it, "count": c, "support": round(c / n_tx, 4)}
            for it, c in item_cnt.items()
        ]
    ).sort_values("support", ascending=False, ignore_index=True)
    itemsets = itemsets[itemsets["support"] >= min_support].reset_index(drop=True)

    rules: list[dict] = []
    for (a, b), cab in pair_cnt.items():
        support_ab = cab / n_tx
        if support_ab < min_support:
            continue
        for ante, cons, cnt_ante in ((a, b, item_cnt[a]), (b, a, item_cnt[b])):
            confidence = cab / cnt_ante
            if confidence < min_confidence:
                continue
            support_cons = item_cnt[cons] / n_tx
            rules.append(
                {
                    "antecedent": ante,
                    "consequent": cons,
                    "support": round(support_ab, 4),
                    "confidence": round(confidence, 4),
                    "lift": round(confidence / support_cons, 4),
                }
            )
    rules_df = pd.DataFrame(
        rules,
        columns=["antecedent", "consequent", "support", "confidence", "lift"],
    )
    if len(rules_df):
        rules_df = rules_df.sort_values("lift", ascending=False, ignore_index=True)
    return itemsets, rules_df


def plot_rules(rules: pd.DataFrame, path: str | Path) -> Path:
    """关联规则散点图：x=支持度 y=置信度 点大小=提升度。"""
    import matplotlib.pyplot as plt

    setup_style()
    fig, ax = plt.subplots(figsize=(8, 5.5))
    if len(rules):
        sc = ax.scatter(
            rules["support"],
            rules["confidence"],
            s=(rules["lift"] ** 2) * 8,
            alpha=0.5,
            c=rules["lift"],
            cmap="viridis",
        )
        fig.colorbar(sc, ax=ax, label="提升度 lift")
    ax.set_xlabel("支持度 support")
    ax.set_ylabel("置信度 confidence")
    ax.set_title("关联规则：支持度 × 置信度（气泡越大提升度越高）")
    return save_chart(fig, path)
