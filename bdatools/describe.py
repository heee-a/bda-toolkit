"""自动 EDA：列画像、总览、相关性 Top-N。"""

from __future__ import annotations

import numpy as np
import pandas as pd


def overview(df: pd.DataFrame) -> pd.DataFrame:
    """数据总览：行数、列数、内存占用、重复行数。"""
    return pd.DataFrame(
        {
            "指标": ["行数", "列数", "重复行数", "内存占用(MB)"],
            "值": pd.Series(
                [len(df), df.shape[1], int(df.duplicated().sum()),
                 round(df.memory_usage(deep=True).sum() / 1024 / 1024, 2)],
                dtype="object",
            ),
        }
    )


def column_profile(df: pd.DataFrame) -> pd.DataFrame:
    """逐列画像：类型、缺失、唯一值、最频繁值；数值列附统计量。"""
    rows = []
    for col in df.columns:
        s = df[col]
        numeric = pd.to_numeric(s, errors="coerce")
        is_num = numeric.notna().mean() > 0.9 and s.dtype.kind in "ifub"
        row: dict = {
            "列名": col,
            "类型": str(s.dtype),
            "非空数": int(s.notna().sum()),
            "缺失%": round(float(s.isna().mean() * 100), 2),
            "唯一值数": int(s.nunique(dropna=True)),
        }
        if len(s.dropna()):
            top = s.value_counts().index[0]
            row["最频繁值"] = str(top)[:40]
        else:
            row["最频繁值"] = None
        if is_num:
            row.update(
                {
                    "均值": round(float(numeric.mean()), 4),
                    "标准差": round(float(numeric.std()), 4),
                    "最小值": numeric.min(),
                    "中位数": numeric.median(),
                    "最大值": numeric.max(),
                }
            )
        rows.append(row)
    return pd.DataFrame(rows)


def top_correlations(df: pd.DataFrame, n: int = 10) -> pd.DataFrame:
    """数值列之间相关性最高的前 n 对字段。"""
    num = df.select_dtypes(include="number")
    if num.shape[1] < 2:
        return pd.DataFrame(columns=["列A", "列B", "相关系数"])
    corr = num.corr(numeric_only=True)
    upper = np.triu(np.ones(corr.shape, dtype=bool), k=1)  # 只取上三角，剔除自身配对
    pairs = (
        corr.where(pd.DataFrame(upper, index=corr.index, columns=corr.columns))
        .stack()
        .sort_values(key=abs, ascending=False)
        .head(n)
    )
    return pd.DataFrame(
        [{"列A": a, "列B": b, "相关系数": round(float(v), 4)} for (a, b), v in pairs.items()]
    )


def eda_report(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    """一键 EDA：返回 {'总览':…, '列画像':…, '缺失情况':…, '相关性Top10':…}。"""
    from .cleaning import missing_profile

    return {
        "总览": overview(df),
        "列画像": column_profile(df),
        "缺失情况": missing_profile(df),
        "相关性Top10": top_correlations(df),
    }
