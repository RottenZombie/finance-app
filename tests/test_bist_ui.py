"""Offscreen smoke test for the BIST PySide6 tab.

This test is skipped on environments without PySide6. On developer machines
with the project requirements installed, it catches Qt widget lifetime and
initialization errors before the full application is launched.
"""

import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView
    from features.bist.database import BistDatabase
    from features.bist.portfolio_tab import BistPortfolioTab
    from features.export_dialog import EXPORT, TEMPLATE
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed in this environment")
class BistUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_bist_tab_initializes_with_live_metric_cards(self):
        with tempfile.TemporaryDirectory() as temp:
            database = BistDatabase(Path(temp) / "ui-test.db")
            tab = BistPortfolioTab(database=database)

            self.assertEqual(tab.table.rowCount(), 0)
            self.assertEqual(tab.count_value.text(), "0")
            self.assertEqual(tab.cost_value.text(), "0,00 ₺")
            self.assertIsNotNone(tab.count_card)
            self.assertIsNotNone(tab.cost_card)

            # Exercise a refresh after inserting a holding. This verifies that
            # both QLabel wrappers still refer to live Qt objects.
            database.upsert_holding("ASELS", "10", "75,50", notes="Uzun vadeli takip")
            tab.refresh_table()
            self.assertEqual(tab.table.rowCount(), 1)
            self.assertEqual(tab.count_value.text(), "1")
            self.assertEqual(tab.cost_value.text(), "755,00 ₺")
            self.assertEqual(tab.table.selectionMode(), QAbstractItemView.SelectionMode.ExtendedSelection)
            self.assertEqual(tab.table.columnCount(), 12)
            self.assertEqual(tab.table.item(0, 10).text(), "Uzun vadeli takip")
            self.assertEqual(tab.table.item(0, 5).text(), "–")
            self.assertEqual(tab.market_value.text(), "Fiyat yok")
            self.assertEqual(tab.pl_value.text(), "Veri yok")
            self.assertEqual(
                tab.table.horizontalHeader().sectionResizeMode(1),
                QHeaderView.ResizeMode.Interactive,
            )
            self.assertEqual(tab.clear_button.text(), "Formu Temizle")
            self.assertEqual(tab.delete_all_button.text(), "Tüm Kayıtları Sil")

            # Delayed quotes fill the price, value and profit/loss columns.
            changes = []
            tab.portfolio_changed.connect(lambda: changes.append(True))
            tab.set_quotes({
                "quotes": {"ASELS": {
                    "price": "80", "as_of": "2026-11-13T10:00:00+00:00", "source": "Test",
                    "fetched_at": "2026-11-13T10:00:00+00:00", "stale": False,
                }},
                "live": ["ASELS"], "cached": [], "failed": [],
            })
            self.assertEqual(changes, [True])
            self.assertEqual(tab.table.item(0, 5).text(), "80,00 ₺")
            self.assertEqual(tab.table.item(0, 6).text(), "800,00 ₺")
            self.assertEqual(tab.table.item(0, 7).text(), "+45,00 ₺")
            self.assertEqual(tab.table.item(0, 8).text(), "+5,96 %")
            self.assertEqual(tab.market_value.text(), "800,00 ₺")
            self.assertEqual(tab.pl_value.text(), "+45,00 ₺ (+5,96 %)")
            self.assertEqual(tab.price_map(), {"ASELS": Decimal("80.0000")})

            # Stale (cached) prices are visibly marked.
            tab.set_quotes({
                "quotes": {"ASELS": {
                    "price": "80", "as_of": None, "source": "Test",
                    "fetched_at": "2026-11-13T10:00:00+00:00", "stale": True,
                }},
                "live": [], "cached": ["ASELS"], "failed": [],
            })
            self.assertEqual(tab.table.item(0, 5).text(), "80,00 ₺ (eski)")

            # Garbage must never crash the tab.
            tab.set_quotes(None)
            self.assertEqual(tab.table.item(0, 5).text(), "–")

            requested = []
            tab.refresh_requested.connect(lambda: requested.append(True))
            tab.refresh_prices_button.click()
            self.assertEqual(requested, [True])

            tab.close()

    def _quotes(self, *symbols, stale=False):
        return {
            "quotes": {
                symbol: {
                    "price": "80", "as_of": "2026-11-13", "source": "Test",
                    "fetched_at": "2026-11-13T10:00:00+00:00", "stale": stale,
                }
                for symbol in symbols
            },
            "live": list(symbols), "cached": [], "failed": [],
        }

    def test_partial_prices_show_profit_loss_of_priced_shares_only(self):
        with tempfile.TemporaryDirectory() as temp:
            database = BistDatabase(Path(temp) / "partial.db")
            database.upsert_holding("ASELS", "10", "75,50")
            database.upsert_holding("THYAO", "5", "200")
            tab = BistPortfolioTab(database=database)
            self.assertIsNone(tab.price_map())  # no lookup finished yet

            payload = self._quotes("ASELS")
            payload["failed"] = ["THYAO"]
            tab.set_quotes(payload)
            self.assertEqual(tab.pl_value.text(), "+45,00 ₺ (+5,96 %) (kısmi)")
            self.assertTrue(tab.market_value.text().startswith("800,00 ₺ (kısmi: 1/2)"))
            self.assertIn("THYAO", tab.notice.text())
            self.assertEqual(tab.price_map(), {"ASELS": Decimal("80.0000")})
            self.assertIn("Test", tab.price_notes()["ASELS"])
            tab.close()

    def test_export_choice_cancel_template_and_data(self):
        import features.bist.portfolio_tab as module

        with tempfile.TemporaryDirectory() as temp:
            database = BistDatabase(Path(temp) / "export.db")
            database.upsert_holding("ASELS", "10", "75,50")
            tab = BistPortfolioTab(database=database)
            tab.set_quotes(self._quotes("ASELS"))

            with patch.object(module, "ask_export_mode", return_value=None), \
                    patch.object(module, "QFileDialog") as dialog:
                tab.export_excel()
                dialog.getSaveFileName.assert_not_called()

            with patch.object(module, "ask_export_mode", return_value=TEMPLATE), \
                    patch.object(module, "run_template_export") as template:
                tab.export_excel()
                template.assert_called_once()
                self.assertEqual(
                    template.call_args.kwargs["default_name"], "BIST_Portfoy_Ornek_Sablon.xlsx"
                )

            target = Path(temp) / "bist.xlsx"
            with patch.object(module, "ask_export_mode", return_value=EXPORT), \
                    patch.object(module, "QMessageBox"), \
                    patch.object(module, "QFileDialog") as dialog:
                dialog.getSaveFileName.return_value = (str(target), "")
                tab.export_excel()
            self.assertTrue(target.exists())
            from openpyxl import load_workbook
            sheet = load_workbook(target).worksheets[0]
            self.assertEqual(sheet.cell(2, 10).value, 45)  # profit/loss at export time
            tab.close()



if __name__ == "__main__":
    unittest.main()