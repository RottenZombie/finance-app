"""Offscreen tests for the app's compact portfolio summary page."""

import os
import unittest
from decimal import Decimal

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

try:
    from PySide6.QtWidgets import QApplication
    from features.summary import SummaryPage
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed in this environment")
class SummaryUiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_summary_totals_are_converted_and_updated(self):
        page = SummaryPage()
        page.update_summary(
            currency_holdings=[{"asset_code": "USD", "quantity": "2", "average_cost_try": "30"}],
            currency_prices={"USD": Decimal("35")},
            metal_holdings=[{"asset_code": "XAU", "quantity": "1", "average_cost_try": "2800"}],
            metal_prices={"XAU": Decimal("3000")},
            bist_holdings=[{"quantity": "10", "average_cost": "100"}],
            try_per_usd=Decimal("35"),
            try_per_eur=Decimal("38"),
        )
        self.assertEqual(page._value_labels[("currency", "TRY")].text(), "70,00")
        self.assertEqual(page._value_labels[("metals", "TRY")].text(), "3.000,00")
        self.assertEqual(page._value_labels[("bist", "TRY")].text(), "1.000,00")
        self.assertEqual(page._value_labels[("total", "TRY")].text(), "4.070,00")
        self.assertEqual(page._value_labels[("total", "USD")].text(), "116,29")
        self.assertEqual(page._value_labels[("currency", "PL")].text(), "+10,00 ₺")
        self.assertEqual(page._value_labels[("metals", "PL")].text(), "+200,00 ₺")
        self.assertEqual(page._value_labels[("bist", "PL")].text(), "Canlı fiyat yok")
        self.assertEqual(page._value_labels[("total", "PL")].text(), "+210,00 ₺")
        page.close()


if __name__ == "__main__":
    unittest.main()
