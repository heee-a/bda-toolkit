"""bdatools 单元测试：pytest -q"""

from __future__ import annotations

import numpy as np
import pandas as pd

from bdatools import abc, basket, cleaning, cohort, describe, funnel, growth, rfm


def make_sales(n_orders: int = 300, seed: int = 7) -> pd.DataFrame:
    """小型合成订单数据：跨 2024/2025 两年，便于验证同比。"""
    rng = np.random.default_rng(seed)
    rows = []
    for i in range(n_orders):
        day = pd.Timestamp("2024-01-01") + pd.Timedelta(days=int(rng.integers(0, 700)))
        for k in range(rng.integers(1, 4)):
            rows.append(
                {
                    "order_id": f"O{i:05d}",
                    "order_date": day,
                    "customer_id": f"C{rng.integers(0, 60):03d}",
                    "product_id": f"P{rng.integers(1, 11):02d}",
                    "category": f"Cat{rng.integers(1, 5)}",
                    "quantity": int(rng.integers(1, 4)),
                    "unit_price": float(rng.integers(10, 200)),
                }
            )
    df = pd.DataFrame(rows)
    df["amount"] = df["quantity"] * df["unit_price"]
    return df


# ---------------- cleaning ----------------
def test_standardize_columns():
    df = pd.DataFrame({"订单号": [1], "下单日期": ["2025-01-01"], "客户ID": ["C1"], "金额": [10.0]})
    std = cleaning.standardize_columns(df)
    assert list(std.columns) == ["order_id", "order_date", "customer_id", "amount"]


def test_clean_sales_dedup_and_fill():
    df = make_sales(100)
    dirty = df.copy()
    dirty.loc[3, "amount"] = np.nan                     # 注入缺失金额
    dirty = pd.concat([dirty, dirty.head(5)], ignore_index=True)  # 注入 5 行完全重复
    res = cleaning.clean_sales(dirty)
    assert len(res.data) == len(df)  # 完全重复行被去除
    assert len(res.steps) > 0
    # 缺失金额按 数量 × 单价 回填
    oid = df.loc[3, "order_id"]
    row = res.data[res.data["order_id"] == oid].iloc[0]
    assert row["amount"] == row["quantity"] * row["unit_price"]


def test_cap_outliers():
    df = pd.DataFrame({"x": list(range(1, 21)) + [10000]})
    capped = cleaning.cap_outliers(df, "x")
    assert capped["x"].max() < 10000
    assert capped["x"].min() >= 0


def test_missing_profile():
    df = pd.DataFrame({"a": [1, None, 3], "b": [1, 2, 3]})
    mp = cleaning.missing_profile(df)
    assert len(mp) == 1 and mp.iloc[0]["列名"] == "a"


# ---------------- describe ----------------
def test_eda_report():
    tables = describe.eda_report(make_sales(120))
    assert set(tables) == {"总览", "列画像", "缺失情况", "相关性Top10"}
    assert {"quantity", "unit_price", "amount"}.issubset(set(tables["列画像"]["列名"]))


# ---------------- growth ----------------
def test_period_summary_yoy_mom():
    months = pd.period_range("2024-01", "2025-02", freq="M")
    df = pd.DataFrame(
        {
            "order_date": [m.to_timestamp() for m in months],
            "amount": [300.0 if str(m) == "2025-01" else 150.0 for m in months],
        }
    )
    out = growth.period_summary(df, freq="M")
    jan25 = out[out["period"] == "2025-01"].iloc[0]
    assert jan25["total"] == 300.0
    assert jan25["yoy_pct"] == 100.0  # 300 vs 去年同期 150
    feb25 = out[out["period"] == "2025-02"].iloc[0]
    assert feb25["mom_pct"] == -50.0  # 150 vs 上月 300


def test_moving_average():
    df = make_sales(200)
    ma = growth.moving_average(df, window=4)
    assert "ma4" in ma.columns and len(ma) > 4


# ---------------- rfm ----------------
def test_rfm_score_segments():
    df = make_sales(500)
    tbl = rfm.rfm_score(df)
    assert {"customer", "recency", "frequency", "monetary", "R", "F", "M", "segment"}.issubset(tbl.columns)
    assert tbl["segment"].isin(rfm.SEGMENT_ORDER).all()
    assert tbl["R"].between(1, 5).all() and tbl["M"].between(1, 5).all()
    summary = rfm.segment_summary(tbl)
    assert summary["客户数"].sum() == tbl["customer"].nunique()


# ---------------- abc ----------------
def test_abc_analysis():
    df = make_sales(400)
    tbl = abc.abc_analysis(df, item_col="category")
    assert tbl["cum_pct"].is_monotonic_increasing
    assert set(tbl["class"]).issubset({"A", "B", "C"})
    s = abc.class_summary(tbl)
    assert s["销售额占比%"].sum().round(1) == 100.0


# ---------------- cohort ----------------
def test_cohort_retention():
    df = make_sales(500)
    ret, sizes = cohort.cohort_retention(df, period="M")
    assert (ret <= 1.0).all().all()
    # 第 0 期留存恒为 100%
    assert (ret.iloc[:, 0] == 1.0).all()
    assert (sizes["客户数"] > 0).all()


# ---------------- basket ----------------
def test_association_rules_math():
    rows = []
    for i in range(10):
        items = ["A", "B"] if i < 6 else ["C"]
        for it in items:
            rows.append({"order_id": f"O{i}", "product_id": it})
    df = pd.DataFrame(rows)
    itemsets, rules = basket.association_rules(df, min_support=0.1, min_confidence=0.1)
    ab = rules[(rules["antecedent"] == "A") & (rules["consequent"] == "B")].iloc[0]
    assert ab["support"] == 0.6
    assert ab["confidence"] == 1.0
    assert ab["lift"] == round(1.0 / 0.6, 4)


# ---------------- funnel ----------------
def test_funnel_math():
    # 用户 a/d/c 只浏览；用户 b 浏览并加购
    df = pd.DataFrame({"user_id": list("aabbbcccd"), "event_type": ["visit"] * 9})
    df.loc[2:3, "event_type"] = "cart"
    out = funnel.funnel_from_events(df, step_order=["visit", "cart"])
    assert out["users"].tolist() == [4, 1]
    assert out["conv_from_prev_pct"].iloc[1] == 25.0


# ---------------- report ----------------
def test_excel_report(tmp_path):
    from bdatools.report import excel_report

    path = excel_report({"表A": pd.DataFrame({"x": [1, 2]}), "表B": pd.DataFrame({"y": [3]})},
                        tmp_path / "r.xlsx")
    assert path.exists()
    sheets = pd.ExcelFile(path).sheet_names
    assert sheets == ["表A", "表B"]


def test_full_report_smoke(tmp_path):
    from bdatools.report import full_report

    df = make_sales(400)
    df_cn = df.rename(columns={
        "order_id": "订单号", "order_date": "下单日期", "customer_id": "客户ID",
        "product_id": "商品ID", "category": "品类", "quantity": "数量",
        "unit_price": "单价", "amount": "金额",
    })
    res = full_report(df_cn, output_dir=tmp_path, min_support=0.03)
    report = tmp_path / "analysis_report.xlsx"
    assert report.exists()
    assert (tmp_path / "charts" / "trend.png").exists()
    assert "RFM分层汇总" in res["tables"]
