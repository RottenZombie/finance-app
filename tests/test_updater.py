from __future__ import annotations

import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from core.updater import (
    UpdateError,
    download_release_asset,
    is_newer_version,
    parse_release_payload,
)


class UpdaterTests(unittest.TestCase):
    def _payload(self, tag="v2.2.8", **overrides):
        data = {
            "tag_name": tag,
            "draft": False,
            "prerelease": False,
            "html_url": f"https://github.com/RottenZombie/finance-app/releases/tag/{tag}",
            "body": "Test release notes",
            "assets": [{
                "name": "FinanceTerminal.exe",
                "browser_download_url": f"https://github.com/RottenZombie/finance-app/releases/download/{tag}/FinanceTerminal.exe",
                "size": 2048,
                "digest": None,
            }],
        }
        data.update(overrides)
        return data

    def test_dev_suffix_same_stable_version_is_not_an_update(self):
        self.assertFalse(is_newer_version("2.2.7-dev", "v2.2.7"))

    def test_newer_release_is_detected(self):
        self.assertTrue(is_newer_version("2.2.7", "v2.2.8"))
        self.assertFalse(is_newer_version("2.2.8", "v2.2.7"))

    def test_malformed_or_path_like_version_is_rejected(self):
        with self.assertRaises(UpdateError):
            is_newer_version("2.2.7", "2.2.8/../../other")

    def test_same_release_is_ignored(self):
        self.assertIsNone(parse_release_payload(self._payload("v2.2.7"), "2.2.7-dev"))

    def test_new_release_returns_expected_asset_metadata(self):
        info = parse_release_payload(self._payload(), "2.2.7")
        self.assertIsNotNone(info)
        self.assertEqual(info.version, "2.2.8")
        self.assertEqual(info.asset_size, 2048)
        self.assertEqual(info.download_url.split("/")[-1], "FinanceTerminal.exe")

    def test_prerelease_is_ignored(self):
        self.assertIsNone(parse_release_payload(self._payload(prerelease=True), "2.2.7"))

    def test_wrong_asset_is_rejected(self):
        payload = self._payload()
        payload["assets"] = [{"name": "other.exe", "browser_download_url": "https://github.com/a/b/x.exe", "size": 2048}]
        with self.assertRaises(UpdateError):
            parse_release_payload(payload, "2.2.7")

    def test_non_github_download_url_is_rejected(self):
        payload = self._payload()
        payload["assets"][0]["browser_download_url"] = "https://example.com/FinanceTerminal.exe"
        with self.assertRaises(UpdateError):
            parse_release_payload(payload, "2.2.7")

    def test_download_checks_mz_signature_size_and_digest(self):
        content = b"MZ" + (b"F" * 2046)
        digest = hashlib.sha256(content).hexdigest()
        info = parse_release_payload(self._payload(), "2.2.7")
        info = info.__class__(
            tag_name=info.tag_name,
            version=info.version,
            release_url=info.release_url,
            download_url=info.download_url,
            asset_size=len(content),
            digest=digest,
            release_notes=info.release_notes,
        )

        class FakeResponse:
            def __init__(self, data):
                self.data = data
                self.offset = 0
            def __enter__(self):
                return self
            def __exit__(self, *_args):
                return False
            def read(self, size=-1):
                if self.offset >= len(self.data):
                    return b""
                chunk = self.data[self.offset:self.offset + size]
                self.offset += len(chunk)
                return chunk

        with patch("core.updater.urlopen", return_value=FakeResponse(content)):
            downloaded = download_release_asset(info)
        try:
            self.assertTrue(downloaded.is_file())
            self.assertEqual(downloaded.read_bytes(), content)
        finally:
            downloaded.unlink(missing_ok=True)

    def test_download_reports_byte_progress_and_speed(self):
        content = b"MZ" + (b"P" * 2046)
        info = parse_release_payload(self._payload(), "2.2.7")
        info = info.__class__(
            tag_name=info.tag_name,
            version=info.version,
            release_url=info.release_url,
            download_url=info.download_url,
            asset_size=len(content),
            digest=hashlib.sha256(content).hexdigest(),
            release_notes=info.release_notes,
        )

        class FakeResponse:
            def __init__(self, data):
                self.data = data
                self.offset = 0
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, size=-1):
                if self.offset >= len(self.data): return b""
                chunk = self.data[self.offset:self.offset + size]
                self.offset += len(chunk)
                return chunk

        progress = []
        with patch("core.updater.urlopen", return_value=FakeResponse(content)):
            downloaded = download_release_asset(
                info, progress_callback=lambda received, total, speed: progress.append(
                    (received, total, speed)
                )
            )
        try:
            self.assertGreaterEqual(len(progress), 3)
            self.assertEqual(progress[0][0], 0)
            self.assertEqual(progress[-1][0], len(content))
            self.assertEqual(progress[-1][1], len(content))
            self.assertGreaterEqual(progress[-1][2], 0.0)
            self.assertTrue(downloaded.is_file())
        finally:
            downloaded.unlink(missing_ok=True)

    def test_bad_digest_rejects_and_cleans_temporary_file(self):
        content = b"MZ" + (b"G" * 2046)
        info = parse_release_payload(self._payload(), "2.2.7")
        info = info.__class__(
            tag_name=info.tag_name,
            version=info.version,
            release_url=info.release_url,
            download_url=info.download_url,
            asset_size=len(content),
            digest="0" * 64,
            release_notes=info.release_notes,
        )

        class FakeResponse:
            def __enter__(self): return self
            def __exit__(self, *_args): return False
            def read(self, _size=-1):
                nonlocal content
                if content:
                    result, content = content, b""
                    return result
                return b""

        with patch("core.updater.urlopen", return_value=FakeResponse()):
            with self.assertRaises(UpdateError):
                download_release_asset(info)


if __name__ == "__main__":
    unittest.main()
