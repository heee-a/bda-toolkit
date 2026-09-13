# bda-toolkit · 商业数据分析工具箱

[![CI](https://github.com/heee-a/bda-toolkit/actions/workflows/ci.yml/badge.svg)](https://github.com/heee-a/bda-toolkit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%2B-blue)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green)](LICENSE)
[![pandas](https://img.shields.io/badge/pandas-%E2%89%A52.0-orange)](https://pandas.pydata.org/)

开箱即用的商业数据分析 Python 工具箱：拿到一份订单明细，一条命令产出**数据清洗 → 指标概览 → 销售趋势 → 品类 ABC → 客户 RFM → 同期群留存 → 购物篮关联 → 转化漏斗**的完整 Excel 分析报告与图表。

不依赖 BI 平台、不需要写 SQL，只要 `pandas` 能读的数据都能分析。

## 报告长什么样

以下均由 `bda demo` 在 6000 行模拟订单上自动生成（[examples/sample_report.xlsx](examples/sample_report.xlsx) 是完整 Excel 报告样本）：

| 销售趋势（柱=销售额，线=环比） | RFM 客户分层 |
|---|---|
| ![销售趋势](docs/sample_trend.png) | ![RFM 分层](docs/sample_rfm.png) |
| **品类 ABC 帕累托图** | **完整 Excel 报告含 16 个 Sheet** |
| ![帕累托](docs/sample_pareto.png) | 清洗日志 · 数据概览 · 列画像 · 相关性 · 销售趋势 · 品类ABC · RFM 明细/分层 · 留存矩阵 · 关联规则 · 转化漏斗 |

## 包含的分析工具

| 模块 | 功能 | 典型问题 |
|---|---|---|
| `cleaning` | 数据清洗：智能读取（utf-8/gbk）、中文列名映射、去重、缺失回填、金额缩尾 | 「数据是脏的怎么办」 |
| `describe` | 自动 EDA：列画像、缺失概况、相关性 Top-N | 「这份数据长什么样」 |
| `growth` | 同比/环比增长率、移动平均 | 「销售额涨没涨、趋势如何」 |
| `abc` | ABC / 帕累托分析 | 「哪些品类贡献了 80% 的收入」 |
| `rfm` | RFM 客户分层（经典 8 层） | 「哪些客户值得重点运营」 |
| `cohort` | 同期群留存矩阵 + 热力图 | 「新客户后续还买不买」 |
| `basket` | 购物篮关联规则（支持度/置信度/提升度，纯 pandas 实现） | 「哪些商品适合捆绑销售」 |
| `funnel` | 转化漏斗（浏览→加购→下单→支付） | 「流量在哪一步流失」 |
| `report` | 一键全流程：Excel 报告 + 图表 | 「老板要一份完整报告」 |

## 快速开始

```bash
# 克隆并安装（支持 pip 可编辑安装）
git clone https://github.com/heee-a/bda-toolkit.git
cd bda-toolkit
pip install -e .

# 一键 demo：自动生成 6000 行模拟订单数据并跑完整分析
python -m bdatools demo --out outputs
# 安装后也可以用等价的短命令（若提示找不到 bda，请用上面的 python -m 方式）
# bda demo --out outputs
```

跑完后在 `outputs/` 下得到：

```
outputs/
├── sample_data/            # 模拟订单明细 + 转化事件（可换成你自己的数据）
├── analysis_report.xlsx    # 完整分析报告（14 个 Sheet）
└── charts/                 # trend.png / pareto.png / rfm_segments.png / cohort.png / rules.png / funnel.png
```

## 用自己的数据

```bash
# 一键完整报告（中文列名自动识别：订单号/下单日期/客户ID/商品ID/品类/数量/单价/金额 …）
python -m bdatools report 你的数据.csv --out outputs --freq M

# 带转化事件表（user_id,event_type）时自动附加漏斗分析
python -m bdatools report 你的数据.csv --events events.csv --out outputs

# 单项分析
python -m bdatools describe 数据.csv              # 数据概览 + 列画像
python -m bdatools growth 订单.csv --freq M       # 月度销售 + 同比/环比
python -m bdatools abc 订单.csv --item 品类       # 品类 ABC（--item 商品ID 可分析商品）
python -m bdatools rfm 订单.csv --out rfm.xlsx    # RFM 分层
```

## 作为 Python 库使用

```python
import bdatools as bda
from bdatools.cleaning import read_table

df = bda.cleaning.clean_sales(read_table("sales.csv")).data          # 清洗
trend = bda.growth.period_summary(df, freq="M")                      # 同比/环比
abc_tbl = bda.abc.abc_analysis(df, item_col="category")              # ABC
rfm_tbl = bda.rfm.rfm_score(df, snapshot="2026-09-01")               # RFM
retention, sizes = bda.cohort.cohort_retention(df, period="M")       # 留存
itemsets, rules = bda.basket.association_rules(df, min_support=0.02) # 购物篮
bda.report.full_report("sales.csv 的 DataFrame", output_dir="outputs")  # 一键报告
```

更多示例见 [examples/usage_library.py](examples/usage_library.py)。

## 输入数据要求

订单明细表只需包含以下列（**中文/英文列名均可，自动映射**，详见 `bdatools.cleaning.COLUMN_ALIASES`）：

| 标准列名 | 中文别名（示例） | 必需 | 用途 |
|---|---|---|---|
| `order_date` | 下单日期/订单日期/日期 | ✅ | 趋势、留存、RFM 的 R |
| `customer_id` | 客户ID/用户ID/会员ID | ✅ | RFM、留存 |
| `amount` | 金额/销售额/实付金额 | ✅ | 所有金额指标（缺失时按 数量×单价 回填） |
| `order_id` | 订单号/单号 | 建议 | 购物篮分析、订单去重 |
| `product_id` / `category` | 商品ID/品类 | 建议 | 购物篮、ABC 分析 |
| `quantity` / `unit_price` | 数量/单价 | 建议 | 金额回填 |

CSV 请尽量使用 `utf-8` 编码；`gbk` 等编码会自动尝试。

## 方法说明

- **RFM 分层**：R/F/M 各按分位数打 1~5 分，与各自中位数比较高/低，映射为经典 8 层（重要价值客户、重要保持客户、重要发展客户、重要挽留客户、一般价值/保持/发展/挽留客户）。
- **ABC 分析**：按销售额降序累计占比，≤70% 为 A 类、70%~90% 为 B 类、其余为 C 类（阈值可调 `thresholds`）。
- **购物篮分析**：纯 pandas 统计 1-项集与 2-项集，计算支持度/置信度/提升度，无 mlxtend 等额外依赖；适合百万行以内的订单表。
- **同比/环比**：按周期聚合后与「上一期」「去年同期」对比；周期支持 D/W/M/Q/Y。
- **金额缩尾**：默认 IQR×3 截断极端值（不删行），可在 `clean_sales(winsorize=False)` 关闭。

## 项目结构

```
bda-toolkit/
├── bdatools/               # 核心包
│   ├── cleaning.py         # 数据清洗
│   ├── describe.py         # 自动 EDA
│   ├── growth.py           # 同比环比 / 移动平均
│   ├── abc.py              # ABC / 帕累托
│   ├── rfm.py              # RFM 分层
│   ├── cohort.py           # 同期群留存
│   ├── basket.py           # 购物篮关联规则
│   ├── funnel.py           # 转化漏斗
│   └── report.py           # 一键 Excel 报告
├── examples/               # 模拟数据生成器 + 库用法示例
├── scripts/demo.py         # 一键跑通全流程
├── tests/                  # pytest 单元测试
├── .github/workflows/ci.yml  # CI（Python 3.10/3.11/3.12）
└── pyproject.toml
```

## 常见问题

**图表中文乱码？** 工具箱已自动优先使用系统中的中文字体（微软雅黑/黑体/PingFang/Noto Sans CJK）。Linux 服务器需安装任意一款中文字体，如 `fonts-noto-cjk`。

**数据量很大？** 购物篮分析按订单内商品种类计数，超大订单可通过 `max_items_per_tx` 限制；其余模块均为向量化运算，千万行级别通常可用。

**报表中的金额有极端值？** `clean_sales` 默认做 IQR×3 缩尾，只截断不删行；如需保留原值传 `winsorize=False`。

## Roadmap

- [ ] 同类目销量预测（移动平均/简单季节模型）
- [ ] 用户生命周期价值 (LTV) 估算
- [ ] 交互式 HTML 报告输出
- [ ] 连接数据库直读（SQLAlchemy）

## Contributing

欢迎 Issue / PR。提交前请运行 `pytest -q` 确保测试通过。

## License

[MIT](LICENSE)
