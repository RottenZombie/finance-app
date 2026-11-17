from __future__ import annotations

import unittest
from decimal import Decimal

from features.bist.valuation import value_holdings
from features.summary_math import bist_value_and_coverage, calculate_portfolio_totals

HOLDINGS = [
    {"symbol": "ASELS", "quantity": "10", "average_cost": "100"},
    {"symbol": "THYAO", "quantity": "5", "average_cost": "200"},
]


class ValuationTests(unittest.TestCase):
    def test_complete_prices_give_profit_loss(self):
        result = value_holdings(HOLDINGS, {"ASELS": Decimal("120"), "THYAO": Decimal("180")})
        self.assertTrue(result["complete"])
        self.assertEqual(result["total_cost"], Decimal("2000"))
        self.assertEqual(result["market_value"], Decimal("2100"))
        self.assertEqual(result["profit_loss"], Decimal("100"))
        self.assertEqual(result["profit_loss_pct"], Decimal("5"))
        self.assertEqual(result["rows"][0]["profit_loss"], Decimal("200"))
        self.assertEqual(result["rows"][1]["profit_loss_pct"], Decimal("-10"))

    def test_missing_price_is_named_and_remaining_holdings_still_show_profit_loss(self):
        result = value_holdings(HOLDINGS, {"ASELS": Decimal("120")})
        self.assertFalse(result["complete"])
        self.assertEqual(result["missing"], ["THYAO"])
        self.assertEqual(result["market_value"], Decimal("1200"))
        self.assertEqual(result["priced_count"], 1)
        # profit/loss covers only ASELS; THYAO is never guessed
        self.assertEqual(result["profit_loss"], Decimal("200"))
        self.assertEqual(result["profit_loss_pct"], Decimal("20"))
        self.assertIsNone(result["rows"][1]["profit_loss"])

    def test_no_prices_and_empty_portfolio(self):
        none = value_holdings(HOLDINGS, None)
        self.assertIsNone(none["market_value"])
        self.assertIsNone(none["profit_loss"])
        empty = value_holdings([], {"X": Decimal("1")})
        self.assertFalse(empty["complete"])
        self.assertEqual(empty["total_cost"], Decimal("0"))

    def test_invalid_prices_are_treated_as_missing(self):
        result = value_holdings(HOLDINGS, {"ASELS": Decimal("0"), "THYAO": Decimal("-1")})
        self.assertEqual(result["priced_count"], 0)

    def test_zero_cost_holding_has_no_percentage(self):
        result = value_holdings(
            [{"symbol": "BONUS", "quantity": "10", "average_cost": "0"}], {"BONUS": Decimal("5")}
        )
        self.assertIsNone(result["rows"][0]["profit_loss_pct"])
        self.assertEqual(result["profit_loss"], Decimal("50"))


class SummaryBistTests(unittest.TestCase):
    def totals(self, prices):
        return calculate_portfolio_totals(
            currency_holdings=[{"asset_code": "USD", "quantity": "2", "average_cost_try": "30"}],
            currency_prices={"USD": Decimal("35")},
            metal_holdings=[], metal_prices={},
            bist_holdings=HOLDINGS, bist_prices=prices,
        )

    def test_without_prices_behaviour_is_unchanged_cost_based(self):
        totals = self.totals(None)
        self.assertEqual(totals["bist"], Decimal("2000"))
        self.assertEqual(totals["bist_coverage"], "none")
        self.assertIsNone(totals["bist_profit_loss"])
        self.assertEqual(totals["total_profit_loss"], Decimal("10"))

    def test_full_coverage_uses_market_value_and_joins_total_pl(self):
        totals = self.totals({"ASELS": Decimal("120"), "THYAO": Decimal("180")})
        self.assertEqual(totals["bist"], Decimal("2100"))
        self.assertEqual(totals["bist_profit_loss"], Decimal("100"))
        self.assertEqual(totals["total_profit_loss"], Decimal("110"))
        self.assertEqual(totals["total"], Decimal("2170"))

    def test_partial_coverage_shows_profit_loss_of_priced_shares_and_names_the_rest(self):
        totals = self.totals({"ASELS": Decimal("120")})
        self.assertEqual(totals["bist"], Decimal("1200") + Decimal("1000"))
        self.assertEqual(totals["bist_coverage"], "partial")
        self.assertEqual(totals["bist_profit_loss"], Decimal("200"))
        self.assertEqual(totals["bist_missing"], ["THYAO"])
        self.assertEqual(totals["total_profit_loss"], Decimal("210"))

    def test_no_price_at_all_lists_every_share_and_keeps_profit_loss_empty(self):
        totals = self.totals({})
        self.assertEqual(totals["bist_coverage"], "none")
        self.assertIsNone(totals["bist_profit_loss"])
        self.assertEqual(totals["bist_missing"], ["ASELS", "THYAO"])
        self.assertEqual(totals["total_profit_loss"], Decimal("10"))

    def test_empty_group(self):
        value, coverage = bist_value_and_coverage([], {"X": Decimal("1")})
        self.assertEqual((value, coverage), (Decimal("0"), "empty"))


if __name__ == "__main__":
    unittest.main()
