import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from features.combined_import import read_combined_portfolio_excel
from features.investment_excel import write_combined_portfolio_excel
from features.investment_store import InvestmentStore
from features.bist.database import BistDatabase
from features.combined_import import apply_combined_portfolio_import


class CombinedPortfolioImportTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.path = self.root / "portfolio.xlsx"

    def tearDown(self):
        self.temp.cleanup()

    def _write(self, *, currency=None, metals=None, bist=None):
        write_combined_portfolio_excel(
            self.path,
            currency_holdings=currency or [],
            currency_prices={"USD": Decimal("40"), "EUR": Decimal("44"), "HUF": Decimal("0.11")},
            metal_holdings=metals or [],
            metal_prices={"XAU": Decimal("4000"), "XAG": Decimal("45")},
            bist_holdings=bist or [],
            try_per_usd=Decimal("40"),
            try_per_eur=Decimal("44"),
        )

    def test_reads_currency_metals_and_bist_from_one_workbook(self):
        self._write(
            currency=[{"asset_code": "USD", "display_name": "ABD Doları", "quantity": "10", "unit": "USD", "average_cost_try": "35"}],
            metals=[{"asset_code": "XAU", "display_name": "Altın", "quantity": "2", "unit": "gr", "average_cost_try": "3500"}],
            bist=[{"symbol": "ASELS", "company": "Aselsan", "quantity": "100", "average_cost": "75", "sector": "Savunma", "notes": ""}],
        )
        result = read_combined_portfolio_excel(
            self.path,
            currency_assets={"USD": ("ABD Doları", "USD"), "EUR": ("Euro", "EUR"), "HUF": ("Forint", "HUF")},
            metal_assets={"XAU": ("Altın", "gr"), "XAG": ("Gümüş", "gr")},
        )
        self.assertEqual(len(result["currency"]), 1)
        self.assertEqual(result["currency"][0]["asset_code"], "USD")
        self.assertEqual(len(result["metals"]), 1)
        self.assertEqual(result["metals"][0]["asset_code"], "XAU")
        self.assertEqual(len(result["bist"]), 1)
        self.assertEqual(result["bist"][0]["symbol"], "ASELS")

    def test_missing_sections_are_empty_and_not_guessed_from_other_sheets(self):
        self._write(
            currency=[{"asset_code": "USD", "display_name": "ABD Doları", "quantity": "10", "unit": "USD", "average_cost_try": "35"}],
        )
        result = read_combined_portfolio_excel(
            self.path,
            currency_assets={"USD": ("ABD Doları", "USD"), "EUR": ("Euro", "EUR"), "HUF": ("Forint", "HUF")},
            metal_assets={"XAU": ("Altın", "gr"), "XAG": ("Gümüş", "gr")},
        )
        self.assertEqual(len(result["currency"]), 1)
        self.assertEqual(result["metals"], [])
        self.assertEqual(result["bist"], [])


    def test_applies_all_sections_once_without_double_counting(self):
        self._write(
            currency=[{"asset_code": "USD", "display_name": "ABD Doları", "quantity": "10", "unit": "USD", "average_cost_try": "35"}],
            metals=[{"asset_code": "XAU", "display_name": "Altın", "quantity": "2", "unit": "gr", "average_cost_try": "3500"}],
            bist=[{"symbol": "ASELS", "company": "Aselsan", "quantity": "100", "average_cost": "75", "sector": "Savunma", "notes": ""}],
        )
        result = read_combined_portfolio_excel(
            self.path,
            currency_assets={"USD": ("ABD Doları", "USD"), "EUR": ("Euro", "EUR"), "HUF": ("Forint", "HUF")},
            metal_assets={"XAU": ("Altın", "gr"), "XAG": ("Gümüş", "gr")},
        )
        currency_store = InvestmentStore(self.root / "currency.db")
        metal_store = InvestmentStore(self.root / "metals.db")
        bist_db = BistDatabase(self.root / "bist.db")
        counts, errors = apply_combined_portfolio_import(
            result, currency_store=currency_store, metal_store=metal_store, bist_database=bist_db
        )
        self.assertEqual(counts, {"currency": 1, "metals": 1, "bist": 1})
        self.assertEqual(errors, [])
        # Importing the same snapshot again replaces values; it does not add units.
        counts_again, errors_again = apply_combined_portfolio_import(
            result, currency_store=currency_store, metal_store=metal_store, bist_database=bist_db
        )
        self.assertEqual(counts_again, counts)
        self.assertEqual(errors_again, [])
        self.assertEqual(currency_store.get_holding("currency", "USD")["quantity"], "10")
        self.assertEqual(metal_store.get_holding("metals", "XAU")["quantity"], "2")
        self.assertEqual(bist_db.get_holding("ASELS")["quantity"], "100")

    def test_icon_assets_are_present(self):
        root = Path(__file__).resolve().parents[1]
        self.assertTrue((root / "assets" / "finance_terminal.svg").is_file())
        self.assertTrue((root / "assets" / "finance_terminal.png").is_file())
        self.assertTrue((root / "assets" / "finance_terminal.ico").is_file())


if __name__ == "__main__":
    unittest.main()
