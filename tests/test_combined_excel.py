import tempfile
import unittest
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from features.investment_excel import read_investment_holdings_excel, write_combined_portfolio_excel
from features.investment_store import InvestmentStore
from features.bist.database import BistDatabase
from features.bist.excel_io import read_portfolio_excel


class CombinedExcelTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        self.investments = InvestmentStore(self.root / "investments.db")
        self.bist = BistDatabase(self.root / "bist.db")

    def tearDown(self):
        self.temp.cleanup()

    def test_import_snapshot_replaces_existing_instead_of_double_counting(self):
        self.investments.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
        self.investments.set_holding(
            "currency", "USD", "25", "34", display_name="ABD Doları", unit="USD"
        )
        holding = self.investments.get_holding("currency", "USD")
        self.assertEqual(Decimal(holding["quantity"]), Decimal("25"))
        self.assertEqual(Decimal(holding["average_cost_try"]), Decimal("34"))

    def test_combined_workbook_summary_and_sheets(self):
        self.investments.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
        self.investments.add_purchase("metals", "XAU", "2", "3000", display_name="Altın", unit="gr")
        self.bist.upsert_holding("ASELS", "100", "75", company="Aselsan")

        path = self.root / "all.xlsx"
        write_combined_portfolio_excel(
            path,
            currency_holdings=self.investments.list_holdings("currency"),
            currency_prices={"USD": Decimal("32")},
            metal_holdings=self.investments.list_holdings("metals"),
            metal_prices={"XAU": Decimal("3500")},
            bist_holdings=self.bist.list_holdings(),
            try_per_usd=Decimal("32"),
            try_per_eur=Decimal("35"),
        )

        workbook = load_workbook(path, data_only=True)
        self.assertEqual(workbook.sheetnames, ["Summary", "Döviz", "Maden", "Hisse Senedi", "Veri Bilgisi"])
        summary = workbook["Summary"]
        self.assertEqual(summary["A5"].value, "Döviz")
        self.assertEqual(summary["C5"].value, 320.0)
        self.assertEqual(summary["A7"].value, "Hisse Senedi")
        self.assertEqual(summary["C7"].value, 7500.0)
        self.assertEqual(summary["A8"].value, "GENEL TOPLAM")
        self.assertEqual(summary["C8"].value, 14820.0)
        metadata = workbook["Veri Bilgisi"]
        self.assertIn("Excel oluşturulma zamanı", metadata["A2"].value)
        self.assertEqual(metadata["A6"].value, "Döviz sağlayıcı sitesi")
        self.assertEqual(metadata["B6"].value, "https://www.exchangerate-api.com/")
        self.assertEqual(metadata["A8"].value, "Altın sağlayıcı sitesi")
        self.assertEqual(metadata["B8"].value, "https://gold-api.com/")
        self.assertEqual(metadata["A10"].value, "Gümüş sağlayıcı sitesi")
        self.assertEqual(metadata["B10"].value, "https://gold-api.com/")
        visible_sources = " ".join(
            str(metadata.cell(row, column).value or "")
            for row in range(1, metadata.max_row + 1)
            for column in (1, 2)
        )
        self.assertNotIn("/v6/latest/", visible_sources)
        self.assertNotIn("/price/XAU", visible_sources)
        self.assertNotIn("/price/XAG", visible_sources)
        self.assertTrue(metadata["B6"].hyperlink)
        self.assertTrue(metadata["B8"].hyperlink)
        workbook.close()

    def test_currency_import_reads_combined_workbook_and_bist_import_skips_summary(self):
        self.investments.add_purchase("currency", "EUR", "4", "35", display_name="Euro", unit="EUR")
        self.bist.upsert_holding("THYAO", "20", "250", company="Türk Hava Yolları")
        path = self.root / "combined.xlsx"
        write_combined_portfolio_excel(
            path,
            currency_holdings=self.investments.list_holdings("currency"),
            currency_prices={"EUR": Decimal("38")},
            metal_holdings=[],
            metal_prices={},
            bist_holdings=self.bist.list_holdings(),
            try_per_usd=Decimal("32"),
            try_per_eur=Decimal("38"),
        )
        currency_rows = read_investment_holdings_excel(
            path,
            asset_group="currency",
            allowed_assets={"USD": ("ABD Doları", "USD"), "EUR": ("Euro", "EUR"), "HUF": ("Forint", "HUF")},
        )
        self.assertEqual(currency_rows[0]["asset_code"], "EUR")
        self.assertEqual(currency_rows[0]["quantity"], Decimal("4"))
        bist_rows = read_portfolio_excel(path)
        self.assertEqual(len(bist_rows), 1)
        self.assertEqual(bist_rows[0]["symbol"], "THYAO")


if __name__ == "__main__":
    unittest.main()
