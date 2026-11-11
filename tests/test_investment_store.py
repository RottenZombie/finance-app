import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from features.investment_store import (
    InvestmentStore,
    format_localized,
    format_quantity,
    parse_localized_decimal,
    write_holdings_excel,
)


class InvestmentStoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = InvestmentStore(Path(self.temp.name) / "investments.db")

    def tearDown(self):
        self.temp.cleanup()


    def test_large_numbers_use_turkish_grouping_and_decimal_separators(self):
        self.assertEqual(format_localized(Decimal("123456789.12")), "123.456.789,12")
        self.assertEqual(format_quantity(Decimal("1234567.5000")), "1.234.567,5")

    def test_turkish_number_parsing(self):
        self.assertEqual(parse_localized_decimal("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_localized_decimal("74,50"), Decimal("74.50"))
        self.assertEqual(parse_localized_decimal("1,234.56"), Decimal("1234.56"))

    def test_repeat_purchases_merge_using_weighted_average(self):
        self.store.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
        holding = self.store.add_purchase("currency", "USD", "10", "40", display_name="ABD Doları", unit="USD")
        self.assertEqual(Decimal(holding["quantity"]), Decimal("20"))
        self.assertEqual(Decimal(holding["average_cost_try"]), Decimal("35"))


    def test_currency_catalog_includes_chf_and_czk(self):
        self.store.add_purchase("currency", "CHF", "2", "40", display_name="İsviçre Frangı", unit="CHF")
        self.store.add_purchase("currency", "CZK", "100", "1.5", display_name="Çek Korunası", unit="CZK")
        self.assertEqual(
            [row["asset_code"] for row in self.store.list_holdings("currency")],
            ["CHF", "CZK"],
        )

    def test_set_holding_replaces_quantity_and_average_cost(self):
        self.store.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
        self.store.set_holding("currency", "USD", "5", "42", display_name="ABD Doları", unit="USD")
        holding = self.store.get_holding("currency", "USD")
        self.assertEqual(Decimal(holding["quantity"]), Decimal("5"))
        self.assertEqual(Decimal(holding["average_cost_try"]), Decimal("42"))

    def test_asset_groups_are_separate(self):
        self.store.add_purchase("currency", "USD", "5", "30", display_name="ABD Doları", unit="USD")
        self.store.add_purchase("metals", "XAU", "5", "2500", display_name="Altın", unit="gr")
        self.assertEqual(len(self.store.list_holdings("currency")), 1)
        self.assertEqual(len(self.store.list_holdings("metals")), 1)

    def test_delete_and_validation(self):
        self.store.add_purchase("metals", "XAG", "100", "35", display_name="Gümüş", unit="gr")
        self.assertTrue(self.store.delete_holding("metals", "XAG"))
        self.assertFalse(self.store.list_holdings("metals"))
        with self.assertRaises(ValueError):
            self.store.add_purchase("currency", "USD", "0", "30", display_name="ABD Doları", unit="USD")
        with self.assertRaises(ValueError):
            self.store.add_purchase("currency", "XAU", "1", "30", display_name="Yanlış", unit="USD")

    def test_delete_selected_and_all_holdings(self):
        self.store.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
        self.store.add_purchase("currency", "EUR", "5", "35", display_name="Euro", unit="EUR")
        self.store.add_purchase("metals", "XAU", "1", "3000", display_name="Altın", unit="gr")

        self.assertEqual(self.store.delete_holdings("currency", ["USD"]), 1)
        self.assertEqual([row["asset_code"] for row in self.store.list_holdings("currency")], ["EUR"])
        self.assertEqual(self.store.delete_all("currency"), 1)
        self.assertEqual(self.store.list_holdings("currency"), [])
        self.assertEqual(len(self.store.list_holdings("metals")), 1)

    def test_excel_export_contains_cost_and_current_valuation(self):
        self.store.add_purchase("currency", "EUR", "4", "35", display_name="Euro", unit="EUR")
        rows = self.store.list_holdings("currency")
        path = Path(self.temp.name) / "export.xlsx"
        write_holdings_excel(path, rows, {"EUR": Decimal("38")}, title="Döviz Portföyü")
        workbook = load_workbook(path, data_only=True)
        try:
            sheet = workbook.active
            self.assertEqual(sheet.max_row, 2)
            self.assertEqual(sheet.cell(2, 6).value, 140.0)
            self.assertEqual(sheet.cell(2, 8).value, 152.0)
            self.assertEqual(sheet.cell(2, 9).value, 12.0)
        finally:
            workbook.close()

        metadata_workbook = load_workbook(path, read_only=True)
        try:
            self.assertIn("Veri Bilgisi", metadata_workbook.sheetnames)
        finally:
            metadata_workbook.close()


if __name__ == "__main__":
    unittest.main()
