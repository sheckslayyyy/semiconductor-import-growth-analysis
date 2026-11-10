# Revised Korean Proposal -> Python implementation map

| Proposal section | Code | Output evidence |
|---|---|---|
| Topic / RQ1: HS8542 import partners and their shares, HHI | `analyze()` aggregate grouping | `aggregate_market_year.csv`, `aggregate_partner_shares.csv`, `01_aggregate_hhi.png` |
| Data structure and preprocessing: HS6 details, official BACI exporter/importer codes | `read_detail()` | validated 4,798 input rows, 90 market–HS6–year groups |
| Cross-file reconciliation | `verify_aggregates()` | verifies all 1,520 HS8542 aggregate partner rows |
| `V`, `T`, source share, HHI, `ΔHHI` | `shares_and_total()`, `hhi()`, `partner_transition()` | `market_hs6_year.csv`, `annual_growth_comparisons.csv` |
| Partner `ΔV`, gross positive `G`, `g`, gross negative changes | `partner_transition()` | `partner_growth_contributions.csv` |
| Prior-year largest 3 partners: positive-growth contribution share | `partner_transition()` (previous-year ranking) | `annual_growth_comparisons.csv` |
| Partner `c_p` sum to `ΔHHI` | `partner_transition()` assertions | `partner_growth_contributions.csv` and tests |
| RQ2 hypothesis: 75 year changes, growing-market observations, HHI direction groups, means/medians | `hypothesis_analysis()` | `hypothesis_group_summary.csv`, `hypothesis_growth_cases.csv` |
| Median-based high/low prior-top-3 contribution grouping and HHI increase frequency | `hypothesis_analysis()` | `hypothesis_group_summary.csv`, `04_hypothesis_high_low.png` |
| Sensitivity: keep/exclude special source 490 and renormalize | `analyze(exclude_code=490)`, `sensitivity_rows()` | `sensitivity_490_yearly.csv`, `sensitivity_490_comparisons.csv`, `hypothesis_group_summary_excluding_490.csv` |
| Results in tables, figures, text summary | `write_csv()`, `draw_charts()`, `build_findings()` | `results/`, `figures/`, `results/KEY_FINDINGS.md` |

**Careful:** The code is an implementation of the **revised Plan B**, not of the original SC-vs-ΔHHI hypothesis. The earlier prototype may be cited as development history, but do not confuse its algorithms with the new proposal. The project final report should quote functions that actually appear in this repository.
