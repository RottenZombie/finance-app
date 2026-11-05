from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import settings
from core.app_paths import app_data_directory, data_directory, settings_file_path


class AppDataPathTests(unittest.TestCase):
    def test_settings_and_database_share_app_data_root(self):
        with tempfile.TemporaryDirectory() as temp:
            with patch.dict(os.environ, {"XDG_DATA_HOME": temp}, clear=False):
                root = app_data_directory()
                self.assertEqual(settings_file_path(), root / "config.json")
                self.assertEqual(data_directory(), root / "data")

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
