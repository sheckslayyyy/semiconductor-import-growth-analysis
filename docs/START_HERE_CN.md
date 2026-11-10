# 中文使用说明 | CAS1100 Plan B

这是按照最终修订的 Proposal **B方案**完成的可运行Python项目。

## 1. 电脑上怎么运行（Windows）

把项目ZIP解压到自己容易找到的位置，进入 `semiconductor-import-growth-analysis` 文件夹，在该文件夹地址栏输入 `cmd` 并按回车。

```bat
py --version
py -m pip install -r requirements.txt
py -m unittest discover -s tests -v
py src\analysis.py
```

没有Matplotlib、暂时不想安装库，也可以直接执行：

```bat
py src\analysis.py --no-plots
```

测试应输出 `Ran 21 tests ... OK`；分析应输出 `PASS: 4798 HS6 input rows`、`75 year transitions` 等。生成CSV在 `results/`，图表在 `figures/`。

**注意：** 你的电脑需要Python 3.10或以上版本；不要直接在压缩包内部双击 `.py`，要先解压再在项目根目录运行。

## 2. 这次研究究竟做了什么？

- RQ1：三个国家2019–2024年HS8542整体进口来源份额和HHI有什么变化？查 `aggregate_market_year.csv` 和 `aggregate_partner_shares.csv`。
- RQ2：按五个HS6产品细分，进口增长究竟来自哪些贸易来源？它们份额变化对HHI变化有怎样的数学贡献？查 `partner_growth_contributions.csv` 和 `annual_growth_comparisons.csv`。
- 探索性假设：进口总额增长时，原来前三大来源占全部**正向增长额**的比例较高，是否更常见HHI上升？查 `hypothesis_group_summary.csv`。
- 敏感性：排除 `Other Asia, nes`（代码490）后，结论如何变化？查 `sensitivity_490_*.csv` 与 `hypothesis_group_summary_excluding_490.csv`。

注意HHI始终非负；`delta_hhi` 可正可负。负值不是「负的集中度」，是「集中程度下降」。

## 3. 如何读增长贡献？

假设原来的两大来源进口额分别是100和50，今年变为110和90，其他来源没有增长。

- A的金额增加10；B的金额增加40。
- 总正向增长额 `G=10+40=50`。
- A的**正向增长贡献率**是20%；B是80%。
- 但是HHI要根据两年的**份额**计算，不能只看绝对进口金额。

如果某来源金额下降，它的增量为负值，单独记录在 `delta_usd` 和 `gross_negative_growth_usd`，**不会作为负项放进正向增长贡献率分母**。

## 4. 要看哪个文件？

| 想知道 | 打开文件 |
|---|---|
| 各国整体HHI、金额 | `results/aggregate_market_year.csv` |
| 整体各来源的份额 | `results/aggregate_partner_shares.csv` |
| 90组HS6产品年度数据 | `results/market_hs6_year.csv` |
| 75次同比增长和HHI变化 | `results/annual_growth_comparisons.csv` |
| 每个贸易来源增加/减少了多少 | `results/partner_growth_contributions.csv` |
| 假设检验高/低组对比 | `results/hypothesis_group_summary.csv` |
| 不含490后的结论 | `results/hypothesis_group_summary_excluding_490.csv` |
| 自动生成的结论摘要 | `results/KEY_FINDINGS.md` |

报告中应该区分「进口总额净增长」和「所有来源正向增量之和」。两个概念不同。

## 5. 最终交作业要注意

这份项目代码不等于已经完成课程的最终视频或研究报告。你们仍须根据教授要求准备报告、MP4演示，报告里引用最终公开仓库的准确链接，并确保讲解的算法与仓库代码完全一致。

不要把包含个人资料的课程Proposal PDF或老师的课程讲义直接公开上传仓库；代码、匿名/公共贸易数据与复现说明足够。
