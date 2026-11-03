"""Offscreen smoke test for the BIST PySide6 tab.

This test is skipped on environments without PySide6. On developer machines
with the project requirements installed, it catches Qt widget lifetime and
initialization errors before the full application is launched.
"""

import os
import tempfile
import unittest
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from features.bist.database import BistDatabase
    from features.bist.portfolio_tab import BistPortfolioTab
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
            database.upsert_holding("ASELS", "10", "75,50")
            tab.refresh_table()
            self.assertEqual(tab.table.rowCount(), 1)
            self.assertEqual(tab.count_value.text(), "1")
            self.assertEqual(tab.cost_value.text(), "755,00 ₺")

            tab.close()


if __name__ == "__main__":
    unittest.main()
