"""Portfolio and Metals calculators (needs PySide6; skipped otherwise)."""
import os
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from core.i18n import set_language
from features.currencies import CURRENCY_INFO, currency_choices

try:
    from PySide6.QtWidgets import QApplication
    from features.metals import Metals
    from features.portfolio import Portfolio
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False


def codes(combo) -> list[str]:
    return [combo.itemData(index) for index in range(combo.count())]


def texts(combo) -> list[str]:
    return [combo.itemText(index) for index in range(combo.count())]


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed in this environment")
class CalculatorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        patcher = patch("features.investment_store.default_database_path",
                        lambda: Path(self._tmp.name) / "holdings.db")
        patcher.start()
        self.addCleanup(patcher.stop)
        self.addCleanup(set_language, "tr")

    # ---------------------------------------------------------------- Portfolio
    def test_extra_currency_list_is_ranked_and_excludes_the_fixed_inputs(self):
        portfolio = Portfolio()
        extra = codes(portfolio.extra_currency)
        self.assertNotIn("USD", extra)
        self.assertNotIn("EUR", extra)
        self.assertNotIn("TRY", extra)
        self.assertIn("RON", extra)
        self.assertEqual(extra, currency_choices(exclude=("USD", "EUR")))
        self.assertEqual(codes(portfolio.out_currency), currency_choices())
        self.assertEqual(portfolio.selected_extra_code(), "HUF")
        self.assertEqual(portfolio.selected_output_code(), "EUR")

    def test_saved_extra_currency_is_restored_and_bad_values_fall_back(self):
        self.assertEqual(Portfolio(extra_currency="SEK").selected_extra_code(), "SEK")
        self.assertEqual(Portfolio(extra_currency="NOPE").selected_extra_code(), "HUF")
        self.assertEqual(Portfolio(extra_currency="usd").selected_extra_code(), "HUF")

    def test_changing_the_extra_currency_is_announced_for_saving(self):
        portfolio = Portfolio()
        seen = []
        portfolio.extra_currency_changed.connect(seen.append)
        portfolio.extra_currency.setCurrentIndex(portfolio.extra_currency.findData("SEK"))
        self.assertEqual(seen, ["SEK"])

    def test_any_currency_can_be_entered_and_converted(self):
        portfolio = Portfolio(extra_currency="SEK")
        portfolio.set_rates({"USD": 35, "EUR": 38, "SEK": 3.5, "RON": 7.0})
        portfolio.usd.setText("10")
        portfolio.eur.setText("5")
        portfolio.extra.setText("100")      # 100 SEK
        portfolio.try_in.setText("50")
        portfolio.calc()
        self.assertIn("940,00 TRY", portfolio.result.text())      # 350 + 190 + 350 + 50
        self.assertIn("24,74 EUR", portfolio.result.text())       # 940 / 38

        portfolio.out_currency.setCurrentIndex(portfolio.out_currency.findData("RON"))
        portfolio.calc()
        self.assertIn("134,29 RON", portfolio.result.text())      # 940 / 7

    def test_amount_without_a_rate_is_reported_not_counted_as_zero(self):
        portfolio = Portfolio(extra_currency="SEK")
        portfolio.set_rates({"USD": 35, "EUR": 38})              # no SEK rate
        portfolio.extra.setText("100")
        portfolio.calc()
        self.assertEqual(portfolio.result.text(), "Kur bilgisi yok: SEK")
        portfolio.extra.setText("0")                             # nothing entered -> fine
        portfolio.usd.setText("1")
        portfolio.calc()
        self.assertIn("35,00 TRY", portfolio.result.text())

    def test_output_currency_without_a_rate(self):
        portfolio = Portfolio()
        portfolio.set_rates({"USD": 35, "EUR": 38})
        portfolio.usd.setText("1")
        portfolio.out_currency.setCurrentIndex(portfolio.out_currency.findData("RON"))
        portfolio.calc()
        self.assertIn("RON: Kur yok", portfolio.result.text())

    def test_invalid_input_shows_an_error_instead_of_raising(self):
        portfolio = Portfolio()
        portfolio.usd.setText("abc")
        portfolio.calc()
        self.assertTrue(portfolio.result.text().startswith("Hata:"))

    def test_english_labels(self):
        set_language("en")
        portfolio = Portfolio()
        self.assertEqual(portfolio.result.text(), "Result: -")
        self.assertIn("SEK — Swedish Krona", texts(portfolio.extra_currency))
        self.assertIn("EUR — Euro", texts(portfolio.out_currency))

    # ------------------------------------------------------------------- Metals
    def test_metals_output_offers_every_currency_in_the_shared_order(self):
        metals = Metals()
        self.assertEqual(codes(metals.out_currency), currency_choices(include_try=True))
        self.assertEqual(str(metals.out_currency.currentData()), "TRY")
        self.assertIn("RON", codes(metals.out_currency))

    def test_metals_convert_to_any_currency(self):
        metals = Metals()
        metals.set_rates(3110.35, 31.1035, 35, eur_try=38, rates={"SEK": 3.5, "USD": 35, "EUR": 38})
        metals.gold_input.setText("1")                  # 1 g gold = 100 USD = 3500 TRY
        for code, expected in (("TRY", "3.500,00 TRY"), ("USD", "100,00 USD"),
                               ("EUR", "92,11 EUR"), ("SEK", "1.000,00 SEK")):
            metals.out_currency.setCurrentIndex(metals.out_currency.findData(code))
            metals.calc()
            self.assertIn(expected, metals.result.text(), code)

    def test_metals_output_without_a_rate_says_so(self):
        metals = Metals()
        metals.set_rates(3110.35, None, 35, eur_try=38, rates={})
        metals.gold_input.setText("1")
        metals.out_currency.setCurrentIndex(metals.out_currency.findData("RON"))
        metals.calc()
        self.assertIn("RON: Kur yok", metals.result.text())

    def test_every_supported_currency_has_a_name_in_both_languages(self):
        from features.currencies import currency_display_name
        for code in CURRENCY_INFO:
            self.assertNotEqual(currency_display_name(code, "tr"), code, code)
            self.assertNotEqual(currency_display_name(code, "en"), code, code)


if __name__ == "__main__":
    unittest.main()
