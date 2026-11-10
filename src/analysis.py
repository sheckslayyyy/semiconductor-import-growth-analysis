"""CAS1100 Plan B: HS6 semiconductor import growth and source concentration.

Pure-Python computations; Matplotlib is optional for PNG figures. This module
separates measured trade facts, accounting identities, and exploratory patterns.
Run from the repository root: python src/analysis.py
"""
from __future__ import annotations

import argparse
import csv
import math
import statistics
from collections import defaultdict
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MARKET_CODES = {"Vietnam": 704, "Thailand": 764, "Malaysia": 458}
MARKETS = tuple(MARKET_CODES)
HS6 = ("854231", "854232", "854233", "854239", "854290")
YEARS = tuple(range(2019, 2025))
SPECIAL_PARTNER = 490  # BACI 'Other Asia, nes' -- not a single identified nation
AMOUNT_ZERO = Decimal("0")
EPS = 1e-10


@dataclass(frozen=True)
class PartnerAmount:
    name: str
    amount: Decimal


# keyed by (import market, HS6, year), then exporter numeric code
GroupedData = dict[tuple[str, str, int], dict[int, PartnerAmount]]


def normalized_market(value: str) -> str:
    """Use one label internally without merging exporter economies."""
    v = value.strip()
    return "Vietnam" if v == "Viet Nam" else v


def read_detail(path: Path, *, strict_scope: bool = True) -> tuple[GroupedData, dict]:
    """Read the submitted HS6 CSV. Reject missing/invalid keys and altered USD values."""
    needed = {"t", "i", "j", "k", "v", "q", "exporter_name", "importer_name", "trade_value_usd"}
    data: GroupedData = defaultdict(dict)
    seen: set[tuple[int, int, int, str]] = set()
    q_missing = 0
    row_count = 0
    with Path(path).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not needed.issubset(reader.fieldnames):
            raise ValueError(f"HS6 CSV is missing required fields: {needed - set(reader.fieldnames or [])}")
        for row_number, row in enumerate(reader, 2):
            try:
                year = int(row["t"])
                exporter = int(row["i"])
                importer_code = int(row["j"])
                hs6 = row["k"].strip()
                name = row["exporter_name"].strip()
                importer = normalized_market(row["importer_name"])
                thousands = Decimal(row["v"])
                usd = Decimal(row["trade_value_usd"])
            except (InvalidOperation, ValueError, KeyError, TypeError) as exc:
                raise ValueError(f"Malformed detail row {row_number}: {exc}") from exc
            if not name or importer not in MARKET_CODES or MARKET_CODES[importer] != importer_code:
                raise ValueError(f"Unexpected importer / partner at row {row_number}")
            if hs6 not in HS6 or year not in YEARS:
                raise ValueError(f"Out-of-scope HS6/year at row {row_number}")
            if not usd.is_finite() or usd <= 0 or not thousands.is_finite() or usd != thousands * 1000:
                raise ValueError(f"Invalid USD conversion or amount at row {row_number}")
            key = (year, importer_code, exporter, hs6)
            if key in seen:
                raise ValueError(f"Duplicate trade key at row {row_number}: {key}")
            seen.add(key)
            group = (importer, hs6, year)
            data[group][exporter] = PartnerAmount(name=name, amount=usd)
            q_missing += int(not (row["q"] or "").strip())
            row_count += 1
    if strict_scope:
        expected = {(m, k, y) for m in MARKETS for k in HS6 for y in YEARS}
        if set(data) != expected:
            raise ValueError(f"Expected 90 market-HS6-year groups; missing {len(expected-set(data))}")
        if row_count != 4798:
            raise ValueError(f"Expected verified 4,798 HS6 rows; found {row_count}")
        if q_missing != 708:
            raise ValueError(f"Expected 708 missing q values; found {q_missing}")
    return dict(data), {"rows": row_count, "groups": len(data), "missing_q": q_missing}


def verify_aggregates(detail: GroupedData, aggregate_csv: Path, *, strict_scope: bool = True) -> dict:
    """Independently reconcile HS6 sums against the second submitted CSV."""
    actual: dict[tuple[str, int, int], Decimal] = defaultdict(lambda: AMOUNT_ZERO)
    for (market, _hs6, year), partners in detail.items():
        for exporter, obj in partners.items():
            actual[(market, year, exporter)] += obj.amount
    needed = {"year", "importer_code", "importer_name", "exporter_code", "hs4", "trade_value_thousand_usd", "trade_value_usd"}
    seen: set[tuple[str, int, int]] = set()
    with Path(aggregate_csv).open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        if not reader.fieldnames or not needed.issubset(reader.fieldnames):
            raise ValueError("Aggregate CSV has invalid columns")
        for lineno, row in enumerate(reader, 2):
            try:
                market = normalized_market(row["importer_name"])
                year = int(row["year"])
                exporter = int(row["exporter_code"])
                code = int(row["importer_code"])
                value = Decimal(row["trade_value_usd"])
                thousands = Decimal(row["trade_value_thousand_usd"])
            except (KeyError, InvalidOperation, ValueError, TypeError) as exc:
                raise ValueError(f"Bad aggregate row {lineno}: {exc}") from exc
            key = (market, year, exporter)
            if market not in MARKET_CODES or MARKET_CODES[market] != code or row["hs4"] != "8542":
                raise ValueError(f"Invalid market/HS4 at aggregate row {lineno}")
            if key in seen:
                raise ValueError(f"Duplicate aggregate key: {key}")
            seen.add(key)
            if key not in actual or actual[key] != value or value != thousands * 1000:
                raise ValueError(f"HS6 / aggregate reconciliation failed for {key}")
    if seen != set(actual):
        raise ValueError(f"Different partner coverage between files: {len(seen)} vs {len(actual)}")
    if strict_scope and len(seen) != 1520:
        raise ValueError(f"Expected 1,520 aggregated rows; got {len(seen)}")
    return {"reconciled_market_year_partner_rows": len(seen), "usd_exact": True}


def shares_and_total(partners: dict[int, PartnerAmount]) -> tuple[dict[int, float], Decimal]:
    if not partners:
        raise ValueError("Market-HS6-year has no partner records")
    total = sum((record.amount for record in partners.values()), AMOUNT_ZERO)
    if total <= 0:
        raise ValueError("Market-HS6-year has no positive total")
    shares = {partner: float(record.amount / total) for partner, record in partners.items()}
    if not math.isclose(sum(shares.values()), 1, abs_tol=1e-10):
        raise ValueError("Source shares fail to sum to one")
    return shares, total


def hhi(shares: dict[int, float]) -> float:
    return sum(s * s for s in shares.values())


def direction(value: float, epsilon: float = EPS) -> str:
    if value > epsilon:
        return "increase"
    if value < -epsilon:
        return "decrease"
    return "unchanged"


def partner_transition(previous: dict[int, PartnerAmount], current: dict[int, PartnerAmount],
                       market: str, hs6: str, year: int) -> tuple[list[dict], dict]:
    """Compute signed gross changes and HHI attribution; absent year is zero for comparison only."""
    prev_shares, prev_total = shares_and_total(previous)
    curr_shares, curr_total = shares_and_total(current)
    prev_hhi = hhi(prev_shares)
    curr_hhi = hhi(curr_shares)
    all_exporters = sorted(set(previous) | set(current))
    increments = {}
    for p in all_exporters:
        old = previous[p].amount if p in previous else AMOUNT_ZERO
        new = current[p].amount if p in current else AMOUNT_ZERO
        increments[p] = new - old
    positive_total = sum((max(x, AMOUNT_ZERO) for x in increments.values()), AMOUNT_ZERO)
    negative_total = sum((min(x, AMOUNT_ZERO) for x in increments.values()), AMOUNT_ZERO)
    top3 = sorted(previous, key=lambda p: (-previous[p].amount, p))[:3]
    top3_growth = sum((max(increments[p], AMOUNT_ZERO) for p in top3), AMOUNT_ZERO)
    top3_ratio = float(top3_growth / positive_total) if positive_total > 0 else None
    partner_rows = []
    for p in all_exporters:
        before = previous[p].amount if p in previous else AMOUNT_ZERO
        after = current[p].amount if p in current else AMOUNT_ZERO
        share_before = prev_shares.get(p, 0.0)
        share_after = curr_shares.get(p, 0.0)
        contrib = share_after ** 2 - share_before ** 2
        partner_rows.append({
            "market": market, "hs6": hs6, "previous_year": year-1, "year": year,
            "exporter_code": p, "exporter_name": current[p].name if p in current else previous[p].name,
            "previous_usd": before, "current_usd": after, "delta_usd": increments[p],
            "positive_growth_usd": max(increments[p], AMOUNT_ZERO),
            "positive_growth_share": float(max(increments[p], AMOUNT_ZERO) / positive_total) if positive_total else None,
            "previous_share": share_before, "current_share": share_after,
            "delta_share_pp": (share_after-share_before)*100, "hhi_contribution": contrib,
            "prior_top3": int(p in top3),
        })
    if sum((v["delta_usd"] for v in partner_rows), AMOUNT_ZERO) != curr_total - prev_total:
        raise AssertionError("Partner delta USD do not reconcile")
    if positive_total + negative_total != curr_total - prev_total:
        raise AssertionError("Positive plus negative growth must equal net change")
    if not math.isclose(sum(v["hhi_contribution"] for v in partner_rows),
                        curr_hhi-prev_hhi, abs_tol=1e-10):
        raise AssertionError("Partner contributions do not reconcile to HHI change")
    if top3_ratio is not None and not 0 <= top3_ratio <= 1 + EPS:
        raise AssertionError("Top 3 positive growth share out of range")
    comparison = {
        "market": market, "hs6": hs6, "previous_year": year-1, "year": year,
        "previous_total_usd": prev_total, "current_total_usd": curr_total,
        "net_growth_usd": curr_total-prev_total,
        "growth_rate_pct": float((curr_total/prev_total-1)*100),
        "gross_positive_growth_usd": positive_total, "gross_negative_growth_usd": negative_total,
        "hhi_previous": prev_hhi, "hhi_current": curr_hhi,
        "delta_hhi": curr_hhi-prev_hhi,
        "hhi_direction": direction(curr_hhi-prev_hhi),
        "total_growth": int(curr_total > prev_total),
        "prior_top3_codes": ";".join(str(p) for p in top3),
        "prior_top3_positive_growth_usd": top3_growth,
        "prior_top3_positive_share": top3_ratio,
    }
    return partner_rows, comparison


def analyze(detail: GroupedData, *, exclude_code: int | None = None) -> dict:
    """Return market/product/year metrics and 75 adjacent-year source comparisons."""
    reduced: GroupedData = {}
    for key, partners in detail.items():
        selected = {p: v for p, v in partners.items() if p != exclude_code}
        if not selected:
            raise ValueError(f"All partners removed for {key}")
        reduced[key] = selected

    yearly, comparisons, changes, aggregate, aggregate_sources_rows = [], [], [], [], []
    for market in MARKETS:
        for year in YEARS:
            aggregate_sources: dict[int, PartnerAmount] = {}
            for hs6 in HS6:
                partners = reduced[market, hs6, year]
                shares, total = shares_and_total(partners)
                largest = max(shares, key=shares.get)
                yearly.append({
                    "market": market, "hs6": hs6, "year": year,
                    "total_usd": total, "partner_count": len(partners),
                    "hhi": hhi(shares), "largest_exporter_code": largest,
                    "largest_exporter_name": partners[largest].name,
                    "largest_exporter_share": shares[largest],
                    "share_490_in_baseline": None if exclude_code is not None else shares.get(SPECIAL_PARTNER, 0.0),
                })
                for p, v in partners.items():
                    prev = aggregate_sources.get(p)
                    aggregate_sources[p] = PartnerAmount(v.name, v.amount + (prev.amount if prev else AMOUNT_ZERO))
            total_shares, total_value = shares_and_total(aggregate_sources)
            biggest = max(total_shares, key=total_shares.get)
            aggregate.append({"market": market, "year": year, "total_usd": total_value,
                              "hhi": hhi(total_shares), "partner_count": len(aggregate_sources),
                              "largest_source": aggregate_sources[biggest].name,
                              "largest_source_share": total_shares[biggest],
                              "delta_hhi_from_previous_year": None})
            for partner in sorted(aggregate_sources):
                aggregate_sources_rows.append({"market": market, "year": year,
                    "exporter_code": partner, "exporter_name": aggregate_sources[partner].name,
                    "trade_value_usd": aggregate_sources[partner].amount,
                    "share": total_shares[partner]})
        for hs6 in HS6:
            for year in YEARS[1:]:
                part, comp = partner_transition(reduced[market, hs6, year-1],
                                                reduced[market, hs6, year], market, hs6, year)
                changes.extend(part)
                comparisons.append(comp)

    annual_hhi = {(r["market"], r["year"]): r["hhi"] for r in aggregate}
    for r in aggregate:
        if r["year"] > YEARS[0]:
            r["delta_hhi_from_previous_year"] = r["hhi"] - annual_hhi[r["market"], r["year"]-1]
    if len(yearly) != 90 or len(aggregate) != 18 or len(comparisons) != 75:
        raise AssertionError("Expected exactly 90 HS6-year, 18 aggregate-year and 75 comparison rows")
    for market in MARKETS:
        for year in YEARS:
            hs6_sum = sum((r["total_usd"] for r in yearly if r["market"] == market and r["year"] == year), AMOUNT_ZERO)
            market_sum = next(r["total_usd"] for r in aggregate if r["market"] == market and r["year"] == year)
            if hs6_sum != market_sum:
                raise AssertionError("Aggregate market-year does not match HS6 sum")
    return {"yearly": yearly, "aggregate": aggregate,
            "aggregate_partner_shares": aggregate_sources_rows,
            "comparisons": comparisons, "partner_changes": changes}


def mean_or_none(numbers: list[float]) -> float | None:
    return statistics.mean(numbers) if numbers else None


def median_or_none(numbers: list[float]) -> float | None:
    return statistics.median(numbers) if numbers else None


def hypothesis_analysis(comparisons: list[dict]) -> tuple[list[dict], list[dict], float]:
    """Explore the proposal's pre-existing-top3 hypothesis on net-growth transitions.

    The median cut-off comes from all net-growth observations. Report comparisons
    descriptively; observations across years/HS6/markets are not independent.
    """
    positive_cases = [dict(row) for row in comparisons if row["net_growth_usd"] > 0]
    if not positive_cases:
        raise ValueError("No net-positive import growth observations")
    values = [r["prior_top3_positive_share"] for r in positive_cases]
    if any(x is None for x in values):
        raise AssertionError("Net growth > 0 must imply gross positive increase > 0")
    threshold = statistics.median(values)
    for row in positive_cases:
        row["top3_group"] = "high" if row["prior_top3_positive_share"] >= threshold else "low"
        row["top3_global_median"] = threshold
        row["hhi_increased"] = int(row["hhi_direction"] == "increase")
    result = []
    selections = [("ALL", "ALL", positive_cases)]
    selections += [("market", market, [r for r in positive_cases if r["market"] == market]) for market in MARKETS]
    selections += [("hs6", k, [r for r in positive_cases if r["hs6"] == k]) for k in HS6]
    for kind, label, subset in selections:
        increased = [r["prior_top3_positive_share"] for r in subset if r["hhi_direction"] == "increase"]
        decreased = [r["prior_top3_positive_share"] for r in subset if r["hhi_direction"] == "decrease"]
        high = [r for r in subset if r["top3_group"] == "high"]
        low = [r for r in subset if r["top3_group"] == "low"]
        rate_high = sum(r["hhi_increased"] for r in high) / len(high) if high else None
        rate_low = sum(r["hhi_increased"] for r in low) / len(low) if low else None
        result.append({
            "group_type": kind, "group_name": label,
            "growth_cases": len(subset),
            "hhi_increase_cases": len(increased), "hhi_decrease_cases": len(decreased),
            "hhi_unchanged_cases": sum(r["hhi_direction"] == "unchanged" for r in subset),
            "mean_top3_share_if_hhi_increase": mean_or_none(increased),
            "median_top3_share_if_hhi_increase": median_or_none(increased),
            "mean_top3_share_if_hhi_decrease": mean_or_none(decreased),
            "median_top3_share_if_hhi_decrease": median_or_none(decreased),
            "global_top3_median_cutoff": threshold,
            "high_group_n": len(high), "low_group_n": len(low),
            "hhi_increase_rate_high": rate_high,
            "hhi_increase_rate_low": rate_low,
            "hhi_increase_rate_difference": rate_high-rate_low if rate_high is not None and rate_low is not None else None,
        })
    return positive_cases, result, threshold


def sensitivity_rows(baseline: dict, excluded: dict) -> tuple[list[dict], list[dict]]:
    """Compare code-490 scenarios, **recomputing** yearly totals/shares/ranks after exclusion."""
    years = {(r["market"], r["hs6"], r["year"]): r for r in excluded["yearly"]}
    comparisons = {(r["market"], r["hs6"], r["year"]): r for r in excluded["comparisons"]}
    year_rows, comparison_rows = [], []
    for row in baseline["yearly"]:
        other = years[row["market"], row["hs6"], row["year"]]
        year_rows.append({"market": row["market"], "hs6": row["hs6"], "year": row["year"],
                          "share_490_baseline": row["share_490_in_baseline"],
                          "total_usd_all": row["total_usd"], "total_usd_excluding_490": other["total_usd"],
                          "hhi_all": row["hhi"], "hhi_excluding_490": other["hhi"],
                          "difference_all_minus_excluded": row["hhi"]-other["hhi"]})
    for row in baseline["comparisons"]:
        other = comparisons[row["market"], row["hs6"], row["year"]]
        comparison_rows.append({"market": row["market"], "hs6": row["hs6"], "previous_year": row["previous_year"], "year": row["year"],
                                "delta_hhi_all": row["delta_hhi"], "delta_hhi_excluding_490": other["delta_hhi"],
                                "direction_all": row["hhi_direction"], "direction_excluding_490": other["hhi_direction"],
                                "direction_reverses": int(row["hhi_direction"] != other["hhi_direction"]),
                                "total_growth_all": row["total_growth"], "total_growth_excluding_490": other["total_growth"],
                                "top3_share_all": row["prior_top3_positive_share"],
                                "top3_share_excluding_490": other["prior_top3_positive_share"]})
    return year_rows, comparison_rows


def formatted(value: object) -> object:
    if value is None:
        return ""
    if isinstance(value, float):
        return f"{value:.10f}" if math.isfinite(value) else ""
    if isinstance(value, Decimal):
        return f"{value:.3f}"
    return value


def write_csv(path: Path, rows: list[dict]) -> None:
    if not rows:
        raise ValueError(f"Cannot write empty {path}")
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0]))
        writer.writeheader()
        for row in rows:
            writer.writerow({key: formatted(val) for key, val in row.items()})


def build_findings(baseline: dict, cases: list[dict], summary: list[dict],
                   sens_comparison: list[dict], meta: dict, reconciled: dict,
                   excluded_cases: list[dict], excluded_summary: list[dict]) -> str:
    all_stats = summary[0]
    example1 = next(r for r in baseline["comparisons"] if r["market"]=="Vietnam" and r["hs6"]=="854232" and r["year"]==2024)
    example2 = next(r for r in baseline["comparisons"] if r["market"]=="Thailand" and r["hs6"]=="854239" and r["year"]==2024)
    reversals = [r for r in sens_comparison if r["direction_reverses"]]
    txt = ["# Automatically generated analysis summary", "",
           "**Data:** CEPII BACI HS17 V202601, 2019–2024, HS6 854231/854232/854233/854239/854290.",
           f"**Verification:** {meta['rows']:,} HS6 records; {meta['groups']} market-product-years; "
           f"{reconciled['reconciled_market_year_partner_rows']:,} reconciled aggregate rows; "
           f"{meta['missing_q']} missing quantity entries retained.", "",
           "## Exploratory hypothesis check", "",
           f"- Adjacent-year comparisons: {len(baseline['comparisons'])}.",
           f"- Net-positive growth comparisons: {len(cases)}.",
           f"- Among net-positive cases, HHI increased in {all_stats['hhi_increase_cases']} and decreased in {all_stats['hhi_decrease_cases']} cases.",
           f"- Median prior-year-top-3 positive growth share (global cutoff): {all_stats['global_top3_median_cutoff']:.4f}.",
           f"- HHI increase rate, high-top3-contribution cases: {all_stats['hhi_increase_rate_high']:.1%} (n={all_stats['high_group_n']}).",
           f"- HHI increase rate, low-top3-contribution cases: {all_stats['hhi_increase_rate_low']:.1%} (n={all_stats['low_group_n']}).",
           "- High/low groups use the **global sample median**, not an invented fixed threshold.",
           "- These are **descriptive associations**, not causal evidence or independent statistical samples.", "",
           "## Illustrative observed cases (2023 to 2024)", "",
           f"- Vietnam / memories (854232): nominal import growth {example1['growth_rate_pct']:+.1f}%, "
           f"delta HHI {example1['delta_hhi']:+.5f}, prior-year-top-3 positive-growth share "
           f"{example1['prior_top3_positive_share']:.1%}.",
           f"- Thailand / other ICs (854239): nominal import growth {example2['growth_rate_pct']:+.1f}%, "
           f"delta HHI {example2['delta_hhi']:+.5f}, prior-year-top-3 positive-growth share "
           f"{example2['prior_top3_positive_share']:.1%}.", "",
           "## Data classification sensitivity", "",
           f"- HHI year-over-year direction changes in {len(reversals)} of {len(sens_comparison)} comparisons "
           "when `Other Asia, nes` (code 490) is excluded and shares are renormalized.",
           f"- Under the exclusion scenario: {len(excluded_cases)} net-positive growth cases, "
           f"{excluded_summary[0]['hhi_increase_cases']} HHI rises, {excluded_summary[0]['hhi_decrease_cases']} HHI falls.",
           f"- Exclusion scenario's high vs low top-three HHI-rise rates: "
           f"{excluded_summary[0]['hhi_increase_rate_high']:.1%} vs "
           f"{excluded_summary[0]['hhi_increase_rate_low']:.1%}.",
           "- Excluding 490 is a **scenario**, not a correction or evidence that this category is a country.",
           "- Since exclusion changes the total, it also changes the growth comparisons and prior-year top-three rankings.", "",
           "## Interpretation constraints", "",
           "- Nominal trade values are not physical chip volumes, buyer demand, or price-adjusted growth.",
           "- Recorded direct trading partners are not automatically chip manufacturing locations or firms.",
           "- Country/product observations share years and partners; do not treat them as independent for inference.",
           "- No claim about supply-chain failure probabilities, causal drivers, or actual sales leads is made.", "",
           "## Reproduce", "", "```bash", "python src/analysis.py", "```", ""]
    return "\n".join(txt)


def draw_charts(baseline: dict, cases: list[dict], stats: list[dict],
                comparison_sensitivity: list[dict], outdir: Path) -> list[str]:
    try:
        import matplotlib.pyplot as plt
    except ImportError:
        print("Optional matplotlib missing: analysis CSV and summary still generated.")
        return []
    outdir.mkdir(parents=True, exist_ok=True)
    files = []
    def save(fig, name):
        fig.tight_layout()
        fig.savefig(outdir/name, dpi=170)
        plt.close(fig)
        files.append(name)

    fig, ax = plt.subplots(figsize=(9, 5))
    for m in MARKETS:
        data = sorted((r for r in baseline["aggregate"] if r["market"]==m),key=lambda r:r["year"])
        ax.plot([x["year"] for x in data],[x["hhi"] for x in data],marker="o",label=m)
    ax.set(title="Overall HS 8542 import source concentration",xlabel="Year",ylabel="HHI")
    ax.set_xticks(YEARS); ax.grid(alpha=.2); ax.legend()
    save(fig,"01_aggregate_hhi.png")

    for m in MARKETS:
        fig, ax = plt.subplots(figsize=(10, 5))
        for hs6 in HS6:
            data=sorted((r for r in baseline["yearly"] if r["market"]==m and r["hs6"]==hs6),key=lambda r:r["year"])
            ax.plot(YEARS,[x["hhi"] for x in data],marker=".",label=hs6)
        ax.set(title=f"HS6 concentration by product: {m}",xlabel="Year",ylabel="HHI")
        ax.set_xticks(YEARS); ax.grid(alpha=.2); ax.legend(title="HS6",ncol=3)
        save(fig,f"02_hs6_hhi_{m.lower()}.png")

    fig, ax = plt.subplots(figsize=(9, 5))
    for m in MARKETS:
        sub=[r for r in cases if r["market"]==m]
        ax.scatter([r["prior_top3_positive_share"] for r in sub],
                   [r["delta_hhi"] for r in sub],label=m,s=52,alpha=.8)
    ax.axhline(0,linestyle="--",linewidth=.9)
    ax.axvline(stats[0]["global_top3_median_cutoff"],linestyle=":",linewidth=.9)
    ax.set(title="Prior top-three positive growth share vs concentration change",
           xlabel="Prior top-three share of gross positive growth (0–1)",ylabel="Annual change in HHI")
    ax.grid(alpha=.2);ax.legend()
    save(fig,"03_top3_vs_delta_hhi.png")

    fig,ax=plt.subplots(figsize=(7,4.5))
    d=stats[0]
    ax.bar(["High top-3 share","Low top-3 share"],
           [100*d["hhi_increase_rate_high"],100*d["hhi_increase_rate_low"]])
    ax.set(title="HHI rise frequency by prior top-three growth contribution",ylabel="Cases with HHI increase (%)",ylim=(0,100))
    save(fig,"04_hypothesis_high_low.png")

    fig,ax=plt.subplots(figsize=(10,5))
    for m in MARKETS:
        data=[r for r in comparison_sensitivity if r["market"]==m]
        ax.scatter([r["delta_hhi_all"] for r in data],[r["delta_hhi_excluding_490"] for r in data],label=m,alpha=.75,s=50)
    lo=min([r["delta_hhi_all"] for r in comparison_sensitivity]+[r["delta_hhi_excluding_490"] for r in comparison_sensitivity])
    hi=max([r["delta_hhi_all"] for r in comparison_sensitivity]+[r["delta_hhi_excluding_490"] for r in comparison_sensitivity])
    ax.plot([lo,hi],[lo,hi],linestyle="--",linewidth=.8)
    ax.axhline(0,linestyle=":",linewidth=.8);ax.axvline(0,linestyle=":",linewidth=.8)
    ax.set(title="HHI change: all partners vs excluding 490",xlabel="Delta HHI (all sources)",ylabel="Delta HHI (excluding 490)")
    ax.grid(alpha=.2);ax.legend()
    save(fig,"05_sensitivity_490.png")
    return files


def run(data: Path, aggregate: Path, output_dir: Path, figures_dir: Path,
        *, no_plots: bool = False, strict_scope: bool = True) -> dict:
    detail, meta = read_detail(data, strict_scope=strict_scope)
    cross = verify_aggregates(detail, aggregate, strict_scope=strict_scope)
    baseline = analyze(detail)
    excluded = analyze(detail, exclude_code=SPECIAL_PARTNER)
    positive_cases, summary, threshold = hypothesis_analysis(baseline["comparisons"])
    excluded_positive_cases, excluded_summary, _ = hypothesis_analysis(excluded["comparisons"])
    yearly_sens, comparison_sens = sensitivity_rows(baseline, excluded)

    outputs = {
        "aggregate_market_year.csv": baseline["aggregate"],
        "aggregate_partner_shares.csv": baseline["aggregate_partner_shares"],
        "market_hs6_year.csv": baseline["yearly"],
        "annual_growth_comparisons.csv": baseline["comparisons"],
        "partner_growth_contributions.csv": baseline["partner_changes"],
        "hypothesis_growth_cases.csv": positive_cases,
        "hypothesis_group_summary.csv": summary,
        "hypothesis_group_summary_excluding_490.csv": excluded_summary,
        "sensitivity_490_yearly.csv": yearly_sens,
        "sensitivity_490_comparisons.csv": comparison_sens,
    }
    for name, records in outputs.items():
        write_csv(output_dir/name, records)
    (output_dir/"KEY_FINDINGS.md").write_text(
        build_findings(baseline, positive_cases, summary, comparison_sens, meta, cross,
                       excluded_cases=excluded_positive_cases, excluded_summary=excluded_summary), encoding="utf-8")
    figures = [] if no_plots else draw_charts(baseline, positive_cases, summary, comparison_sens, figures_dir)
    print(f"PASS: {meta['rows']} HS6 input rows; {meta['groups']} yearly HS6 groups; "
          f"{cross['reconciled_market_year_partner_rows']} aggregate partners")
    print(f"PASS: {len(baseline['comparisons'])} year transitions; {len(positive_cases)} net-growth cases; "
          f"{summary[0]['hhi_increase_cases']} HHI rises; {summary[0]['hhi_decrease_cases']} HHI falls")
    print(f"Top-3 contribution global median: {threshold:.4f}")
    print(f"High vs low group HHI-rise frequency: {summary[0]['hhi_increase_rate_high']:.1%} vs "
          f"{summary[0]['hhi_increase_rate_low']:.1%}")
    print(f"Generated: {len(outputs)} CSVs, 1 summary markdown, {len(figures)} charts")
    return {"input": meta, "reconciliation": cross, "baseline": baseline, "excluded": excluded,
            "cases": positive_cases, "summary": summary, "sensitivity": comparison_sens,
            "figures": figures}


def main() -> None:
    parser = argparse.ArgumentParser(description="CAS1100 Plan B HS6 growth & source concentration analysis")
    parser.add_argument("--data",type=Path,default=ROOT/"data/semiconductor_hs6_detail.csv")
    parser.add_argument("--aggregate",type=Path,default=ROOT/"data/semiconductor_trade_2019_2024.csv")
    parser.add_argument("--output",type=Path,default=ROOT/"results")
    parser.add_argument("--figures",type=Path,default=ROOT/"figures")
    parser.add_argument("--no-plots",action="store_true",help="CSV and markdown only; matplotlib optional")
    args=parser.parse_args()
    run(args.data,args.aggregate,args.output,args.figures,no_plots=args.no_plots)


if __name__ == "__main__":
    main()
