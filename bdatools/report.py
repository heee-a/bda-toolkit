"""一键分析报告：清洗 -> EDA -> 趋势 -> ABC -> RFM -> 留存 -> 购物篮 -> 漏斗，
输出多 Sheet Excel 报告与配套图表 PNG。
"""

from __future__ import annotations

from pathlib import Path

import pandas as pd

from . import abc, basket, cleaning, cohort, describe, funnel, growth, rfm


def excel_report(tables: dict[str, pd.DataFrame], path: str | Path) -> Path:
    """把多张表写成一个带自动列宽的 Excel 文件（每张表一个 Sheet）。"""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(path, engine="openpyxl") as writer:
        used: set[str] = set()
        for name, df in tables.items():
            sheet = str(name)[:31]
            i = 2
            while sheet in used:  # Excel sheet 名不可重复
                suffix = f"~{i}"
                sheet = str(name)[: 31 - len(suffix)] + suffix
                i += 1
            used.add(sheet)
            df.to_excel(writer, sheet_name=sheet, index=False)
        for ws in writer.book.worksheets:  # 自动列宽
            for column_cells in ws.columns:
                width = max(
                    (len(str(c.value)) for c in column_cells if c.value is not None),
                    default=8,
                )
                ws.column_dimensions[column_cells[0].column_letter].width = min(
                    42, max(9, width + 2)
                )
    return path


def full_report(
    sales_df: pd.DataFrame,
    events_df: pd.DataFrame | None = None,
    output_dir: str | Path = "outputs",
    snapshot: pd.Timestamp | str | None = None,
    freq: str = "M",
    min_support: float = 0.02,
) -> dict:
    """对销售订单数据跑完整分析流水线，产出 Excel 报告 + 图表。

    Parameters
    ----------
    sales_df : 订单明细，推荐列：order_id/order_date/customer_id/product_id/category/amount
               （中文列名会自动映射，见 bdatools.cleaning.COLUMN_ALIASES）
    events_df : 可选，转化事件表（user_id, event_type），提供则输出漏斗分析
    output_dir : 输出目录，生成 analysis_report.xlsx 和 charts/*.png
    snapshot : RFM/留存计算的基准日期，默认数据最大日期
    freq : 趋势统计周期 M/Q/W/D
    min_support : 购物篮分析最小支持度

    Returns
    -------
    {"data": 清洗后数据, "tables": 各分析结果表, "charts": 图表路径}
    """
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    chart_dir = out / "charts"

    print("[1/7] 数据清洗 ...")
    cleaned = cleaning.clean_sales(sales_df, snapshot=snapshot)
    data = cleaned.data
    print(f"      清洗完成：{cleaned.steps['处理前行数'].iloc[0]:,} -> {len(data):,} 行")

    tables: dict[str, pd.DataFrame] = {"清洗日志": cleaned.steps}

    print("[2/7] 数据概览 EDA ...")
    tables.update(describe.eda_report(data))

    print("[3/7] 销售趋势 ...")
    trend = growth.period_summary(data, freq=freq)
    ma = growth.moving_average(data, freq="W", window=4)
    tables["销售趋势"] = trend
    tables["周销售与4周均线"] = ma
    charts = [growth.plot_trend(trend, chart_dir / "trend.png")]

    print("[4/7] 品类 ABC 分析 ...")
    item_col = "category" if "category" in data.columns else (
        data.select_dtypes(exclude="number").columns[0] if len(data.select_dtypes(exclude="number").columns) else "order_id"
    )
    abc_tbl = abc.abc_analysis(data, item_col=item_col)
    tables["品类ABC"] = abc_tbl
    tables["ABC汇总"] = abc.class_summary(abc_tbl, item_col=item_col)
    charts.append(abc.plot_pareto(abc_tbl, item_col, chart_dir / "pareto.png"))

    print("[5/7] RFM 客户分层 ...")
    rfm_tbl = rfm.rfm_score(data, snapshot=snapshot)
    rfm_sum = rfm.segment_summary(rfm_tbl)
    tables["RFM明细"] = rfm_tbl
    tables["RFM分层汇总"] = rfm_sum
    charts.append(rfm.plot_segments(rfm_sum, chart_dir / "rfm_segments.png"))

    print("[6/7] 用户留存 ...")
    retention, sizes = cohort.cohort_retention(data, period="M")
    tables["留存矩阵"] = retention.reset_index().rename(columns={"index": "同期群"})
    tables["同期群人数"] = sizes.reset_index()
    charts.append(cohort.plot_cohort(retention, chart_dir / "cohort.png"))

    if "product_id" in data.columns:
        print("[6.5] 购物篮关联规则 ...")
        itemsets, rules = basket.association_rules(
            data, item_col="product_id", min_support=min_support
        )
        tables["高频商品"] = itemsets.head(50)
        tables["关联规则"] = rules.head(50)
        charts.append(basket.plot_rules(rules, chart_dir / "rules.png"))
    else:
        print("[6.5] 跳过购物篮分析（缺少 product_id 列）")

    if events_df is not None:
        print("[6.8] 转化漏斗 ...")
        fun = funnel.funnel_from_events(events_df)
        tables["转化漏斗"] = fun
        charts.append(funnel.plot_funnel(fun, chart_dir / "funnel.png"))

    print("[7/7] 生成 Excel 报告与图表 ...")
    # 周期列转字符串，便于 Excel 展示
    for key in ("销售趋势", "周销售与4周均线"):
        if key in tables:
            tables[key]["period"] = tables[key]["period"].astype(str)
    if "留存矩阵" in tables:
        first_col = tables["留存矩阵"].columns[0]
        tables["留存矩阵"][first_col] = tables["留存矩阵"][first_col].astype(str)
    if "同期群人数" in tables:
        tables["同期群人数"]["cohort"] = tables["同期群人数"]["cohort"].astype(str)

    report_path = excel_report(tables, out / "analysis_report.xlsx")
    print(f"完成！Excel 报告: {report_path}")
    print(f"      图表目录: {chart_dir}")
    return {"data": data, "tables": tables, "charts": charts, "report": report_path}
