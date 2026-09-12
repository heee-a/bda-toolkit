"""库调用方式示例：像 import 普通第三方库一样使用 bdatools。

运行前先安装: pip install -e .
"""

import bdatools as bda
from bdatools.cleaning import read_table

# 1) 读取 + 清洗（自动映射中文列名）
raw = read_table("sample_data/sample_sales.csv")
clean = bda.cleaning.clean_sales(raw)
print(clean.steps)  # 清洗日志
df = clean.data

# 2) 销售趋势：月度汇总 + 环比/同比
trend = bda.growth.period_summary(df, freq="M")
print(trend.tail())

# 3) 品类 ABC 分析
abc_tbl = bda.abc.abc_analysis(df, item_col="category")
print(abc_tbl)

# 4) RFM 客户分层
rfm_tbl = bda.rfm.rfm_score(df)
print(bda.rfm.segment_summary(rfm_tbl).head())

# 5) 同期群留存
retention, sizes = bda.cohort.cohort_retention(df, period="M")
print(retention.iloc[:5, :6])

# 6) 购物篮关联规则（无额外依赖）
itemsets, rules = bda.basket.association_rules(df, item_col="product_id")
print(rules.head())

# 7) 转化漏斗（需要事件表）
events = read_table("sample_data/sample_events.csv")
print(bda.funnel.funnel_from_events(events))

# 8) 一键完整报告：outputs/analysis_report.xlsx + outputs/charts/*.png
bda.report.full_report(raw, events_df=events, output_dir="outputs")
