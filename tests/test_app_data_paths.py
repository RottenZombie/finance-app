from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings
from core.app_paths import (
    app_data_directory, data_directory, settings_file_path,
    set_active_profile, profile_directory, migrate_legacy_data_to_profile1,
)


class AppDataPathTests(unittest.TestCase):
    def test_settings_and_database_share_app_data_root(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": temp, "APPDATA": temp}, clear=False):
                set_active_profile("profile1")
                root = app_data_directory()
                self.assertEqual(settings_file_path(), root / "config.json")
                self.assertEqual(data_directory(), root / "profiles" / "profile1" / "data")
                set_active_profile("profile2")
                self.assertEqual(data_directory(), root / "profiles" / "profile2" / "data")
                set_active_profile("profile3")
                self.assertEqual(data_directory(), root / "profiles" / "profile3" / "data")
                with self.assertRaises(ValueError):
                    set_active_profile("profile4")
                set_active_profile("profile1")



    def test_profile_stores_use_independent_database_paths(self):
        from features.investment_store import InvestmentStore
        from features.bist.database import BistDatabase

        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": temp, "APPDATA": temp}, clear=False):
                set_active_profile("profile1")
                first_investment = InvestmentStore().db_path
                first_bist = BistDatabase().db_path
                set_active_profile("profile2")
                second_investment = InvestmentStore().db_path
                second_bist = BistDatabase().db_path
                set_active_profile("profile3")
                third_investment = InvestmentStore().db_path
                third_bist = BistDatabase().db_path
                self.assertEqual(len({first_investment, second_investment, third_investment}), 3)
                self.assertEqual(len({first_bist, second_bist, third_bist}), 3)
                self.assertIn("profile1", str(first_investment))
                self.assertIn("profile2", str(second_investment))
                self.assertIn("profile3", str(third_investment))
                set_active_profile("profile1")

    def test_legacy_data_is_copied_to_profile1_and_original_is_kept(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp) / "FinanceTerminal"
            legacy = root / "data"
            legacy.mkdir(parents=True)
            (legacy / "investment_holdings.db").write_bytes(b"legacy-db")
            with patch("core.app_paths.app_data_directory", return_value=root):
                self.assertTrue(migrate_legacy_data_to_profile1())
                target = root / "profiles" / "profile1" / "data" / "investment_holdings.db"
                self.assertEqual(target.read_bytes(), b"legacy-db")
                self.assertEqual((legacy / "investment_holdings.db").read_bytes(), b"legacy-db")
                self.assertFalse(migrate_legacy_data_to_profile1())

    def test_legacy_config_is_migrated_and_removed_from_old_location(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "appdata" / "FinanceTerminal" / "config.json"
            legacy = root / "old_install" / "config.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({"theme": "Blue", "precision": 4}), encoding="utf-8")
            with patch("settings.settings_file_path", return_value=target), \
                 patch("settings._legacy_config_candidates", return_value=[legacy]), \
                 patch.object(settings.sys, "frozen", True, create=True):
                loaded = settings.load()
            self.assertEqual(loaded["theme"], "Blue")
            self.assertEqual(loaded["precision"], 4)
            self.assertTrue(target.is_file())
            self.assertFalse(legacy.exists())

    def test_saving_settings_creates_config_inside_app_data(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "FinanceTerminal" / "config.json"
            with patch("settings.settings_file_path", return_value=target), \
                 patch("settings._legacy_config_candidates", return_value=[]):
                settings.save({"theme": "Dark", "auto_update_check": True})
                loaded = settings.load()
            self.assertEqual(loaded["theme"], "Dark")
            self.assertTrue(loaded["auto_update_check"])

    def test_source_mode_keeps_project_config_file_after_migration_copy(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            target = root / "appdata" / "FinanceTerminal" / "config.json"
            legacy = root / "project" / "config.json"
            legacy.parent.mkdir(parents=True)
            legacy.write_text(json.dumps({"theme": "Dark"}), encoding="utf-8")
            with patch("settings.settings_file_path", return_value=target), \
                 patch("settings._legacy_config_candidates", return_value=[legacy]), \
                 patch.object(settings.sys, "frozen", False, create=True):
                loaded = settings.load()
            self.assertEqual(loaded["theme"], "Dark")
            self.assertTrue(target.is_file())
            self.assertTrue(legacy.is_file())


if __name__ == "__main__":
    unittest.main()
