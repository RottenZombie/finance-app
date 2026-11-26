from __future__ import annotations

import base64
import copy
import json
import tempfile
import time
import unicodedata
import unittest
from decimal import Decimal
from pathlib import Path

from core import backup
from core.backup import (
    BackupError, CorruptBackupError, NewerBackupError, NotABackupError,
    PasswordRequiredError, WrongPasswordError,
)
from core.i18n import set_language
from features import backup_data
from features.bist.database import BistDatabase
from features.investment_store import InvestmentStore

ROOT = Path(__file__).resolve().parents[1]
FAST = 100_000                       # PBKDF2 iterations: the minimum accepted, keeps tests quick
PASSWORD = "Şifre-123-ığüİ"
PAYLOAD = {
    "preferences": {"precision": 3, "currency_codes": ["USD", "SEK"], "calculator_extra_currency": "SEK"},
    "profiles": [{
        "id": "profile1", "name": "Ana",
        "currency": [{"code": "USD", "quantity": "100.5", "average_cost_try": "30.25"}],
        "metals": [{"code": "XAU", "quantity": "10", "average_cost_try": "2800"}],
        "stocks": [{"symbol": "ASELS", "company": "Aselsan", "quantity": "10", "average_cost": "75.50", "sector": "S", "notes": "n"}],
    }],
}


def make(password=None, payload=PAYLOAD, **kwargs):
    kwargs.setdefault("iterations", FAST)
    return backup.create_backup(payload, password=password, app_version="9.9.9", **kwargs)


class EnvelopeTests(unittest.TestCase):
    def test_plain_round_trip_and_header(self):
        data = make()
        info = backup.inspect_backup(data)
        self.assertFalse(info.encrypted)
        self.assertEqual((info.format_version, info.app_version, info.platform), (1, "9.9.9", "windows"))
        self.assertRegex(info.created_at, r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$")
        header, payload = backup.read_backup(data)
        self.assertEqual(payload, PAYLOAD)
        self.assertEqual(header, info)

    def test_encrypted_round_trip_needs_the_right_password(self):
        data = make(PASSWORD)
        self.assertTrue(backup.inspect_backup(data).encrypted)       # header readable without a password
        self.assertNotIn(b"ASELS", data)                             # payload really is hidden
        self.assertEqual(backup.read_backup(data, PASSWORD)[1], PAYLOAD)
        with self.assertRaises(PasswordRequiredError):
            backup.read_backup(data)
        with self.assertRaises(PasswordRequiredError):
            backup.read_backup(data, "")
        with self.assertRaises(WrongPasswordError):
            backup.read_backup(data, PASSWORD + "x")

    def test_password_is_unicode_normalised_for_every_keyboard_and_platform(self):
        data = make(unicodedata.normalize("NFC", PASSWORD))
        decomposed = unicodedata.normalize("NFD", PASSWORD)
        self.assertNotEqual(decomposed, PASSWORD)
        self.assertEqual(backup.read_backup(data, decomposed)[1], PAYLOAD)

    def test_every_encrypted_backup_uses_fresh_salt_and_nonce(self):
        first, second = json.loads(make(PASSWORD)), json.loads(make(PASSWORD))
        self.assertNotEqual(first["kdf"]["salt"], second["kdf"]["salt"])
        self.assertNotEqual(first["cipher"]["nonce"], second["cipher"]["nonce"])
        self.assertNotEqual(first["payload"], second["payload"])

    def test_short_passwords_are_refused(self):
        with self.assertRaises(BackupError):
            make("1234567")
        self.assertIsNone(backup.password_problem("12345678"))
        self.assertIn("8", backup.password_problem("x"))

    def test_tampering_is_detected(self):
        plain = json.loads(make())
        plain["payload"] = plain["payload"].replace("ASELS", "THYAO")
        with self.assertRaises(CorruptBackupError):
            backup.read_backup(json.dumps(plain).encode())

        enc = json.loads(make(PASSWORD))
        raw = bytearray(base64.b64decode(enc["payload"]))
        raw[3] ^= 0x01
        enc["payload"] = base64.b64encode(bytes(raw)).decode()
        with self.assertRaises(WrongPasswordError):
            backup.read_backup(json.dumps(enc).encode(), PASSWORD)

    def test_ciphertext_is_bound_to_format_and_version(self):
        enc = json.loads(make(PASSWORD))
        enc["format_version"] = 1
        # Same bytes read with a different associated-data version must not decrypt.
        original = backup._aad
        try:
            backup._aad = lambda version: b"other"
            with self.assertRaises(WrongPasswordError):
                backup.read_backup(json.dumps(enc).encode(), PASSWORD)
        finally:
            backup._aad = original

    def test_unreadable_or_foreign_files(self):
        for junk in (b"", b"\x00\x01\x02", b"not json", b"[]", b'{"format": "Other"}', json.dumps({"a": 1}).encode()):
            with self.assertRaises(NotABackupError):
                backup.inspect_backup(junk)
        with self.assertRaises(NotABackupError):
            backup.inspect_backup(b" " * (backup.MAX_FILE_BYTES + 1))

    def test_newer_and_invalid_format_versions(self):
        envelope = json.loads(make())
        envelope["format_version"] = 2
        with self.assertRaises(NewerBackupError):
            backup.inspect_backup(json.dumps(envelope).encode())
        for bad in (0, "1", None, True, 1.5):
            envelope["format_version"] = bad
            with self.assertRaises(CorruptBackupError):
                backup.inspect_backup(json.dumps(envelope).encode())

    def test_damaged_encryption_parameters_are_rejected(self):
        for mutate in (
            lambda e: e["kdf"].update(iterations=backup.MAX_ITERATIONS + 1),   # CPU-exhaustion attempt
            lambda e: e["kdf"].update(iterations=1),
            lambda e: e["kdf"].update(name="scrypt"),
            lambda e: e["cipher"].update(name="AES-128-CBC"),
            lambda e: e["cipher"].update(nonce="AAAA"),
            lambda e: e["kdf"].update(salt="!!!not base64!!!"),
            lambda e: e.update(payload="AAAA"),
            lambda e: e.update(payload=12),
        ):
            envelope = json.loads(make(PASSWORD))
            mutate(envelope)
            with self.assertRaises(CorruptBackupError):
                backup.read_backup(json.dumps(envelope).encode(), PASSWORD)

    def test_utf8_bom_from_other_tools_is_tolerated(self):
        self.assertEqual(backup.read_backup(b"\xef\xbb\xbf" + make())[1], PAYLOAD)

    def test_messages_follow_the_language(self):
        set_language("en")
        self.addCleanup(set_language, "tr")
        with self.assertRaises(NotABackupError) as caught:
            backup.inspect_backup(b"x")
        self.assertEqual(str(caught.exception), "This file is not a FinanceTerminal backup.")
        with self.assertRaises(WrongPasswordError) as caught:
            backup.read_backup(make(PASSWORD), "wrong-password")
        self.assertEqual(str(caught.exception), "The password is wrong or the file is damaged.")


class GoldenVectorTests(unittest.TestCase):
    """Published vectors: if these change, the file format changed (bump FORMAT_VERSION)."""

    def test_vectors_match_what_the_code_generates(self):
        import importlib.util
        spec = importlib.util.spec_from_file_location("make_vectors", ROOT / "tools" / "make_backup_vectors.py")
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        for name, data in module.generate().items():
            self.assertEqual((ROOT / "docs" / "test-vectors" / name).read_bytes(), data, name)

    def test_the_specification_document_states_the_same_test_vector_parameters(self):
        """Keeps docs/DATA_FORMAT.md from drifting away from the code."""
        text = (ROOT / "docs" / "DATA_FORMAT.md").read_text(encoding="utf-8")
        key = backup.derive_key("Şifre-123-ığüİ", bytes(range(16)), backup.PBKDF2_ITERATIONS).hex()
        self.assertIn(key, text)
        self.assertIn(bytes(range(16)).hex(), text)
        self.assertIn(bytes(range(12)).hex(), text)
        self.assertIn(f"{backup.PBKDF2_ITERATIONS:,}".replace(",", " "), text)
        self.assertIn(f"FinanceTerminal.Backup/{backup.FORMAT_VERSION}", text)
        for field in backup.SHARED_PREFERENCE_KEYS:
            self.assertIn(f"`{field}`", text)

    def test_vectors_decode_to_the_documented_payload(self):
        folder = ROOT / "docs" / "test-vectors"
        _info, plain_payload = backup.read_backup((folder / "plain.ftbackup").read_bytes())
        _info, enc_payload = backup.read_backup((folder / "encrypted.ftbackup").read_bytes(), "Şifre-123-ığüİ")
        self.assertEqual(plain_payload, enc_payload)
        self.assertEqual(plain_payload["profiles"][0]["stocks"][0]["symbol"], "ASELS")


class DecimalTests(unittest.TestCase):
    def test_canonical_decimal_is_locale_independent(self):
        self.assertEqual(backup.canonical_decimal("1.250"), Decimal("1.250"))       # NOT one thousand two hundred fifty
        self.assertEqual(backup.canonical_decimal(" 75.50 "), Decimal("75.50"))
        self.assertEqual(backup.canonical_decimal(7), Decimal("7"))
        for bad in ("1,5", "1e3", "1.2.3", "", "abc", "NaN", "Infinity", None, True, [], "1 000"):
            self.assertIsNone(backup.canonical_decimal(bad), bad)

    def test_plain_never_uses_scientific_notation(self):
        self.assertEqual(backup.plain(Decimal("1E+3")), "1000")
        self.assertEqual(backup.plain(Decimal("0.0000001")), "0.0000001")
        self.assertEqual(backup.plain(Decimal("75.50")), "75.50")


class ValidationTests(unittest.TestCase):
    def test_good_payload(self):
        clean = backup.validate_payload(PAYLOAD)
        self.assertEqual(clean.skipped, [])
        self.assertEqual([p.id for p in clean.profiles], ["profile1"])
        self.assertEqual(clean.profiles[0].currency[0]["quantity"], Decimal("100.5"))
        self.assertEqual(clean.profiles[0].stocks[0]["symbol"], "ASELS")
        self.assertEqual(clean.preferences, {"precision": 3, "currency_codes": ["USD", "SEK"], "calculator_extra_currency": "SEK"})

    def test_bad_rows_are_skipped_and_reported_not_fatal(self):
        payload = copy.deepcopy(PAYLOAD)
        payload["profiles"][0]["currency"] += [
            {"code": "XXX", "quantity": "1", "average_cost_try": "1"},     # unsupported currency (e.g. a newer phone app)
            {"code": "EUR", "quantity": "0", "average_cost_try": "1"},     # zero quantity
            {"code": "GBP", "quantity": "5", "average_cost_try": "-1"},    # negative cost
            {"code": "SEK", "quantity": "1,5", "average_cost_try": "1"},   # locale separator
            {"code": "USD", "quantity": "1", "average_cost_try": "1"},     # duplicate of the first row
            "not a row", 5,
        ]
        payload["profiles"][0]["stocks"].append({"symbol": "!!", "quantity": "1", "average_cost": "1"})
        payload["profiles"][0]["metals"] = [{"code": "XPT", "quantity": "1", "average_cost_try": "1"}]
        clean = backup.validate_payload(payload)
        self.assertEqual(len(clean.skipped), 9)
        self.assertEqual([r["code"] for r in clean.profiles[0].currency], ["USD"])
        self.assertEqual(clean.profiles[0].metals, [])
        self.assertTrue(all("profile1" in message for message in clean.skipped))

    def test_unknown_profiles_duplicates_and_extra_fields_are_ignored(self):
        payload = copy.deepcopy(PAYLOAD)
        payload["profiles"] += [{"id": "profile9"}, {"id": "PROFILE1", "name": "dup"}, "x", {"id": "profile2", "name": "x" * 500}]
        payload["future_field"] = {"anything": 1}
        payload["profiles"][0]["future_row_field"] = True
        clean = backup.validate_payload(payload)
        self.assertEqual([p.id for p in clean.profiles], ["profile1", "profile2"])
        self.assertEqual(len(clean.profiles[1].name), backup.MAX_NAME_LENGTH)

    def test_preferences_are_sanitised(self):
        clean = backup.validate_payload({"profiles": [], "preferences": {
            "precision": 99, "currency_codes": ["usd", "ZZZ", "sek"], "calculator_extra_currency": "USD", "theme": "Dark", "language": "en"}})
        self.assertEqual(clean.preferences, {"currency_codes": ["USD", "SEK"]})   # personal settings never come from a file
        self.assertEqual(backup.validate_payload({"profiles": [], "preferences": "x"}).preferences, {})

    def test_structure_errors_are_fatal(self):
        for bad in (None, [], "x", {}, {"profiles": "x"}):
            with self.assertRaises(CorruptBackupError):
                backup.validate_payload(bad)

    def test_too_many_rows_are_capped(self):
        rows = [{"code": "USD", "quantity": "1", "average_cost_try": "1"}] * (backup.MAX_ROWS_PER_SECTION + 5)
        clean = backup.validate_payload({"profiles": [{"id": "profile1", "currency": rows}]})
        self.assertTrue(any("10000" in m for m in clean.skipped))


class DataRoundTripTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.root = Path(self._tmp.name)
        self.settings = {
            "precision": 2, "currency_codes": ["USD", "EUR", "HUF"], "calculator_extra_currency": "HUF",
            "profile_names": {"profile1": "Ana", "profile2": "Eş"}, "theme": "Dark", "language": "tr",
        }

    def seed(self, root, profile="profile1", usd="100", stock="ASELS"):
        data = backup_data.profile_data_dir(profile, root)
        data.mkdir(parents=True, exist_ok=True)
        store = InvestmentStore(data / backup_data.INVESTMENT_DB)
        store.set_holding("currency", "USD", Decimal(usd), Decimal("30.5"), display_name="x", unit="USD")
        store.set_holding("metals", "XAU", Decimal("10"), Decimal("2800"), display_name="x", unit="gr")
        BistDatabase(data / backup_data.BIST_DB).upsert_holding(stock, Decimal("10"), Decimal("75.5"), "Aselsan", "Savunma", "not")

    def rows(self, root, profile="profile1"):
        data = backup_data.profile_data_dir(profile, root)
        store = InvestmentStore(data / backup_data.INVESTMENT_DB)
        return (
            sorted((r["asset_code"], r["quantity"], r["average_cost_try"]) for g in ("currency", "metals") for r in store.list_holdings(g)),
            sorted((r["symbol"], r["quantity"], r["average_cost"], r["company"], r["sector"], r["notes"]) for r in BistDatabase(data / backup_data.BIST_DB).list_holdings()),
        )

    def test_export_reads_every_profile_and_creates_nothing(self):
        self.seed(self.root)
        payload = backup_data.collect_payload(self.settings, self.root)
        self.assertEqual([p["id"] for p in payload["profiles"]], ["profile1", "profile2"])
        self.assertEqual(payload["profiles"][0]["currency"][0]["quantity"], "100")
        self.assertEqual(payload["profiles"][0]["stocks"][0]["average_cost"], "75.5")
        self.assertEqual(payload["profiles"][1]["currency"], [])
        self.assertFalse(backup_data.profile_data_dir("profile2", self.root).exists())       # exporting made no files
        self.assertNotIn("theme", payload["preferences"])                                      # personal settings stay home

    def test_full_round_trip_between_two_installations(self):
        self.seed(self.root, usd="100.123456789")
        self.settings["profile_names"]["profile3"] = "Üçüncü"
        data, counts = backup_data.build_backup_bytes(self.settings, password=PASSWORD, app_version="1", data_root=self.root)
        self.assertEqual((counts["currency"], counts["metals"], counts["stocks"]), (1, 1, 1))

        other = self.root / "phone"
        other_settings = {"precision": 4, "profile_names": {"profile1": "x", "profile2": "y"}, "theme": "Midnight"}
        _info, clean = backup_data.load_clean(data, PASSWORD)
        report = backup_data.apply_backup(clean, backup_data.REPLACE, other_settings, app_version="1", data_root=other)

        self.assertEqual(self.rows(other), self.rows(self.root))                  # identical records, exact decimals
        self.assertEqual(report.settings["profile_names"], {"profile1": "Ana", "profile2": "Eş", "profile3": "Üçüncü"})
        self.assertEqual(report.settings["precision"], 2)
        self.assertEqual(report.settings["currency_codes"], ["USD", "EUR", "HUF"])
        self.assertEqual(report.settings["theme"], "Midnight")                    # personal setting untouched
        # and back again: desktop -> phone -> desktop gives the same file content
        again, _ = backup_data.build_backup_bytes(report.settings, password=None, app_version="1", data_root=other)
        original = json.loads(json.loads(backup_data.build_backup_bytes(self.settings, password=None, app_version="1", data_root=self.root)[0])["payload"])
        returned = json.loads(json.loads(again)["payload"])
        for payload in (original, returned):
            for profile in payload["profiles"]:
                for rows in (profile["currency"], profile["metals"], profile["stocks"]):
                    for row in rows:
                        row.pop("updated_at", None)
        self.assertEqual(original, returned)

    def test_merge_keeps_local_records_and_lets_the_file_win_for_shared_codes(self):
        self.seed(self.root, usd="500")
        data, _ = backup_data.build_backup_bytes(self.settings, password=None, app_version="1", data_root=self.root)
        local = self.root / "local"
        self.seed(local, usd="1", stock="THYAO")                                   # local has USD=1 and THYAO
        before = {"precision": 5, "profile_names": {"profile1": "Benim", "profile2": "Profil 2"}}
        _info, clean = backup_data.load_clean(data)
        report = backup_data.apply_backup(clean, backup_data.MERGE, before, app_version="1", data_root=local)
        currency_and_metals, stocks = self.rows(local)
        self.assertIn(("USD", "500", "30.5"), currency_and_metals)                # file wins
        self.assertEqual({s[0] for s in stocks}, {"ASELS", "THYAO"})              # local-only THYAO survives
        self.assertEqual(report.settings["precision"], 5)                          # merge keeps local preferences
        self.assertEqual(report.settings["profile_names"]["profile1"], "Benim")    # and names

    def test_replace_removes_records_that_are_not_in_the_file(self):
        self.seed(self.root)
        data, _ = backup_data.build_backup_bytes(self.settings, password=None, app_version="1", data_root=self.root)
        local = self.root / "local"
        self.seed(local, stock="THYAO")
        _info, clean = backup_data.load_clean(data)
        backup_data.apply_backup(clean, backup_data.REPLACE, self.settings, app_version="1", data_root=local)
        self.assertEqual({s[0] for s in self.rows(local)[1]}, {"ASELS"})

    def test_profiles_missing_from_the_file_are_left_alone_even_on_replace(self):
        self.seed(self.root)
        self.seed(self.root, profile="profile2", stock="KCHOL")
        local = self.root / "local"
        self.seed(local, profile="profile2", stock="LOCAL")
        only_profile1 = {"preferences": {}, "profiles": [backup_data.collect_payload(self.settings, self.root)["profiles"][0]]}
        clean = backup.validate_payload(only_profile1)
        backup_data.apply_backup(clean, backup_data.REPLACE, self.settings, app_version="1", data_root=local)
        self.assertEqual({s[0] for s in self.rows(local, "profile2")[1]}, {"LOCAL"})

    def test_a_safety_backup_of_the_current_data_is_saved_first(self):
        self.seed(self.root)
        local = self.root / "local"
        self.seed(local, stock="THYAO")
        data, _ = backup_data.build_backup_bytes(self.settings, password=None, app_version="1", data_root=self.root)
        _info, clean = backup_data.load_clean(data)
        report = backup_data.apply_backup(clean, backup_data.REPLACE, self.settings, app_version="1", data_root=local)
        self.assertTrue(report.safety_backup.is_file())
        _info, previous = backup.read_backup(report.safety_backup.read_bytes())
        self.assertEqual(previous["profiles"][0]["stocks"][0]["symbol"], "THYAO")   # what was there before
        _info, restored = backup_data.load_clean(report.safety_backup.read_bytes())  # and it is a normal, restorable backup
        self.assertEqual(restored.profiles[0].stocks[0]["symbol"], "THYAO")

    def test_only_the_five_newest_safety_backups_are_kept(self):
        local = self.root / "local"
        self.seed(local)
        for index in range(8):
            backup_data.write_safety_backup(self.settings, "1", local)
            time.sleep(0.01)
        self.assertEqual(len(list(backup_data.backups_dir(local).glob("before-restore-*.ftbackup"))), backup_data.KEEP_SAFETY_BACKUPS)

    def test_nothing_is_modified_when_the_file_cannot_be_read(self):
        self.seed(self.root)
        before = self.rows(self.root)
        data, _ = backup_data.build_backup_bytes(self.settings, password=PASSWORD, app_version="1", data_root=self.root)
        with self.assertRaises(WrongPasswordError):
            backup_data.load_clean(data, "wrong-password")
        with self.assertRaises(NotABackupError):
            backup_data.load_clean(b"garbage")
        self.assertEqual(self.rows(self.root), before)
        self.assertFalse(backup_data.backups_dir(self.root).exists())

    def test_rows_the_store_rejects_are_reported(self):
        clean = backup.validate_payload(PAYLOAD)
        clean.profiles[0].currency[0]["quantity"] = Decimal("0")     # slipped past (simulated): the store must still refuse
        report = backup_data.apply_backup(clean, backup_data.MERGE, self.settings, app_version="1", data_root=self.root)
        self.assertTrue(any("USD" in m for m in report.skipped))
        self.assertEqual(report.total_imported, 2)

    def test_invalid_mode(self):
        with self.assertRaises(ValueError):
            backup_data.apply_backup(backup.validate_payload(PAYLOAD), "overwrite", self.settings, app_version="1", data_root=self.root)

    def test_works_in_english(self):
        set_language("en")
        self.addCleanup(set_language, "tr")
        self.seed(self.root)
        data, _ = backup_data.build_backup_bytes(self.settings, password=None, app_version="1", data_root=self.root)
        local = self.root / "local"
        _info, clean = backup_data.load_clean(data)
        report = backup_data.apply_backup(clean, backup_data.REPLACE, self.settings, app_version="1", data_root=local)
        self.assertEqual(report.total_imported, 3)
        self.assertEqual(self.rows(local), self.rows(self.root))
        with self.assertRaises(BackupError) as caught:
            backup_data.apply_backup(clean, backup_data.REPLACE, self.settings, app_version="1", data_root=Path("/proc/nonexistent/x"))
        self.assertNotRegex(str(caught.exception), r"[çğıöşüÇĞİÖŞÜ]{2}")


if __name__ == "__main__":
    unittest.main()
