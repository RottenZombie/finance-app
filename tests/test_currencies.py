from __future__ import annotations

import re
import unittest
from unittest.mock import Mock, patch

from core.api import get_all_rates, parse_tcmb_xml
from features.currencies import (
    CURRENCY_INFO,
    CURRENCY_RANKING,
    DEFAULT_CURRENCY_CODES,
    currency_choices,
    currency_display_name,
    currency_rank,
    localized_currency_assets,
    sort_currency_codes,
)


class RankingTests(unittest.TestCase):
    def test_top_of_the_list_follows_global_fx_turnover(self):
        # BIS Triennial Survey 2025: USD, EUR, JPY, GBP, CNY, CHF, AUD, CAD, HKD, SGD
        self.assertEqual(
            list(CURRENCY_RANKING[:10]),
            ["USD", "EUR", "JPY", "GBP", "CNY", "CHF", "AUD", "CAD", "HKD", "SGD"],
        )

    def test_every_list_uses_the_same_order(self):
        self.assertEqual(list(CURRENCY_INFO), [c for c in CURRENCY_RANKING if c != "TRY"])
        self.assertEqual(currency_choices(), list(CURRENCY_INFO))
        with_try = currency_choices(include_try=True)
        self.assertEqual([c for c in with_try if c != "TRY"], currency_choices())
        self.assertEqual(list(localized_currency_assets()), currency_choices())

    def test_codes_are_unique_iso_style_and_named_in_both_languages(self):
        self.assertEqual(len(set(CURRENCY_RANKING)), len(CURRENCY_RANKING))
        for code in CURRENCY_RANKING:
            self.assertRegex(code, r"^[A-Z]{3}$")
            for language in ("tr", "en"):
                self.assertNotEqual(currency_display_name(code, language), code, f"{code}/{language}")

    def test_romanian_leu_and_the_new_currencies_are_available(self):
        for code in ("RON", "UAH", "RSD", "GEL", "AZN", "EGP", "ILS", "MYR", "KZT"):
            self.assertIn(code, CURRENCY_INFO)
        self.assertEqual(currency_display_name("RON", "tr"), "Romen Leyi")
        self.assertEqual(currency_display_name("RON", "en"), "Romanian Leu")

    def test_previously_supported_currencies_are_still_supported(self):
        for code in ("USD", "EUR", "HUF", "GBP", "CHF", "SEK", "NOK", "DKK", "PLN", "CZK", "JPY", "CNY", "RUB"):
            self.assertIn(code, CURRENCY_INFO)
        for code in DEFAULT_CURRENCY_CODES:
            self.assertIn(code, CURRENCY_INFO)

    def test_sorting_helpers(self):
        self.assertEqual(sort_currency_codes(["HUF", "eur", "SEK", "usd", "EUR"]), ["USD", "EUR", "SEK", "HUF"])
        self.assertLess(currency_rank("USD"), currency_rank("EUR"))
        self.assertGreater(currency_rank("ZZZ"), currency_rank("KZT"))   # unknown codes go last
        self.assertEqual(currency_choices(exclude=("USD", "EUR"))[0], "JPY")


class RateProviderTests(unittest.TestCase):
    @patch("core.api.requests.get")
    def test_every_supported_currency_gets_a_rate_from_the_provider(self, get):
        response = Mock()
        rates = {"TRY": 35.0, **{code: 2.0 for code in CURRENCY_INFO}}
        response.json.return_value = {"rates": rates}
        get.return_value = response
        result = get_all_rates()
        self.assertEqual(result["status"], "Online")
        for code in CURRENCY_INFO:
            self.assertIsNotNone(result[code], code)
        self.assertAlmostEqual(result["RON"], 17.5)           # 35 TRY per USD / 2 RON per USD

    def test_tcmb_fallback_understands_the_romanian_leu(self):
        xml = b"""<?xml version="1.0"?><Tarih_Date>
        <Currency Kod="USD"><Unit>1</Unit><ForexBuying>35.00</ForexBuying><ForexSelling>35.10</ForexSelling></Currency>
        <Currency Kod="RON"><Unit>1</Unit><ForexBuying>7.00</ForexBuying><ForexSelling>7.10</ForexSelling></Currency>
        </Tarih_Date>"""
        self.assertAlmostEqual(parse_tcmb_xml(xml)["RON"], 7.05)

    def test_currency_names_are_never_empty(self):
        for code, (name, unit) in CURRENCY_INFO.items():
            self.assertTrue(name.strip())
            self.assertEqual(unit, code)
            self.assertFalse(re.search(r"\d", name))


if __name__ == "__main__":
    unittest.main()
