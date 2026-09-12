"""生成模拟电商订单数据（含趋势/季节性/客户分层/商品组合/脏数据），用于演示与测试。

用法:
    python -m examples.make_sample_data --rows 6000 --out sample_data
"""

from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np
import pandas as pd

CATEGORIES: dict[str, tuple[float, float]] = {  # 品类: (均价, 价格波动系数)
    "手机数码": (1500, 0.4),
    "家居生活": (180, 0.5),
    "美妆个护": (120, 0.4),
    "食品饮料": (45, 0.5),
    "服饰鞋包": (260, 0.5),
    "运动户外": (320, 0.45),
}
CAT_WEIGHTS = {"手机数码": 0.18, "家居生活": 0.22, "美妆个护": 0.18,
               "食品饮料": 0.17, "服饰鞋包": 0.15, "运动户外": 0.10}
# 配件商品：与指定“手机”高频同单，制造可被购物篮发现的关联规则
BUNDLE = {"P-BUD-01": ("蓝牙耳机", 199), "P-BUD-02": ("手机壳", 39), "P-BUD-03": ("充电器", 89)}
# 手机爆款及其固定搭配的配件（P001 主推 P-BUD-01，P002 主推 P-BUD-02）
PHONES = {"P001": "P-BUD-01", "P002": "P-BUD-02"}


def _build_products() -> pd.DataFrame:
    rows = []
    n = 0
    for cat, (mean_price, cv) in CATEGORIES.items():
        for k in range(6):
            n += 1
            rows.append(
                {
                    "product_id": f"P{n:03d}",
                    "product_name": f"{cat}商品{k + 1}",
                    "category": cat,
                    "unit_price": round(mean_price * (0.4 + abs(np.random.default_rng(n).normal(0, cv))), 2),
                }
            )
    for pid, (name, price) in BUNDLE.items():  # 配件商品也登记入表，供购物篮/ABC 使用
        rows.append({"product_id": pid, "product_name": name, "category": "手机数码",
                     "unit_price": float(price)})
    return pd.DataFrame(rows)


def make_sample_data(out_dir: str | Path = "sample_data", rows: int = 6000,
                     seed: int = 42) -> tuple[Path, Path]:
    """生成 sample_sales.csv 与 sample_events.csv，返回两个文件路径。"""
    rng = np.random.default_rng(seed)
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    np.random.seed(seed)

    products = _build_products()
    cat_products = {c: g["product_id"].tolist() for c, g in products.groupby("category")}
    pinfo = products.set_index("product_id")

    n_customers = max(50, rows // 12)
    customer_ids = [f"C{i:04d}" for i in range(n_customers)]
    ranks = np.arange(1, n_customers + 1)
    cust_weights = 1.0 / ranks ** 0.9  # 少数大客户贡献多数订单
    cust_weights /= cust_weights.sum()

    start = pd.Timestamp("2025-01-01")
    end = pd.Timestamp("2026-08-31")
    days = pd.date_range(start, end, freq="D")
    trend = np.linspace(1.0, 1.4, len(days))                      # 整体增长
    weekly = 1 + 0.25 * (days.dayofweek >= 5)                     # 周末更高
    promo = np.where(days.strftime("%m%d").isin(["1111", "1110", "0618", "0617"]), 2.6, 1.0)
    day_weights = trend * weekly * promo
    day_weights /= day_weights.sum()

    records: list[dict] = []
    oid = 0
    while len(records) < rows:
        oid += 1
        day = rng.choice(days, p=day_weights)
        cust = rng.choice(customer_ids, p=cust_weights)
        n_lines = rng.choice([1, 2, 3], p=[0.55, 0.32, 0.13])
        main_cat = rng.choice(list(CAT_WEIGHTS), p=list(CAT_WEIGHTS.values()))
        if main_cat == "手机数码" and rng.random() < 0.7:
            chosen = [rng.choice(list(PHONES))]  # 手机数码订单 70% 是爆款手机
        else:
            chosen = [rng.choice(cat_products[main_cat])]
        for _ in range(n_lines - 1):
            if chosen[0] in PHONES and rng.random() < 0.8:
                chosen.append(PHONES[chosen[0]])  # 手机 + 指定配件强绑定
            elif chosen[0] in cat_products["手机数码"] and rng.random() < 0.4:
                chosen.append(rng.choice(list(BUNDLE)))  # 其他数码单随机搭配件
            else:
                chosen.append(rng.choice(list(products["product_id"])))
        for pid in chosen:
            qty = int(rng.integers(1, 6)) if pinfo.loc[pid, "category"] == "食品饮料" else int(rng.integers(1, 4))
            price = float(pinfo.loc[pid, "unit_price"])
            records.append(
                {
                    "订单号": f"SO{oid:06d}",
                    "下单日期": day,
                    "客户ID": cust,
                    "商品ID": pid,
                    "品类": pinfo.loc[pid, "category"],
                    "数量": qty,
                    "单价": price,
                    "金额": round(qty * price, 2),
                }
            )
    df = pd.DataFrame(records).head(rows)

    # ---- 注入脏数据，演示清洗流程 ----
    df.loc[df.sample(frac=0.005, random_state=seed).index, "金额"] = np.nan      # 缺失金额（可回填）
    dup = df.sample(n=min(30, rows // 50), random_state=seed)                    # 完全重复行
    df = pd.concat([df, dup], ignore_index=True)
    big = df.sample(n=max(3, rows // 800), random_state=seed).index              # 极端大额
    df.loc[big, "金额"] = df.loc[big, "金额"] * 20
    df = df.sample(frac=1.0, random_state=seed).reset_index(drop=True)           # 打乱

    sales_path = out_dir / "sample_sales.csv"
    df.to_csv(sales_path, index=False, encoding="utf-8-sig")

    # ---- 转化事件：浏览 -> 加购 -> 下单 -> 支付（每一步先筛选幸存者再记录事件）----
    users = [f"U{i:04d}" for i in range(1500)]
    stages = [("visit", 1.0), ("cart", 0.38), ("order", 0.55), ("pay", 0.88)]
    active = list(users)
    ev_rows = []
    base = start + pd.Timedelta(days=int(rng.integers(0, 200)))
    for i, (name, keep) in enumerate(stages):
        if i > 0:
            active = list(rng.choice(active, size=max(1, int(len(active) * keep)), replace=False))
        for u in active:
            for _ in range(int(rng.integers(1, 8))):
                ev_rows.append(
                    {"user_id": u, "event_type": name,
                     "event_date": base + pd.Timedelta(days=int(rng.integers(0, 180)))}
                )
    events = pd.DataFrame(ev_rows)
    events_path = out_dir / "sample_events.csv"
    events.to_csv(events_path, index=False, encoding="utf-8-sig")

    print(f"已生成: {sales_path}（{len(df):,} 行订单明细, 含缺失/重复/异常值）")
    print(f"        {events_path}（{len(events):,} 条转化事件）")
    return sales_path, events_path


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="生成模拟电商数据")
    ap.add_argument("--rows", type=int, default=6000)
    ap.add_argument("--out", default="sample_data")
    make_sample_data(**vars(ap.parse_args()))
