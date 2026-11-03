import tempfile
import unittest
from pathlib import Path
from decimal import Decimal

from features.bist.database import BistDatabase
from features.bist.utils import parse_localized_decimal, normalize_symbol, format_tl
from features.bist.excel_io import read_portfolio_excel, write_portfolio_excel


class BistCoreTests(unittest.TestCase):
    def test_turkish_number_parsing(self):
        self.assertEqual(parse_localized_decimal("1.234,56"), Decimal("1234.56"))
        self.assertEqual(parse_localized_decimal("74,50"), Decimal("74.50"))
        self.assertEqual(parse_localized_decimal("1,234.56"), Decimal("1234.56"))

    def test_symbol_normalization(self):
        self.assertEqual(normalize_symbol(" bist:asels "), "ASELS")
        self.assertEqual(normalize_symbol("thyao.is"), "THYAO")

    def test_database_crud_and_summary(self):
        with tempfile.TemporaryDirectory() as temp:
            db = BistDatabase(Path(temp) / "test.db")
            db.upsert_holding("ASELS", "100", "75,50", company="Aselsan")
            db.upsert_holding("THYAO", "20", "250")
            self.assertEqual(len(db.list_holdings()), 2)
            self.assertEqual(db.summary()["holding_count"], 2)
            self.assertEqual(db.summary()["total_cost"], Decimal("12550.0"))
            db.upsert_holding("ASELS", "120", "76")
            self.assertEqual(db.get_holding("ASELS")["quantity"], "120")
            self.assertTrue(db.delete_holding("THYAO"))
            self.assertEqual(len(db.list_holdings()), 1)

    def test_excel_export_import_round_trip(self):
        with tempfile.TemporaryDirectory() as temp:
            db = BistDatabase(Path(temp) / "original.db")
            db.upsert_holding("ASELS", "100", "75,50", company="Aselsan", sector="Savunma")
            db.upsert_holding("THYAO", "20", "250", company="Türk Hava Yolları", sector="Ulaştırma")
            xlsx = Path(temp) / "portfolio.xlsx"
            write_portfolio_excel(xlsx, db.list_holdings())
            imported_rows = read_portfolio_excel(xlsx)
            clone = BistDatabase(Path(temp) / "clone.db")
            imported, errors = clone.import_rows(imported_rows)
            self.assertEqual(imported, 2)
            self.assertEqual(errors, [])
            self.assertEqual(len(clone.list_holdings()), 2)
            self.assertEqual(clone.get_holding("ASELS")["company"], "Aselsan")

    def test_validation(self):
        with tempfile.TemporaryDirectory() as temp:
            db = BistDatabase(Path(temp) / "test.db")
            with self.assertRaises(ValueError):
                db.upsert_holding("ASELS", "0", "10")
            with self.assertRaises(ValueError):
                db.upsert_holding("bad symbol", "1", "10")

    def test_format(self):
        self.assertEqual(format_tl(Decimal("1234.5")), "1.234,50")


if __name__ == "__main__":
    unittest.main()
