# Automatically generated analysis summary

**Data:** CEPII BACI HS17 V202601, 2019–2024, HS6 854231/854232/854233/854239/854290.
**Verification:** 4,798 HS6 records; 90 market-product-years; 1,520 reconciled aggregate rows; 708 missing quantity entries retained.

## Exploratory hypothesis check

- Adjacent-year comparisons: 75.
- Net-positive growth comparisons: 50.
- Among net-positive cases, HHI increased in 28 and decreased in 22 cases.
- Median prior-year-top-3 positive growth share (global cutoff): 0.5371.
- HHI increase rate, high-top3-contribution cases: 68.0% (n=25).
- HHI increase rate, low-top3-contribution cases: 44.0% (n=25).
- High/low groups use the **global sample median**, not an invented fixed threshold.
- These are **descriptive associations**, not causal evidence or independent statistical samples.

## Illustrative observed cases (2023 to 2024)

- Vietnam / memories (854232): nominal import growth +182.0%, delta HHI -0.11201, prior-year-top-3 positive-growth share 86.9%.
- Thailand / other ICs (854239): nominal import growth +71.3%, delta HHI +0.15016, prior-year-top-3 positive-growth share 83.0%.

## Data classification sensitivity

- HHI year-over-year direction changes in 20 of 75 comparisons when `Other Asia, nes` (code 490) is excluded and shares are renormalized.
- Under the exclusion scenario: 44 net-positive growth cases, 20 HHI rises, 24 HHI falls.
- Exclusion scenario's high vs low top-three HHI-rise rates: 59.1% vs 31.8%.
- Excluding 490 is a **scenario**, not a correction or evidence that this category is a country.
- Since exclusion changes the total, it also changes the growth comparisons and prior-year top-three rankings.

## Interpretation constraints

- Nominal trade values are not physical chip volumes, buyer demand, or price-adjusted growth.
- Recorded direct trading partners are not automatically chip manufacturing locations or firms.
- Country/product observations share years and partners; do not treat them as independent for inference.
- No claim about supply-chain failure probabilities, causal drivers, or actual sales leads is made.

## Reproduce

```bash
python src/analysis.py
```
