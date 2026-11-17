from __future__ import annotations

import logging
import tempfile
import unittest
from pathlib import Path

from core import log_setup
from core.cache import load_json, save_json_atomic


class CacheTests(unittest.TestCase):
    def test_round_trip_and_no_temp_files_left(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sub" / "c.json"
            self.assertTrue(save_json_atomic(path, {"a": 1, "ş": "ü"}))
            self.assertEqual(load_json(path), {"a": 1, "ş": "ü"})
            self.assertEqual([p.name for p in path.parent.iterdir()], ["c.json"])

    def test_missing_corrupt_and_non_dict_files_give_empty_dict(self):
        with tempfile.TemporaryDirectory() as tmp:
            self.assertEqual(load_json(Path(tmp) / "missing.json"), {})
            bad = Path(tmp) / "bad.json"
            bad.write_text("{oops", encoding="utf-8")
            self.assertEqual(load_json(bad), {})
            bad.write_text("[1, 2]", encoding="utf-8")
            self.assertEqual(load_json(bad), {})

    def test_unserializable_data_is_reported_not_raised(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "x.json"
            self.assertFalse(save_json_atomic(path, {"bad": object()}))
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(tmp).iterdir()), [])


class LoggingTests(unittest.TestCase):
    def test_setup_writes_to_file_and_is_idempotent(self):
        base = logging.getLogger("financeterminal")
        saved = (list(base.handlers), base.level, base.propagate, log_setup._configured)
        import sys
        hook = sys.excepthook
        try:
            log_setup._configured = False
            with tempfile.TemporaryDirectory() as tmp:
                logger = log_setup.setup_logging(tmp)
                log_setup.setup_logging(tmp)  # second call must not add handlers
                file_handlers = [h for h in logger.handlers if hasattr(h, "baseFilename")]
                self.assertEqual(len(file_handlers), 1)
                log_setup.get_logger("test").warning("merhaba günlük")
                for handler in logger.handlers:
                    handler.flush()
                content = (Path(tmp) / "app.log").read_text(encoding="utf-8")
                self.assertIn("merhaba günlük", content)
                for handler in file_handlers:
                    handler.close()
                    logger.removeHandler(handler)
        finally:
            sys.excepthook = hook
            base.handlers[:] = saved[0]
            base.setLevel(saved[1])
            base.propagate = saved[2]
            log_setup._configured = saved[3]


if __name__ == "__main__":
    unittest.main()
