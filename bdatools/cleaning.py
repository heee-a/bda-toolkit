"""数据清洗：智能读取、中英文列名映射、缺失/重复/异常值处理。"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

# 常见中文业务列名 -> 标准英文列名（standardize_columns 自动映射）
COLUMN_ALIASES: dict[str, list[str]] = {
    "order_id": ["订单号", "订单id", "订单编号", "订单", "单号"],
    "order_date": ["下单日期", "订单日期", "日期", "销售日期", "成交日期", "date"],
    "customer_id": ["客户id", "客户编号", "用户id", "用户编号", "会员id", "买家id", "客户"],
    "product_id": ["商品id", "商品编号", "产品id", "产品编号", "sku", "货号"],
    "product_name": ["商品名称", "产品名称", "商品"],
    "category": ["品类", "类目", "商品类目", "类别", "分类", "品类名称"],
    "quantity": ["数量", "销售数量", "件数", "购买数量", "销量"],
    "unit_price": ["单价", "售价", "标准单价"],
    "amount": ["金额", "销售额", "销售金额", "实付金额", "订单金额", "成交金额"],
    "region": ["地区", "区域", "大区", "省份", "城市"],
    "channel": ["渠道", "来源渠道", "流量渠道"],
}

_ENCANDIDATES = ("utf-8-sig", "gbk", "utf-16", "latin1")


def read_table(path: str) -> pd.DataFrame:
    """读取 CSV/Excel，自动尝试常见编码（utf-8/gbk 等）。"""
    path = str(path)
    if path.lower().endswith((".xlsx", ".xls")):
        return pd.read_excel(path)
    last_err: Exception | None = None
    for enc in _ENCANDIDATES:
        try:
            return pd.read_csv(path, encoding=enc)
        except UnicodeDecodeError as e:  # 编码不对，换下一个
            last_err = e
    raise last_err  # type: ignore[misc]


def standardize_columns(df: pd.DataFrame) -> pd.DataFrame:
    """把常见中文列名映射为标准英文列名，未识别的列保持原名。"""
    mapping: dict[str, str] = {}
    for col in df.columns:
        key = str(col).strip().lower()
        for std, aliases in COLUMN_ALIASES.items():
            if key in {a.lower() for a in aliases}:
                mapping[col] = std
                break
    return df.rename(columns=mapping)


def resolve_column(name: str) -> str:
    """把用户传入的列名（含中文别名）解析为标准列名，未识别则原样返回。"""
    key = str(name).strip().lower()
    for std, aliases in COLUMN_ALIASES.items():
        if key == std or key in {a.lower() for a in aliases}:
            return std
    return str(name)


def missing_profile(df: pd.DataFrame) -> pd.DataFrame:
    """每列缺失数量与缺失占比。"""
    miss = df.isna().sum()
    out = pd.DataFrame(
        {
            "列名": miss.index,
            "缺失数": miss.values,
            "缺失占比%": (miss.values / len(df) * 100).round(2) if len(df) else miss.values,
        }
    )
    return out[out["缺失数"] > 0].reset_index(drop=True)


def cap_outliers(
    df: pd.DataFrame,
    column: str,
    factor: float = 3.0,
    method: str = "iqr",
) -> pd.DataFrame:
    """用 IQR（默认）或 zscore 方法对数值列做缩尾（winsorize）处理。

    超出上下界的值被截断到边界，而不是删除，适合金额类右偏数据。
    """
    x = pd.to_numeric(df[column], errors="coerce")
    if method == "iqr":
        q1, q3 = x.quantile(0.25), x.quantile(0.75)
        iqr = q3 - q1
        lo, hi = q1 - factor * iqr, q3 + factor * iqr
    elif method == "zscore":
        mu, sd = x.mean(), x.std()
        lo, hi = mu - factor * sd, mu + factor * sd
    else:
        raise ValueError(f"未知 method: {method}，可选 iqr / zscore")
    out = df.copy()
    out[column] = x.clip(lower=lo, upper=hi)
    return out


@dataclass
class CleanResult:
    """清洗结果：清洗后的数据 + 每一步的日志表。"""

    data: pd.DataFrame
    steps: pd.DataFrame = field(default_factory=pd.DataFrame)

    @property
    def log(self) -> pd.DataFrame:
        return self.steps


def clean_sales(
    df: pd.DataFrame,
    snapshot: pd.Timestamp | None = None,
    winsorize: bool = True,
    dedup_orders: bool = False,
) -> CleanResult:
    """一键清洗销售/订单明细数据。

    步骤：中文列名映射 -> 日期解析 -> 数值列修正 -> 去重 ->
          缺失关键行剔除 -> 金额缺失回填(数量*单价) -> 金额缩尾。

    Parameters
    ----------
    df : 订单明细 DataFrame
    snapshot : 计算近期性等的基准日期，默认取数据中最大日期
    winsorize : 是否对 amount 做 IQR 缩尾（默认开启，factor=3 只截极端值）
    dedup_orders : 是否按订单号只保留一条明细；购物篮分析需要多商品订单，勿开启

    Returns
    -------
    CleanResult(data=清洗后数据, steps=清洗日志)
    """
    steps: list[dict] = []

    def _log(name: str, before: int, after: int, note: str = "") -> None:
        steps.append({"步骤": name, "处理前行数": before, "处理后行数": after, "说明": note})

    n0 = len(df)
    df = standardize_columns(df)
    steps.append({"步骤": "列名标准化", "处理前行数": n0, "处理后行数": len(df),
                  "说明": "中文列名映射为标准英文列名"})

    if "order_date" in df.columns:
        df = df.copy()
        df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce")

    for col in ("quantity", "unit_price", "amount"):
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce")

    before = len(df)
    df = df.drop_duplicates()
    _log("去除完全重复行", before, len(df))

    if dedup_orders and "order_id" in df.columns:
        before = len(df)
        df = df.drop_duplicates(subset="order_id", keep="first")
        _log("按订单号去重", before, len(df), "每单仅保留一条明细")

    if "amount" in df.columns and {"quantity", "unit_price"}.issubset(df.columns):
        mask = df["amount"].isna() & df["quantity"].notna() & df["unit_price"].notna()
        df.loc[mask, "amount"] = df.loc[mask, "quantity"] * df.loc[mask, "unit_price"]
        if mask.any():
            steps.append({"步骤": "回填缺失金额", "处理前行数": int(mask.sum()),
                          "处理后行数": int(mask.sum()), "说明": "金额 = 数量 × 单价"})

    critical = [c for c in ("order_id", "order_date", "customer_id", "amount") if c in df.columns]
    if critical:
        before = len(df)
        df = df.dropna(subset=critical)
        _log("剔除关键列缺失的行", before, len(df), f"关键列: {', '.join(critical)}")

    if "amount" in df.columns:
        before_min, before_max = df["amount"].min(), df["amount"].max()
        if winsorize and len(df) >= 10:
            df = cap_outliers(df, "amount", factor=3.0)
            steps.append({"步骤": "金额缩尾(IQR×3)", "处理前行数": before_min,
                          "处理后行数": before_max,
                          "说明": "极端金额截断到 IQR 边界，不删行"})
        df = df[df["amount"] > 0]

    df = df.reset_index(drop=True)
    _log("完成", n0, len(df))
    return CleanResult(data=df, steps=pd.DataFrame(steps))
