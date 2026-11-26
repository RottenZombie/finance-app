from __future__ import annotations

import re
import tempfile
import unittest
from datetime import datetime, timezone
from decimal import Decimal
from pathlib import Path

from openpyxl import load_workbook

from core import i18n
from core.help_text import HELP_EN, HELP_TR, help_html
from core.i18n import set_language, tr
from core.translations_en import EN
from tools.i18n_keys import collect_keys

TURKISH_LETTERS = re.compile(r"[çğıöşüÇĞİÖŞÜâîû]")
# Proper nouns / provider names that legitimately keep Turkish letters in English text.
ALLOWED_NAMES = ("İş Yatırım", "Türkçe")
PLACEHOLDER = re.compile(r"\{(\d+)(?:![sra])?(?::[^}]*)?\}")


class LanguageSwitchMixin:
    def setUp(self):
        set_language("en")
        self.addCleanup(set_language, "tr")


class TranslationTableTests(unittest.TestCase):
    def test_every_text_passed_to_tr_has_an_english_entry(self):
        missing = [key for key in collect_keys() if key not in EN]
        self.assertEqual(missing, [], "texts without an English translation")

    def test_no_unused_english_entries(self):
        used = set(collect_keys())
        self.assertEqual(sorted(key for key in EN if key not in used), [])

    def test_placeholders_are_identical_in_both_languages(self):
        for key, english in EN.items():
            self.assertEqual(
                sorted(PLACEHOLDER.findall(key)), sorted(PLACEHOLDER.findall(english)),
                f"placeholder mismatch: {key[:70]!r}",
            )

    def test_english_text_formats_without_stray_braces(self):
        for key, english in EN.items():
            count = len(set(PLACEHOLDER.findall(english)))
            try:
                english.format(*([1.5] * (count or 1)))
            except (IndexError, KeyError, ValueError) as exc:
                self.fail(f"cannot format {english[:70]!r}: {exc}")

    def test_english_text_contains_no_turkish_letters(self):
        for key, english in EN.items():
            cleaned = english
            for name in ALLOWED_NAMES:
                cleaned = cleaned.replace(name, "")
            self.assertIsNone(TURKISH_LETTERS.search(cleaned), f"Turkish text left in: {english[:80]!r}")

    def test_identical_translations_are_only_words_that_are_the_same_in_both_languages(self):
        same = [key for key, english in EN.items() if key == english]
        self.assertTrue(all(not TURKISH_LETTERS.search(key) for key in same), same)


class RuntimeTests(unittest.TestCase):
    def tearDown(self):
        set_language("tr")

    def test_turkish_is_the_source_language_and_default(self):
        set_language("tr")
        self.assertEqual(tr("Kaydet"), "Kaydet")
        self.assertEqual(i18n.get_language(), "tr")

    def test_english_lookup_and_unknown_text_fallback(self):
        set_language("en")
        self.assertEqual(tr("Kaydet"), "Save")
        self.assertEqual(tr("bu metin sözlükte yok"), "bu metin sözlükte yok")

    def test_language_codes_are_normalised(self):
        self.assertEqual(set_language("EN"), "en")
        self.assertEqual(set_language("en-US"), "en")
        self.assertEqual(set_language("de"), "tr")
        self.assertEqual(set_language(None), "tr")

    def test_translate_is_independent_of_the_active_language(self):
        set_language("tr")
        self.assertEqual(i18n.translate("Kaydet", "en"), "Save")
        self.assertEqual(i18n.translate("Kaydet", "tr"), "Kaydet")

    def test_help_exists_in_both_languages_with_the_same_structure(self):
        self.assertNotEqual(HELP_TR, HELP_EN)
        for tag in ("<h2>", "<h3>"):
            self.assertEqual(HELP_TR.count(tag), HELP_EN.count(tag), tag)
        set_language("en")
        self.assertIs(help_html(), HELP_EN)
        set_language("tr")
        self.assertIs(help_html(), HELP_TR)
        self.assertIsNone(TURKISH_LETTERS.search(HELP_EN.replace("Türkçe", "")))


def all_strings(path) -> list[str]:
    workbook = load_workbook(path)
    try:
        found = list(workbook.sheetnames)
        for sheet in workbook.worksheets:
            for row in sheet.iter_rows(values_only=True):
                found.extend(str(value) for value in row if isinstance(value, str))
        return found
    finally:
        workbook.close()


class EnglishExportTests(LanguageSwitchMixin, unittest.TestCase):
    """English mode must not leak Turkish into files, and files must import back."""

    def setUp(self):
        super().setUp()
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.dir = Path(self._tmp.name)

    def assert_english(self, path):
        for text in all_strings(path):
            cleaned = text
            for name in ALLOWED_NAMES:
                cleaned = cleaned.replace(name, "")
            self.assertIsNone(TURKISH_LETTERS.search(cleaned), f"{path.name}: {text!r}")

    def test_english_templates_are_english_and_import_back(self):
        from features.bist.excel_io import read_portfolio_excel
        from features.combined_import import read_combined_portfolio_excel
        from features.currencies import localized_currency_assets
        from features.export_templates import (
            write_bist_template, write_combined_template, write_investment_template,
        )
        from features.investment_excel import read_investment_holdings_excel
        from features.currencies import metal_assets

        currency, metals = localized_currency_assets(), metal_assets()
        write_investment_template(self.dir / "c.xlsx", "currency", currency)
        write_investment_template(self.dir / "m.xlsx", "metals", metals)
        write_bist_template(self.dir / "b.xlsx")
        write_combined_template(self.dir / "all.xlsx", currency, metals)
        for name in ("c", "m", "b", "all"):
            self.assert_english(self.dir / f"{name}.xlsx")

        workbook = load_workbook(self.dir / "all.xlsx")
        self.assertEqual(workbook.sheetnames, ["Summary", "Currency", "Metals", "Stocks", "Data Info"])
        workbook.close()

        rows = read_investment_holdings_excel(self.dir / "c.xlsx", asset_group="currency", allowed_assets=currency)
        self.assertEqual([r["asset_code"] for r in rows], ["USD"])
        rows = read_investment_holdings_excel(self.dir / "m.xlsx", asset_group="metals", allowed_assets=metals)
        self.assertEqual([r["asset_code"] for r in rows], ["XAU"])
        self.assertEqual([r["symbol"] for r in read_portfolio_excel(self.dir / "b.xlsx")], ["ASELS"])
        data = read_combined_portfolio_excel(self.dir / "all.xlsx", currency_assets=currency, metal_assets=metals)
        self.assertEqual((len(data["currency"]), len(data["metals"]), len(data["bist"])), (1, 1, 1))

    def test_english_bist_export_with_partial_prices_is_english_and_imports(self):
        from features.bist.excel_io import read_portfolio_excel, write_portfolio_excel

        holdings = [
            {"symbol": "ASELS", "company": "Aselsan", "quantity": "10", "average_cost": "75.5", "sector": "", "notes": ""},
            {"symbol": "THYAO", "company": "THY", "quantity": "5", "average_cost": "200", "sector": "", "notes": ""},
        ]
        write_portfolio_excel(self.dir / "b.xlsx", holdings, prices={"ASELS": Decimal("80")})
        self.assert_english(self.dir / "b.xlsx")
        self.assertEqual(len(read_portfolio_excel(self.dir / "b.xlsx")), 2)

    def test_english_combined_export_is_english_and_imports(self):
        from features.combined_import import read_combined_portfolio_excel
        from features.currencies import localized_currency_assets
        from features.currencies import metal_assets
        from features.investment_excel import write_combined_portfolio_excel

        write_combined_portfolio_excel(
            self.dir / "all.xlsx",
            currency_holdings=[{"asset_code": "SEK", "display_name": "x", "unit": "SEK", "quantity": "5", "average_cost_try": "3"}],
            currency_prices={"SEK": Decimal("4")},
            metal_holdings=[], metal_prices={},
            bist_holdings=[{"symbol": "ASELS", "company": "A", "quantity": "1", "average_cost": "10", "sector": "", "notes": ""},
                           {"symbol": "THYAO", "company": "T", "quantity": "1", "average_cost": "10", "sector": "", "notes": ""}],
            bist_prices={"ASELS": Decimal("12")},
            try_per_usd=Decimal("35"), try_per_eur=Decimal("38"),
        )
        self.assert_english(self.dir / "all.xlsx")
        data = read_combined_portfolio_excel(
            self.dir / "all.xlsx", currency_assets=localized_currency_assets(), metal_assets=metal_assets()
        )
        self.assertEqual([r["asset_code"] for r in data["currency"]], ["SEK"])
        self.assertEqual(len(data["bist"]), 2)

    def test_holdings_saved_in_turkish_are_shown_with_english_names(self):
        from features.investment_store import InvestmentStore

        store = InvestmentStore(self.dir / "holdings.db")
        store.add_purchase("currency", "SEK", "10", "3", display_name="İsveç Kronu", unit="SEK")
        store.add_purchase("metals", "XAU", "1", "100", display_name="Altın", unit="gr")
        self.assertEqual(store.list_holdings("currency")[0]["display_name"], "Swedish Krona")
        self.assertEqual(store.list_holdings("metals")[0]["display_name"], "Gold")
        set_language("tr")
        self.assertEqual(store.list_holdings("currency")[0]["display_name"], "İsveç Kronu")

    def test_market_status_and_validation_messages_are_english(self):
        from core.market_refresh import collect_market_snapshot
        from features.bist.utils import normalize_symbol

        now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)
        cache = self.dir / "market.json"
        online = lambda: {"USD": 35.0, "EUR": 38.0, "TRY": 1.0, "status": "Online"}  # noqa: E731
        offline = lambda: {"USD": None, "EUR": None, "TRY": 1.0, "status": "Offline"}  # noqa: E731
        collect_market_snapshot(cache, rates_fn=online, metals_fn=lambda: (2650.0, 31.0), now=now)
        later = collect_market_snapshot(cache, rates_fn=offline, metals_fn=lambda: (None, None), now=now)
        self.assertIn("cache", later["status"])
        self.assertIn("gold/silver from cache", later["status"])
        self.assertIsNone(TURKISH_LETTERS.search(later["status"]))
        with self.assertRaises(ValueError) as caught:
            normalize_symbol("!")
        self.assertIsNone(TURKISH_LETTERS.search(str(caught.exception)))


class ErrorMessageLanguageTests(LanguageSwitchMixin, unittest.TestCase):
    """Validation messages shown to the user must follow the language, defaults included."""

    def test_parser_messages_are_english(self):
        from features.bist.utils import parse_localized_decimal as bist_parse
        from features.investment_store import parse_localized_decimal as store_parse

        for parse in (bist_parse, store_parse):
            for value, label in ((None, None), ("abc", None), ("", "Miktar")):
                with self.assertRaises(ValueError) as caught:
                    parse(value, field_name=tr(label)) if label else parse(value)
                message = str(caught.exception)
                self.assertIsNone(TURKISH_LETTERS.search(message), message)
                self.assertNotIn("Değer", message)
        with self.assertRaises(ValueError) as caught:
            store_parse(None)
        self.assertEqual(str(caught.exception), "Value cannot be empty.")

    def test_quantity_labels_in_store_errors_are_english(self):
        import tempfile
        from pathlib import Path
        from features.bist.database import BistDatabase
        from features.investment_store import InvestmentStore

        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ValueError) as caught:
                InvestmentStore(Path(tmp) / "a.db").add_purchase("currency", "USD", "", "3", display_name="x", unit="USD")
            self.assertIn("Quantity", str(caught.exception))
            with self.assertRaises(ValueError) as caught:
                BistDatabase(Path(tmp) / "b.db").upsert_holding("ASELS", "", "3")
            self.assertIn("Quantity", str(caught.exception))


class CurrencyNameTests(unittest.TestCase):
    def test_names_follow_the_language(self):
        from features.currencies import currency_display_name

        self.assertEqual(currency_display_name("RON", "tr"), "Romen Leyi")
        self.assertEqual(currency_display_name("RON", "en"), "Romanian Leu")
        self.assertEqual(currency_display_name("XXX", "en"), "XXX")


class NoImportTimeTranslationTests(unittest.TestCase):
    """tr() reads the active language, which is only known after startup.

    A tr() call that runs while a module is imported would freeze the language at
    its default, so every call must sit inside a function (use tr_noop for constants).
    """

    def test_tr_is_only_called_inside_function_bodies(self):
        import ast

        root = Path(__file__).resolve().parents[1]
        offenders = []
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root)
            if {"tests", "tools", "docs"} & set(relative.parts) or relative.name in {"app.py", "translations_en.py"}:
                continue
            tree = ast.parse(path.read_text(encoding="utf-8"))
            for node in ast.walk(tree):
                for child in ast.iter_child_nodes(node):
                    child._parent = node
            for node in ast.walk(tree):
                if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id == "tr":
                    cursor, previous, inside = node, None, False
                    while cursor is not None:
                        previous, cursor = cursor, getattr(cursor, "_parent", None)
                        if isinstance(cursor, (ast.FunctionDef, ast.AsyncFunctionDef)):
                            # Only the body runs at call time; defaults and decorators run at import.
                            inside = previous in cursor.body
                            break
                        if isinstance(cursor, ast.Lambda):
                            inside = previous is cursor.body
                            break
                    if not inside:
                        offenders.append(f"{relative}:{node.lineno}")
        self.assertEqual(offenders, [])


class FormatCallTests(unittest.TestCase):
    def test_format_calls_supply_exactly_the_placeholders_of_their_text(self):
        import ast

        root = Path(__file__).resolve().parents[1]
        problems = []
        checked = 0
        for path in sorted(root.rglob("*.py")):
            relative = path.relative_to(root)
            if {"tests", "tools", "docs"} & set(relative.parts) or relative.name == "translations_en.py":
                continue
            for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
                if (
                    isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and node.func.attr == "format" and isinstance(node.func.value, ast.Call)
                    and isinstance(node.func.value.func, ast.Name) and node.func.value.func.id == "tr"
                    and node.func.value.args and isinstance(node.func.value.args[0], ast.Constant)
                ):
                    checked += 1
                    wanted = {int(n) for n in PLACEHOLDER.findall(node.func.value.args[0].value)}
                    supplied = set(range(len(node.args)))
                    if wanted != supplied or node.keywords:
                        problems.append(f"{relative}:{node.lineno} wants {sorted(wanted)} gets {sorted(supplied)}")
        self.assertGreater(checked, 40)
        self.assertEqual(problems, [])


if __name__ == "__main__":
    unittest.main()
