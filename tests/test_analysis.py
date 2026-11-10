"""Standard-library tests. Run: python -m unittest discover -s tests -v"""
from __future__ import annotations

import sys
import tempfile
import unittest
from decimal import Decimal
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from analysis import (  # noqa: E402
    AMOUNT_ZERO, HS6, MARKET_CODES, MARKETS, PartnerAmount, SPECIAL_PARTNER,
    YEARS, analyze, direction, hhi, hypothesis_analysis, partner_transition,
    read_detail, sensitivity_rows, shares_and_total, verify_aggregates,
    write_csv,
)


def partner(name: str, value: str) -> PartnerAmount:
    return PartnerAmount(name=name, amount=Decimal(value))


class CoreMetricTests(unittest.TestCase):
    def test_hhi_known_values(self):
        self.assertAlmostEqual(hhi({1: 0.7, 2: 0.3}), 0.58)
        self.assertAlmostEqual(hhi({1: 1.0}), 1.0)

    def test_hhi_source_swap_preserves_value(self):
        self.assertAlmostEqual(hhi({1: 0.7, 2: 0.3}), hhi({1: 0.3, 2: 0.7}))

    def test_shares_are_normalized(self):
        shares, total = shares_and_total({1: partner('A', '50'), 2: partner('B', '150')})
        self.assertEqual(total, Decimal('200'))
        self.assertAlmostEqual(shares[1], 0.25)
        self.assertAlmostEqual(shares[2], 0.75)

    def test_empty_group_fails(self):
        with self.assertRaisesRegex(ValueError, "no partner"):
            shares_and_total({})

    def test_sign_classification(self):
        self.assertEqual(direction(0.02), 'increase')
        self.assertEqual(direction(-0.02), 'decrease')
        self.assertEqual(direction(0.0), 'unchanged')

    def test_missing_partner_is_zero_only_in_comparison(self):
        prev = {1: partner('A', '100')}
        now = {2: partner('B', '300')}
        changes, comparison = partner_transition(prev, now, 'Vietnam', '854232', 2024)
        self.assertEqual(len(changes), 2)
        self.assertEqual(next(x['previous_usd'] for x in changes if x['exporter_code']==2), AMOUNT_ZERO)
        self.assertEqual(next(x['current_usd'] for x in changes if x['exporter_code']==1), AMOUNT_ZERO)
        self.assertEqual(comparison['net_growth_usd'], Decimal('200'))
        self.assertEqual(comparison['hhi_direction'], 'unchanged')
        self.assertEqual(len(prev), 1)  # source data not modified
        self.assertEqual(len(now), 1)

    def test_top_three_selected_from_prior_year_not_current(self):
        prev = {1: partner('A', '60'), 2: partner('B', '30'), 3: partner('C', '20'),
                4: partner('D', '10')}
        now = {1: partner('A', '70'), 2: partner('B', '40'), 3: partner('C', '20'),
               4: partner('D', '110')}
        changes, comparison = partner_transition(prev, now, 'Thailand', '854239', 2024)
        self.assertEqual(comparison['prior_top3_codes'], '1;2;3')
        self.assertAlmostEqual(comparison['prior_top3_positive_share'], 20 / 120)
        self.assertEqual(next(x for x in changes if x['exporter_code']==4)['prior_top3'], 0)

    def test_positive_denominator_not_net_increase(self):
        prev = {1: partner('A', '80'), 2: partner('B', '20')}
        now = {1: partner('A', '90'), 2: partner('B', '5'), 3: partner('C', '50')}
        changes, comparison = partner_transition(prev, now, 'Malaysia', '854231', 2024)
        self.assertEqual(comparison['gross_positive_growth_usd'], Decimal('60'))
        self.assertEqual(comparison['gross_negative_growth_usd'], Decimal('-15'))
        self.assertEqual(comparison['net_growth_usd'], Decimal('45'))
        self.assertAlmostEqual(sum(x['positive_growth_share'] for x in changes), 1.0)

    def test_import_value_can_rise_while_market_share_falls(self):
        prev = {1: partner('A', '70'), 2: partner('B', '30')}
        now = {1: partner('A', '80'), 2: partner('B', '120')}
        changes, comparison = partner_transition(prev, now, 'Vietnam', '854232', 2024)
        a = next(x for x in changes if x['exporter_code']==1)
        self.assertGreater(a['delta_usd'], 0)
        self.assertLess(a['delta_share_pp'], 0)
        self.assertLess(comparison['delta_hhi'], 0)

    def test_contributions_sum_to_total_delta_hhi(self):
        prev = {1: partner('A', '70'), 2: partner('B', '30')}
        now = {1: partner('A', '100'), 2: partner('B', '15'), 3: partner('C', '5')}
        changes, comparison = partner_transition(prev, now, 'Thailand', '854231', 2024)
        self.assertAlmostEqual(sum(x['hhi_contribution'] for x in changes), comparison['delta_hhi'])

    def test_excluding_490_changes_distribution(self):
        base = {1: partner('A', '70'), 490: partner('Other Asia, nes', '30')}
        without = {p:v for p,v in base.items() if p != SPECIAL_PARTNER}
        shares1, _ = shares_and_total(base)
        shares2, _ = shares_and_total(without)
        self.assertAlmostEqual(shares1[1], 0.7)
        self.assertAlmostEqual(shares2[1], 1.0)
        self.assertIn(490, base)


class DataValidationTests(unittest.TestCase):
    def test_usd_conversion_error_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"bad.csv"
            path.write_text("t,i,j,k,v,q,exporter_name,importer_name,trade_value_usd\n"
                            "2019,410,704,854232,1.2,,Rep. of Korea,Viet Nam,1201\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "USD conversion"):
                read_detail(path, strict_scope=False)

    def test_duplicate_source_trade_key_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp)/"duplicate.csv"
            line = "2019,410,704,854232,1.2,,Rep. of Korea,Viet Nam,1200\n"
            path.write_text("t,i,j,k,v,q,exporter_name,importer_name,trade_value_usd\n"+line+line,encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "Duplicate"):
                read_detail(path, strict_scope=False)

    def test_empty_output_is_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaisesRegex(ValueError, "empty"):
                write_csv(Path(tmp)/"unused.csv", [])


class RealInputIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.input, cls.meta = read_detail(ROOT / "data/semiconductor_hs6_detail.csv")
        cls.reconciliation = verify_aggregates(cls.input, ROOT / "data/semiconductor_trade_2019_2024.csv")
        cls.baseline = analyze(cls.input)
        cls.excluded = analyze(cls.input, exclude_code=490)
        cls.cases, cls.summary, cls.threshold = hypothesis_analysis(cls.baseline["comparisons"])

    def test_real_file_counts(self):
        self.assertEqual(self.meta["rows"], 4798)
        self.assertEqual(self.meta["groups"], 90)
        self.assertEqual(self.meta["missing_q"], 708)
        self.assertEqual(self.reconciliation["reconciled_market_year_partner_rows"], 1520)

    def test_expected_observation_counts(self):
        self.assertEqual(len(self.baseline["yearly"]), 90)
        self.assertEqual(len(self.baseline["aggregate"]), 18)
        self.assertEqual(len(self.baseline["aggregate_partner_shares"]), 1520)
        self.assertEqual(len(self.baseline["comparisons"]), 75)
        self.assertEqual(len(self.cases), 50)
        self.assertEqual(self.summary[0]["hhi_increase_cases"], 28)
        self.assertEqual(self.summary[0]["hhi_decrease_cases"], 22)

    def test_real_historical_aggregate_hhi(self):
        find = {(r["market"], r["year"]):r["hhi"] for r in self.baseline["aggregate"]}
        self.assertAlmostEqual(find["Vietnam",2019], 0.21889634, places=7)
        self.assertAlmostEqual(find["Vietnam",2024], 0.18004930, places=7)
        self.assertAlmostEqual(find["Thailand",2024], 0.21416897, places=7)
        self.assertAlmostEqual(find["Malaysia",2024], 0.13593105, places=7)

    def test_hypothesis_groups_are_defined_and_reproducible(self):
        all_row = self.summary[0]
        self.assertEqual(all_row['high_group_n']+all_row['low_group_n'], 50)
        self.assertAlmostEqual(all_row['hhi_increase_rate_high'], .68)
        self.assertAlmostEqual(all_row['hhi_increase_rate_low'], .44)
        self.assertTrue(0 <= self.threshold <= 1)

    def test_hs6_amounts_equal_each_aggregate_year(self):
        for ag in self.baseline["aggregate"]:
            total = sum((r["total_usd"] for r in self.baseline["yearly"] if
                         r["market"] == ag["market"] and r["year"] == ag["year"]), AMOUNT_ZERO)
            self.assertEqual(total, ag["total_usd"])

    def test_490_sensitivity_recalculates_all(self):
        y, c = sensitivity_rows(self.baseline, self.excluded)
        self.assertEqual(len(y),90)
        self.assertEqual(len(c),75)
        self.assertEqual(sum(row['direction_reverses'] for row in c),20)
        positive_cases, summary, _ = hypothesis_analysis(self.excluded["comparisons"])
        self.assertEqual(len(positive_cases),44)
        self.assertEqual(summary[0]['hhi_increase_cases'],20)

    def test_real_individual_partner_hhi_contribution_identity(self):
        by = defaultdict(float)
        for row in self.baseline["partner_changes"]:
            by[row['market'], row['hs6'], row['year']] += row['hhi_contribution']
        for row in self.baseline["comparisons"]:
            self.assertAlmostEqual(by[row['market'],row['hs6'],row['year']], row['delta_hhi'], places=9)


if __name__ == '__main__':
    unittest.main()
