"""Offscreen smoke test for the new investment register UI."""

import os
import tempfile
import unittest
from pathlib import Path
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication, QAbstractItemView, QHeaderView
    from features.investment_store import InvestmentStore
    from features.investment_panel import InvestmentPanel
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed in this environment")
class InvestmentUiSmokeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_panel_displays_cost_and_live_value(self):
        with tempfile.TemporaryDirectory() as temp:
            store = InvestmentStore(Path(temp) / "ui-test.db")
            store.add_purchase("currency", "USD", "10", "30", display_name="ABD Doları", unit="USD")
            panel = InvestmentPanel(
                asset_group="currency",
                assets={"USD": ("ABD Doları", "USD")},
                quantity_label="Miktar",
                title="Test Portföyü",
                export_filename="test.xlsx",
                store=store,
            )
            panel.set_prices(
                {"USD": Decimal("32")},
                rates_updated_at="04.11.2026 16:45:00",
                rates_status="Online",
            )
            self.assertEqual(panel.table.rowCount(), 1)
            self.assertEqual(panel.table.item(0, 3).text(), "300,00")
            self.assertEqual(panel.table.item(0, 5).text(), "320,00")
            self.assertEqual(panel.table.item(0, 6).text(), "20,00")
            self.assertEqual(panel.import_button.text(), "Excel'den İçe Aktar")
            self.assertEqual(panel.export_button.text(), "Excel'e Aktar")
            self.assertEqual(panel.table.selectionMode(), QAbstractItemView.SelectionMode.ExtendedSelection)
            self.assertEqual(panel.delete_all_button.text(), "Tüm Kayıtları Sil")
            self.assertEqual(panel.clear_button.text(), "Formu Temizle")
            self.assertIn("04.11.2026 16:45:00", panel.last_update_label.text())
            self.assertIn("Online", panel.last_update_label.text())
            self.assertEqual(
                panel.table.horizontalHeader().sectionResizeMode(0),
                QHeaderView.ResizeMode.Interactive,
            )
            panel.close()


if __name__ == "__main__":
    unittest.main()
