"""命令行入口：bda <command>。详见 README 或 bda --help。"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import pandas as pd


def _read(path: str) -> pd.DataFrame:
    from .cleaning import read_table

    if not Path(path).exists():
        sys.exit(f"文件不存在: {path}")
    return read_table(path)


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="bda",
        description="bdatools 商业数据分析工具箱 —— 见 https://github.com/yourname/bda-toolkit",
    )
    sub = p.add_subparsers(dest="command", required=True)

    demo = sub.add_parser("demo", help="生成模拟数据并跑完整分析 demo")
    demo.add_argument("--rows", type=int, default=6000, help="模拟订单行数")
    demo.add_argument("--out", default="outputs", help="输出目录")

    rep = sub.add_parser("report", help="对自己的订单数据一键生成完整分析报告")
    rep.add_argument("csv", help="订单明细 CSV/Excel 路径")
    rep.add_argument("--events", default=None, help="可选：转化事件表 CSV（user_id,event_type）")
    rep.add_argument("--out", default="outputs", help="输出目录")
    rep.add_argument("--freq", default="M", choices=["D", "W", "M", "Q", "Y"], help="趋势统计周期")
    rep.add_argument("--snapshot", default=None, help="RFM 基准日期，如 2026-09-01")

    desc = sub.add_parser("describe", help="打印数据概览与列画像")
    desc.add_argument("csv", help="数据文件路径")

    r = sub.add_parser("rfm", help="RFM 客户分层")
    r.add_argument("csv", help="订单明细路径")
    r.add_argument("--snapshot", default=None, help="基准日期")
    r.add_argument("--out", default=None, help="结果保存 xlsx 路径")

    a = sub.add_parser("abc", help="ABC/帕累托分析")
    a.add_argument("csv", help="订单明细路径")
    a.add_argument("--item", default="category", help="分析对象列，默认 category（可传中文别名如 品类）")

    g = sub.add_parser("growth", help="期间汇总 + 同比/环比")
    g.add_argument("csv", help="订单明细路径")
    g.add_argument("--freq", default="M", choices=["D", "W", "M", "Q", "Y"])

    return p


def main(argv: list[str] | None = None) -> None:
    args = build_parser().parse_args(argv)

    if args.command == "demo":
        from examples.make_sample_data import make_sample_data
        from .report import full_report

        out = Path(args.out)
        sales_path, events_path = make_sample_data(out / "sample_data", rows=args.rows)
        sales = pd.read_csv(sales_path)
        events = pd.read_csv(events_path)
        full_report(sales, events_df=events, output_dir=out / "report")

    elif args.command == "report":
        from .report import full_report

        sales = _read(args.csv)
        events = _read(args.events) if args.events else None
        full_report(sales, events_df=events, output_dir=args.out, freq=args.freq,
                    snapshot=args.snapshot)

    elif args.command == "describe":
        from .describe import eda_report

        for name, tbl in eda_report(_read(args.csv)).items():
            print(f"\n=== {name} ===")
            print(tbl.to_string(index=False))

    elif args.command == "rfm":
        from .cleaning import standardize_columns
        from .rfm import rfm_score, segment_summary

        tbl = rfm_score(standardize_columns(_read(args.csv)), snapshot=args.snapshot)
        summary = segment_summary(tbl)
        print(summary.to_string(index=False))
        if args.out:
            from .report import excel_report

            excel_report({"RFM明细": tbl, "RFM分层汇总": summary}, args.out)
            print(f"\n已保存: {args.out}")

    elif args.command == "abc":
        from .abc import abc_analysis, class_summary, plot_pareto
        from .cleaning import resolve_column, standardize_columns

        item = resolve_column(args.item)
        df = standardize_columns(_read(args.csv))
        tbl = abc_analysis(df, item_col=item)
        print(class_summary(tbl, item_col=item).to_string(index=False))
        print("\nTop 10：")
        print(tbl.head(10).to_string(index=False))
        plot_pareto(tbl, item, "outputs/abc_pareto.png")
        print("\n图表已保存: outputs/abc_pareto.png")

    elif args.command == "growth":
        from .cleaning import standardize_columns
        from .growth import period_summary

        trend = period_summary(standardize_columns(_read(args.csv)), freq=args.freq)
        print(trend.to_string(index=False))


if __name__ == "__main__":
    main()
