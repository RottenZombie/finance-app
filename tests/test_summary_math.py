import unittest
from decimal import Decimal

from features.summary_math import calculate_portfolio_totals, convert_try_total


class SummaryCalculationTests(unittest.TestCase):
    def test_total_groups_and_conversions(self):
        totals = calculate_portfolio_totals(
            currency_holdings=[{"asset_code": "USD", "quantity": "2", "average_cost_try": "30"}],
            currency_prices={"USD": Decimal("35")},
            metal_holdings=[{"asset_code": "XAU", "quantity": "1", "average_cost_try": "2800"}],
            metal_prices={"XAU": Decimal("3000")},
            bist_holdings=[{"quantity": "10", "average_cost": "100"}],
        )
        self.assertEqual(totals["currency"], Decimal("70"))
        self.assertEqual(totals["metals"], Decimal("3000"))
        self.assertEqual(totals["bist"], Decimal("1000"))
        self.assertEqual(totals["total"], Decimal("4070"))
        converted = convert_try_total(
            totals["total"], try_per_eur=Decimal("38"), try_per_usd=Decimal("35")
        )
        self.assertEqual(converted, {"TRY": "4.070,00", "EUR": "107,11", "USD": "116,29"})


    def test_profit_loss_is_calculated_for_quoted_assets_only(self):
        totals = calculate_portfolio_totals(
            currency_holdings=[
                {"asset_code": "USD", "quantity": "2", "average_cost_try": "30"}
            ],
            currency_prices={"USD": Decimal("35")},
            metal_holdings=[
                {"asset_code": "XAU", "quantity": "1", "average_cost_try": "2800"}
            ],
            metal_prices={"XAU": Decimal("3000")},
            bist_holdings=[{"quantity": "10", "average_cost": "100"}],
        )
        self.assertEqual(totals["currency_profit_loss"], Decimal("10"))
        self.assertEqual(totals["metals_profit_loss"], Decimal("200"))
        self.assertIsNone(totals["bist_profit_loss"])
        self.assertEqual(totals["total_profit_loss"], Decimal("210"))

    def test_profit_loss_is_unknown_when_a_held_asset_has_no_quote(self):
        totals = calculate_portfolio_totals(
            currency_holdings=[
                {"asset_code": "USD", "quantity": "2", "average_cost_try": "30"}
            ],
            currency_prices={"USD": None},
            metal_holdings=[], metal_prices={}, bist_holdings=[],
        )
        self.assertIsNone(totals["currency_profit_loss"])
        self.assertIsNone(totals["total_profit_loss"])

    def test_missing_quote_does_not_show_partial_group_total(self):
        totals = calculate_portfolio_totals(
            currency_holdings=[{"asset_code": "USD", "quantity": "2"}],
            currency_prices={"USD": None},
            metal_holdings=[], metal_prices={}, bist_holdings=[],
        )
        self.assertIsNone(totals["currency"])
        self.assertIsNone(totals["total"])
        self.assertEqual(totals["metals"], Decimal("0"))


if __name__ == "__main__":
    unittest.main()
