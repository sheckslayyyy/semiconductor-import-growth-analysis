# Methodology and scope (Plan B)

## Research design

The question is not whether two mathematical indices *can* move in different directions. It investigates **where real historical HS6 import growth was recorded** and the observable relationship between partner growth patterns and concentration for three selected markets (2019–2024).

**Unit:** market `m`, HS6 `k`, year `t`, exporter code `p`. Input value `V(m,k,t,p)` is nominal USD, converted from BACI `v` in thousands of USD. Importer is the BACI `j` field, exporter the BACI `i` field. HS6 codes: 854231/854232/854233/854239/854290.

## 1. Input verification

- 4,798 retained HS6 flow records (2019–2024, three markets and five HS6 codes); 90 non-empty market–HS6–year groups.
- Required columns checked; keys `(t,j,i,k)` unique; nominal trade value positive and finite; `v × 1,000 = trade_value_usd` exactly with Decimal.
- 708 missing `q` quantities kept as observed and ignored for amount-based analysis.
- Independently re-aggregate HS6 to market/year/partner and compare **exact USD values** against 1,520 rows of submitted HS8542 total CSV. All 18 market-years reconciled.
- Keep China, Hong Kong SAR, Macao SAR and `Other Asia, nes` separate; do not infer fabrication origin from exporter.

## 2. Overall market analysis (RQ1)

At each market/year, sum `V` over the five HS6 codes by exporter. Compute total `T`, each source share `s = V/T`, leading exporter and `HHI = Σ s²`. Compare yearly levels and `ΔHHI`. The partner-level outputs allow inspection of the major sources, not only the top-ranked one.

## 3. Product-level growth and partner attribution (RQ2)

For every market/HS6/year, compute total nominal imports `T` and source shares `s_p`. For each adjacent-year comparison (3 × 5 × 5 = 75):

- `ΔV_p = V(p,t) − V(p,t−1)`. Values absent in one year are treated as zero for the *comparison only*; no input rows are imputed.
- Net total increase: `ΔT = T(t) − T(t−1) = Σ ΔV_p`.
- Gross positive increase: `G = Σ max(ΔV_p, 0)`.
- Gross negative decrease: `N = Σ min(ΔV_p, 0)` (nonpositive, separately recorded). Verify `G + N = ΔT`.
- Positive-growth contribution: `g_p = max(ΔV_p,0) / G` when `G > 0`; the positive contributions sum to 1. This is **not** the same denominator as net growth `ΔT`.
- **Prior Top 3:** Rank exporter codes using **the previous year's import value**; tie-break with numeric exporter code. Sum their `g_p` to obtain `top3_share`.
- HHI change: `ΔHHI = HHI(t) − HHI(t−1)`.
- Per-source HHI change contribution: `c_p = s(p,t)² − s(p,t−1)²`. Verify `Σ c_p = ΔHHI`. These are mathematical accounting contributions, **not causal effects**.

For each market–HS6–year, the identity checks run programmatically. This prevents descriptive output from reducing to a ranking of the largest growers.

## 4. Exploratory hypothesis check

**Hypothesis:** Among observations with net-positive total nominal import growth, a higher fraction of gross positive growth allocated to the previous year's top three sources may be associated with a higher frequency of increases in HHI.

1. Select comparisons with `ΔT > 0` (50 cases from the submitted dataset).
2. Calculate the **sample median** of their Top 3 positive growth contribution. No arbitrary cutoff is imposed. Ties at the median are assigned to the `high` group.
3. Split the positive-growth comparisons into `high` (>= median) and `low` (< median) prior-Top-3 contribution groups. Calculate the frequency of `ΔHHI > 0` in each.
4. Also reverse the comparison: group by HHI increase vs decrease and compare the **mean and median** of prior-Top-3 contributions. Inspect market and HS6 subgroups and contradictory cases.
5. Do not assume 75 transitions are 75 independent random samples; do not turn the calculated difference into an unsupported inferential p-value, causality, or a risk forecast.

*Why this is not mathematically guaranteed:* The Top 3 **as a combined group** may receive most gross positive growth while the distribution **within the group** becomes more balanced, decreasing HHI. The observed hypothesis is non-deterministic.

## 5. Statistical category 490 sensitivity

The official category `Other Asia, nes` (code 490) is kept in the baseline. In a **separate** scenario, exclude it from every market–HS6–year group and then recompute from scratch:

- yearly totals, source shares, and HHI;
- net/gross import growth and prior-year Top 3 selection;
- Top 3 positive-growth contributions and grouped hypothesis checks.

Hence the number of net-positive-growth transitions may change, and comparisons are **not simply the same sample with a different HHI**. The full sample yields 50 positive-growth cases; the exclusion scenario yields 44. Code 490 is an official statistical category, not an observed single independent supplier country; removing it does not make the remaining data automatically more accurate.

## 6. Limitations and interpretation

- Nominal growth can reflect prices, product-mix, statistical revisions, or trade routing; it does **not** prove increased physical chip demand.
- The HS6 categories include integrated-circuit **parts**, not every semiconductor product; HS6 is insufficient for part-number sales targeting.
- Importer/exporter are recorded trading economies, not necessarily final origin or individual suppliers.
- Partner shares and HHI measure import-source **concentration**, not supply-chain disruption probabilities or resilience.
- Growth share and ΔHHI are calculated from the same trade amounts, and adjacent years/products share observations; associations are descriptive.
- This code implements the specific proposal study scope and does not claim arbitrary country/year/HS-version compatibility.

## 7. Reproducibility and validation

```bash
python -m unittest discover -s tests -v
python src/analysis.py
```

Tests cover input corruption and duplicate detection, positive-growth denominators, prior-year top-three selection, amount/HHI identity checks, historical known values, and exclusion re-normalization. All published CSVs and PNGs should be generated by the same script, not manually edited.
