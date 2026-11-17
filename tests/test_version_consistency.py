"""The version number must be identical everywhere it appears."""
from __future__ import annotations

import re
import unittest
from pathlib import Path

from core.version import APP_VERSION
from features.bist import __version__ as bist_version

ROOT = Path(__file__).resolve().parents[1]


class VersionConsistencyTests(unittest.TestCase):
    def test_version_is_plain_semver(self):
        self.assertRegex(APP_VERSION, r"^\d+\.\d+\.\d+$")

    def test_bist_package_follows_app_version(self):
        self.assertEqual(bist_version, APP_VERSION)

    def test_readme_headline_and_current_version(self):
        text = (ROOT / "README.md").read_text(encoding="utf-8")
        self.assertIn(f"# FinanceTerminal {APP_VERSION}", text)
        self.assertIn(f"**Current version:** `{APP_VERSION}`", text)
        self.assertIn(f"### {APP_VERSION}\n", text)

    def test_workflow_uses_the_same_version(self):
        text = (ROOT / ".github" / "workflows" / "build.yml").read_text(encoding="utf-8")
        # The trigger branch is still called "bist-ai-2.2.1"; that is a branch name,
        # not an application version, so it is ignored here.
        found = set(re.findall(r"(?<!bist-ai-)\b\d+\.\d+\.\d+\b", text))
        self.assertEqual(found, {APP_VERSION}, f"build.yml mentions versions: {sorted(found)}")

    def test_main_window_reads_the_shared_constant(self):
        text = (ROOT / "ui" / "main_window.py").read_text(encoding="utf-8")
        self.assertIn("self.VERSION = APP_VERSION", text)


if __name__ == "__main__":
    unittest.main()
