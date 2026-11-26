"""Backup/restore dialog flows. All Qt widgets are replaced, so no window opens."""
from __future__ import annotations

import json
import tempfile
import unittest
from decimal import Decimal
from pathlib import Path
from unittest.mock import MagicMock, patch

from core import backup
from core.i18n import set_language
from features import backup_data
from features.bist.database import BistDatabase
from features.investment_store import InvestmentStore

try:
    from features import backup_dialogs as dlg
    PYSIDE_AVAILABLE = True
except ImportError:
    PYSIDE_AVAILABLE = False

SETTINGS = {"precision": 2, "currency_codes": ["USD", "EUR", "HUF"], "calculator_extra_currency": "HUF",
            "profile_names": {"profile1": "Ana", "profile2": "Eş"}, "theme": "Dark"}


def seed(root: Path, stock="ASELS"):
    data = backup_data.profile_data_dir("profile1", root)
    data.mkdir(parents=True, exist_ok=True)
    store = InvestmentStore(data / backup_data.INVESTMENT_DB)
    store.set_holding("currency", "USD", Decimal("100"), Decimal("30.5"), display_name="x", unit="USD")
    BistDatabase(data / backup_data.BIST_DB).upsert_holding(stock, Decimal("10"), Decimal("75.5"), "Aselsan", "", "")


def stocks(root: Path) -> set[str]:
    path = backup_data.profile_data_dir("profile1", root) / backup_data.BIST_DB
    return {r["symbol"] for r in BistDatabase(path).list_holdings()} if path.exists() else set()


def box_choosing(index: int | None):
    """A fake QMessageBox whose user clicks the index-th button added (None = closes it)."""
    box = MagicMock()
    buttons = [MagicMock(name=f"button{i}") for i in range(3)]
    box.addButton.side_effect = buttons
    box.clickedButton.return_value = None if index is None else buttons[index]
    return box


@unittest.skipUnless(PYSIDE_AVAILABLE, "PySide6 is not installed in this environment")
class DialogFlowTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name) / "appdata"
        self.files = Path(self._tmp.name) / "files"
        self.files.mkdir()
        self.addCleanup(set_language, "tr")
        for target in ("features.backup_data.app_data_directory",):
            patcher = patch(target, lambda: self.root)
            patcher.start()
            self.addCleanup(patcher.stop)
        self.mb = patch.object(dlg, "QMessageBox").start()
        self.addCleanup(patch.stopall)
        self.fd = patch.object(dlg, "QFileDialog").start()
        self.inp = patch.object(dlg, "QInputDialog").start()
        seed(self.root)

    def choose(self, index):
        self.mb.return_value = box_choosing(index)

    # ------------------------------------------------------------------ backup
    def test_unencrypted_backup(self):
        self.choose(1)
        target = self.files / "plain"                                  # no extension typed: it is added
        self.fd.getSaveFileName.return_value = (str(target), "")
        self.assertTrue(dlg.run_backup(None, SETTINGS, "9.9"))
        data = (self.files / "plain.ftbackup").read_bytes()
        self.assertFalse(backup.inspect_backup(data).encrypted)
        _info, payload = backup.read_backup(data)
        self.assertEqual(payload["profiles"][0]["stocks"][0]["symbol"], "ASELS")
        self.assertNotIn("theme", payload["preferences"])
        self.assertIn("şifresiz", self.mb.information.call_args.args[2])
        self.assertEqual([p.name for p in self.files.iterdir()], ["plain.ftbackup"])     # no temp files left

    def test_encrypted_backup_asks_for_the_password_twice_and_checks_it(self):
        self.choose(0)
        self.inp.getText.side_effect = [
            ("short", True),                  # too short -> warning, asked again
            ("Gizli-Parola-1", True), ("başka-parola-2", True),    # confirmation differs -> warning, again
            ("Gizli-Parola-1", True), ("Gizli-Parola-1", True),
        ]
        self.fd.getSaveFileName.return_value = (str(self.files / "enc.ftbackup"), "")
        self.assertTrue(dlg.run_backup(None, SETTINGS, "9.9"))
        data = (self.files / "enc.ftbackup").read_bytes()
        self.assertTrue(backup.inspect_backup(data).encrypted)
        self.assertNotIn(b"ASELS", data)
        self.assertEqual(backup.read_backup(data, "Gizli-Parola-1")[1]["profiles"][0]["stocks"][0]["symbol"], "ASELS")
        warnings = [call.args[2] for call in self.mb.warning.call_args_list]
        self.assertEqual(len(warnings), 2)
        self.assertIn("8", warnings[0])
        self.assertIn("aynı değil", warnings[1])
        self.assertIn("kurtarılamaz", self.mb.information.call_args.args[2])       # forgotten password warning

    def test_the_encryption_question_warns_about_a_forgotten_password(self):
        self.choose(None)
        dlg.run_backup(None, SETTINGS, "9.9")
        box = self.mb.return_value
        self.assertIn("kurtarılamaz", box.setInformativeText.call_args.args[0])
        self.assertEqual([c.args[0] for c in box.addButton.call_args_list], ["Şifreli Yedek", "Şifresiz Yedek", "İptal"])

    def test_every_cancel_point_writes_nothing(self):
        self.choose(None)                                               # closes the encryption question
        self.assertFalse(dlg.run_backup(None, SETTINGS, "9.9"))
        self.fd.getSaveFileName.assert_not_called()

        self.choose(0)
        self.inp.getText.side_effect = [("", False)]                    # cancels the password
        self.assertFalse(dlg.run_backup(None, SETTINGS, "9.9"))

        self.choose(1)
        self.fd.getSaveFileName.return_value = ("", "")                 # cancels the file dialog
        self.assertFalse(dlg.run_backup(None, SETTINGS, "9.9"))
        self.assertEqual(list(self.files.iterdir()), [])

    def test_unwritable_target_is_reported(self):
        self.choose(1)
        self.fd.getSaveFileName.return_value = (str(self.files / "missing-folder" / "x.ftbackup"), "")
        self.assertFalse(dlg.run_backup(None, SETTINGS, "9.9"))
        self.assertTrue(self.mb.warning.called)

    # ----------------------------------------------------------------- restore
    def make_file(self, name="b.ftbackup", password=None, stock="ASELS"):
        source = Path(self._tmp.name) / f"source-{name}"
        seed(source, stock)
        data, _ = backup_data.build_backup_bytes(SETTINGS, password=password, app_version="1", data_root=source)
        path = self.files / name
        path.write_bytes(data)
        self.fd.getOpenFileName.return_value = (str(path), "")
        return path

    def test_merge_keeps_local_records(self):
        seed(self.root, stock="THYAO")
        self.make_file()
        self.choose(0)                                                  # "Merge"
        report = dlg.run_restore(None, SETTINGS, "9.9")
        self.assertEqual(report.mode, backup_data.MERGE)
        self.assertEqual(stocks(self.root), {"ASELS", "THYAO"})
        self.assertTrue(report.safety_backup.is_file())
        self.assertIn("geri yüklendi", self.mb.information.call_args.args[2])

    def test_replace_needs_a_second_confirmation(self):
        seed(self.root, stock="THYAO")
        self.make_file()
        self.choose(1)                                                  # "Overwrite"
        with patch.object(dlg, "ask_warning_question", return_value=self.mb.StandardButton.No) as ask:
            self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        ask.assert_called_once()
        self.assertEqual(stocks(self.root), {"ASELS", "THYAO"})         # declined: untouched
        self.assertFalse(backup_data.backups_dir(self.root).exists())

        self.choose(1)
        with patch.object(dlg, "ask_warning_question", return_value=self.mb.StandardButton.Yes):
            report = dlg.run_restore(None, SETTINGS, "9.9")
        self.assertEqual(report.mode, backup_data.REPLACE)
        self.assertEqual(stocks(self.root), {"ASELS"})                  # THYAO (not in the file) is gone

    def test_cancelling_the_mode_question_changes_nothing(self):
        self.make_file()
        self.choose(2)
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.choose(None)
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.assertFalse(backup_data.backups_dir(self.root).exists())

    def test_encrypted_restore_retries_a_wrong_password(self):
        self.make_file("enc.ftbackup", password="Gizli-Parola-1", stock="KCHOL")
        self.choose(0)
        self.inp.getText.side_effect = [("yanlis-parola", True), ("Gizli-Parola-1", True)]
        report = dlg.run_restore(None, SETTINGS, "9.9")
        self.assertIsNotNone(report)
        self.assertIn("KCHOL", stocks(self.root))
        self.assertEqual(self.mb.warning.call_count, 1)                  # one "wrong password" message

    def test_three_wrong_passwords_and_cancel_change_nothing(self):
        self.make_file("enc.ftbackup", password="Gizli-Parola-1", stock="KCHOL")
        self.inp.getText.side_effect = [("a", True), ("b", True), ("c", True)]
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.assertEqual(self.inp.getText.call_count, dlg.PASSWORD_ATTEMPTS)
        self.inp.getText.side_effect = [("", False)]
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.assertNotIn("KCHOL", stocks(self.root))

    def test_foreign_unreadable_and_newer_files_are_explained(self):
        for name, content, expected in (
            ("a.txt", b"hello", "yedeği değil"),
            ("b.ftbackup", json.dumps({"format": "FinanceTerminal.Backup", "format_version": 7}).encode(), "daha yeni"),
        ):
            path = self.files / name
            path.write_bytes(content)
            self.fd.getOpenFileName.return_value = (str(path), "")
            self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
            self.assertIn(expected, self.mb.warning.call_args.args[2])
        self.fd.getOpenFileName.return_value = (str(self.files / "does-not-exist"), "")
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.fd.getOpenFileName.return_value = ("", "")
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))

    def test_skipped_rows_are_listed_and_capped(self):
        rows = [{"code": "XXX", "quantity": "1", "average_cost_try": "1"} for _ in range(12)]
        payload = {"preferences": {}, "profiles": [{"id": "profile1", "name": "A", "currency": rows,
                   "stocks": [{"symbol": "KCHOL", "quantity": "1", "average_cost": "1"}]}]}
        path = self.files / "bad-rows.ftbackup"
        path.write_bytes(backup.create_backup(payload, app_version="1"))
        self.fd.getOpenFileName.return_value = (str(path), "")
        self.choose(0)
        report = dlg.run_restore(None, SETTINGS, "9.9")
        self.assertEqual(report.total_imported, 1)
        mode_text = self.mb.return_value.setText.call_args.args[0]
        self.assertIn("12 satır okunamadığı için atlanacak", mode_text)
        shown = self.mb.information.call_args.args[2]
        self.assertIn("... ve 4 satır daha.", shown)
        self.assertEqual(shown.count("desteklenmeyen kod"), dlg.SHOWN_SKIPPED)

    def test_a_file_without_profiles_is_not_restored(self):
        path = self.files / "empty.ftbackup"
        path.write_bytes(backup.create_backup({"profiles": []}, app_version="1"))
        self.fd.getOpenFileName.return_value = (str(path), "")
        self.assertIsNone(dlg.run_restore(None, SETTINGS, "9.9"))
        self.assertTrue(self.mb.information.called)

    def test_english_dialog_texts(self):
        set_language("en")
        self.choose(None)
        dlg.run_backup(None, SETTINGS, "9.9")
        box = self.mb.return_value
        self.assertEqual([c.args[0] for c in box.addButton.call_args_list], ["Encrypted Backup", "Unencrypted Backup", "Cancel"])
        self.assertIn("cannot be recovered", box.setInformativeText.call_args.args[0])


if __name__ == "__main__":
    unittest.main()
