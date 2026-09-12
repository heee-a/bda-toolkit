"""bdatools: 开箱即用的商业数据分析工具箱.

模块一览
--------
cleaning  数据清洗（中英文列名映射、缺失/重复/异常值处理）
describe  自动 EDA 与列画像
growth    销售趋势：同比/环比/移动平均
rfm       RFM 客户分层
abc       ABC / 帕累托分析
cohort    用户留存矩阵
basket    购物篮分析（关联规则）
funnel    转化漏斗
report    一键生成 Excel 分析报告 + 图表
"""

__version__ = "0.1.0"

from . import abc, basket, cleaning, cohort, describe, funnel, growth, plotting, report, rfm

__all__ = [
    "abc",
    "basket",
    "cleaning",
    "cohort",
    "describe",
    "funnel",
    "growth",
    "plotting",
    "report",
    "rfm",
]
