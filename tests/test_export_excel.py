from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from features.bist.excel_io import read_portfolio_excel, write_portfolio_excel
from features.bist.quotes import Quote, describe_quote
from features.combined_import import read_combined_portfolio_excel
from features.currencies import CURRENCY_INFO
from features.export_templates import (
    TEMPLATE_STATUS,
    template_filename,
    write_bist_template,
    write_combined_template,
    write_investment_template,
)
from features.investment_excel import read_investment_holdings_excel, write_combined_portfolio_excel

METALS = {"XAU": ("Altın", "gr"), "XAG": ("Gümüş", "gr")}
HOLDINGS = [
    {"symbol": "ASELS", "company": "Aselsan", "quantity": "10", "average_cost": "75.50",
     "sector": "Savunma", "notes": "not"},
    {"symbol": "THYAO", "company": "THY", "quantity": "5", "average_cost": "200",
     "sector": "", "notes": ""},
]


def rows(path, sheet=0):
    workbook = load_workbook(path)
    try:
        ws = workbook.worksheets[sheet] if isinstance(sheet, int) else workbook[sheet]
        return [list(r) for r in ws.iter_rows(values_only=True)]
    finally:
        workbook.close()


class BistExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "bist.xlsx"

    def test_export_contains_price_value_profit_loss_and_source(self):
        write_portfolio_excel(
            self.path, HOLDINGS, prices={"ASELS": Decimal("80"), "THYAO": Decimal("180")},
            price_notes={"ASELS": "Yahoo Finance · 13.11.2026", "THYAO": "İş Yatırım · 12.11.2026"},
        )
        data = rows(self.path)
        self.assertEqual(data[0][7:], ["Güncel Fiyat (TL)", "Güncel Değer (TL)",
                                       "Kâr / Zarar (TL)", "Kâr / Zarar (%)", "Fiyat Kaynağı / Zamanı"])
        asels, thyao = data[1], data[2]
        self.assertEqual(asels[7:10], [80, 800, 45])
        self.assertAlmostEqual(asels[10], 45 / 755 * 100)
        self.assertEqual(thyao[9], -100)
        self.assertEqual(asels[11], "Yahoo Finance · 13.11.2026")
        labels = {r[3]: r[4] for r in data if r[3]}
        self.assertEqual(labels["Toplam Maliyet"], 1755)
        self.assertEqual(labels["Kâr / Zarar (TL)"], -55)
        self.assertIn("Hesaplama zamanı", labels)

    def test_missing_price_is_named_and_other_rows_keep_profit_loss(self):
        write_portfolio_excel(self.path, HOLDINGS, prices={"ASELS": Decimal("80")})
        data = rows(self.path)
        self.assertEqual(data[1][9], 45)
        self.assertIsNone(data[2][9])
        self.assertEqual(data[2][11], "Fiyat alınamadı")
        warning = [r[3] for r in data if r[3] and str(r[3]).startswith("⚠")]
        self.assertEqual(len(warning), 1)
        self.assertIn("THYAO", warning[0])

    def test_export_without_any_price_has_no_profit_loss_rows(self):
        write_portfolio_excel(self.path, HOLDINGS)
        labels = [r[3] for r in rows(self.path) if r[3]]
        self.assertNotIn("Kâr / Zarar (TL)", labels)
        self.assertTrue(any(str(label).startswith("⚠") for label in labels))

    def test_export_can_be_imported_again_without_footer_rows(self):
        write_portfolio_excel(self.path, HOLDINGS, prices={"ASELS": Decimal("80")})
        imported = read_portfolio_excel(self.path)
        self.assertEqual([row["symbol"] for row in imported], ["ASELS", "THYAO"])


class CombinedExportTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.path = Path(self._tmp.name) / "all.xlsx"

    def export(self, bist_prices):
        write_combined_portfolio_excel(
            self.path,
            currency_holdings=[{"asset_code": "USD", "display_name": "USD", "unit": "USD",
                                "quantity": "2", "average_cost_try": "30"}],
            currency_prices={"USD": Decimal("35")},
            metal_holdings=[], metal_prices={},
            bist_holdings=HOLDINGS, bist_prices=bist_prices,
            bist_price_notes={"ASELS": "Test · 13.11.2026"},
            try_per_usd=Decimal("35"), try_per_eur=Decimal("38"),
        )
        return {r[0]: r for r in rows(self.path, "Summary") if r and r[0]}

    def test_summary_has_profit_loss_column_with_full_prices(self):
        summary = self.export({"ASELS": Decimal("80"), "THYAO": Decimal("180")})
        self.assertEqual(summary["Portföy"][5], "Kâr / Zarar (₺)")
        self.assertEqual(summary["Döviz"][5], 10)
        self.assertEqual(summary["Hisse Senedi"][2], 800 + 900)
        self.assertEqual(summary["Hisse Senedi"][5], -55)
        self.assertEqual(summary["GENEL TOPLAM"][5], 10 - 55)
        bist = rows(self.path, "Hisse Senedi")
        self.assertEqual(bist[1][7:10], [80, 800, 45])
        self.assertEqual(bist[1][11], "Test · 13.11.2026")

    def test_partial_prices_warn_by_name_and_keep_remaining_profit_loss(self):
        summary = self.export({"ASELS": Decimal("80")})
        self.assertEqual(summary["Hisse Senedi"][5], 45)
        self.assertEqual(summary["Hisse Senedi"][2], 800 + 1000)  # unpriced share at cost
        self.assertEqual(summary["GENEL TOPLAM"][5], 10 + 45)
        notes = " ".join(str(c) for r in rows(self.path, "Summary") for c in r if c)
        self.assertIn("Şu hisse senetlerinin fiyatı alınamadı: THYAO", notes)

    def test_no_prices_means_cost_basis_and_no_stock_profit_loss(self):
        summary = self.export(None)
        self.assertIsNone(summary["Hisse Senedi"][5])
        self.assertEqual(summary["Hisse Senedi"][2], 1755)
        self.assertEqual(summary["GENEL TOPLAM"][5], 10)

    def test_combined_export_still_imports(self):
        self.export({"ASELS": Decimal("80")})
        data = read_combined_portfolio_excel(self.path, currency_assets=CURRENCY_INFO, metal_assets=METALS)
        self.assertEqual((len(data["currency"]), len(data["bist"])), (1, 2))


class TemplateTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def test_template_filename(self):
        self.assertEqual(template_filename("FinanceTerminal_Doviz_Portfoyu.xlsx"),
                         "FinanceTerminal_Doviz_Portfoyu_Ornek_Sablon.xlsx")

    def test_currency_and_metal_templates_have_exactly_one_importable_example(self):
        write_investment_template(self.dir / "c.xlsx", "currency", CURRENCY_INFO)
        write_investment_template(self.dir / "m.xlsx", "metals", METALS)
        currency = read_investment_holdings_excel(self.dir / "c.xlsx", asset_group="currency", allowed_assets=CURRENCY_INFO)
        metals = read_investment_holdings_excel(self.dir / "m.xlsx", asset_group="metals", allowed_assets=METALS)
        self.assertEqual([r["asset_code"] for r in currency], ["USD"])
        self.assertEqual([r["asset_code"] for r in metals], ["XAU"])
        # same layout as the real export, including the profit/loss columns
        header = rows(self.dir / "c.xlsx")[0]
        self.assertIn("Kâr / Zarar (₺)", header)
        self.assertEqual(rows(self.dir / "c.xlsx")[1][8], 500)

    def test_bist_template_has_one_example_with_profit_loss(self):
        write_bist_template(self.dir / "b.xlsx")
        data = rows(self.dir / "b.xlsx")
        self.assertEqual(data[1][0], "ASELS")
        self.assertEqual(data[1][9], 45)
        self.assertEqual([r["symbol"] for r in read_portfolio_excel(self.dir / "b.xlsx")], ["ASELS"])

    def test_combined_template_has_one_example_per_sheet(self):
        write_combined_template(self.dir / "all.xlsx", CURRENCY_INFO, METALS)
        workbook = load_workbook(self.dir / "all.xlsx")
        self.assertEqual(workbook.sheetnames, ["Summary", "Döviz", "Maden", "Hisse Senedi", "Veri Bilgisi"])
        workbook.close()
        data = read_combined_portfolio_excel(self.dir / "all.xlsx", currency_assets=CURRENCY_INFO, metal_assets=METALS)
        self.assertEqual((len(data["currency"]), len(data["metals"]), len(data["bist"])), (1, 1, 1))

    def test_templates_are_marked_as_not_real_data(self):
        write_bist_template(self.dir / "b.xlsx")
        info = " ".join(str(c) for r in rows(self.dir / "b.xlsx", "Veri Bilgisi") for c in r if c)
        self.assertIn(TEMPLATE_STATUS, info)


class DescribeQuoteTests(unittest.TestCase):
    def test_describes_source_and_date(self):
        quote = Quote("A", Decimal("1"), "2026-11-12", "İş Yatırım", "2026-11-13T10:00:00+00:00")
        self.assertEqual(describe_quote(quote), "İş Yatırım · 12.11.2026")

    def test_stale_quote_is_marked_and_missing_time_is_tolerated(self):
        quote = Quote("A", Decimal("1"), None, "Yahoo Finance", "", stale=True)
        self.assertEqual(describe_quote(quote), "Yahoo Finance (eski fiyat)")

    def test_timestamp_is_rendered_in_local_time(self):
        moment = datetime(2026, 11, 13, 10, 0, tzinfo=timezone.utc)
        quote = Quote("A", Decimal("1"), moment.isoformat(timespec="seconds"), "Yahoo Finance", "")
        expected = moment.astimezone().strftime("%d.%m.%Y %H:%M")
        self.assertEqual(describe_quote(quote), f"Yahoo Finance · {expected}")


if __name__ == "__main__":
    unittest.main()
