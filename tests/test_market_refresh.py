from __future__ import annotations

import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import Mock, patch

import requests

from core.api import get_all_rates, get_metal_prices, parse_tcmb_xml
from core.market_refresh import collect_market_snapshot

TCMB_XML = b"""<?xml version="1.0" encoding="UTF-8"?>
<?xml-stylesheet type="text/xsl" href="isokur.xsl"?>
<Tarih_Date Tarih="16.11.2026" Date="11/16/2026" Bulten_No="2026/220">
<Currency CrossOrder="0" Kod="USD" CurrencyCode="USD"><Unit>1</Unit><Isim>ABD DOLARI</Isim>
<ForexBuying>35.00</ForexBuying><ForexSelling>35.10</ForexSelling></Currency>
<Currency CrossOrder="1" Kod="EUR" CurrencyCode="EUR"><Unit>1</Unit><Isim>EURO</Isim>
<ForexBuying>38.00</ForexBuying><ForexSelling>38.20</ForexSelling></Currency>
<Currency CrossOrder="2" Kod="JPY" CurrencyCode="JPY"><Unit>100</Unit><Isim>JAPON YENI</Isim>
<ForexBuying>23.00</ForexBuying><ForexSelling>23.40</ForexSelling></Currency>
<Currency CrossOrder="3" Kod="XDR" CurrencyCode="XDR"><Unit>1</Unit><ForexBuying>1</ForexBuying></Currency>
<Currency CrossOrder="4" Kod="CHF" CurrencyCode="CHF"><Unit>1</Unit><ForexBuying></ForexBuying><ForexSelling></ForexSelling></Currency>
</Tarih_Date>"""


class TcmbTests(unittest.TestCase):
    def test_parse_uses_mid_value_and_unit(self):
        rates = parse_tcmb_xml(TCMB_XML)
        self.assertAlmostEqual(rates["USD"], 35.05)
        self.assertAlmostEqual(rates["EUR"], 38.10)
        self.assertAlmostEqual(rates["JPY"], 0.232)
        self.assertNotIn("XDR", rates)   # not a supported currency
        self.assertNotIn("CHF", rates)   # empty quote must be skipped, not zero

    def test_parse_rejects_entity_declarations_and_oversize(self):
        evil = b'<?xml version="1.0"?><!DOCTYPE a [<!ENTITY x "y">]><a/>'
        with self.assertRaises(ValueError):
            parse_tcmb_xml(evil)
        with self.assertRaises(ValueError):
            parse_tcmb_xml(b"<a>" + b"x" * 2_000_000 + b"</a>")

    @patch("core.api.requests.get")
    def test_tcmb_is_used_when_primary_provider_fails(self, get):
        def fake_get(url, **_kwargs):
            if "open.er-api.com" in url:
                raise requests.ConnectionError("down")
            response = Mock()
            response.content = TCMB_XML
            return response
        get.side_effect = fake_get
        result = get_all_rates()
        self.assertEqual(result["status"], "Online (TCMB yedek)")
        self.assertAlmostEqual(result["USD"], 35.05)
        self.assertEqual(result["TRY"], 1.0)
        self.assertIsNone(result["HUF"])  # TCMB does not publish every currency

    @patch("core.api.requests.get", side_effect=RuntimeError("offline"))
    def test_everything_down_gives_offline_with_all_keys(self, _get):
        result = get_all_rates()
        self.assertEqual(result["status"], "Offline")
        self.assertIsNone(result["USD"])

    @patch("core.api.requests.get")
    def test_metals_fail_independently_and_return_none(self, get):
        def fake_get(url, **_kwargs):
            if url.endswith("XAG"):
                raise requests.Timeout("slow")
            response = Mock()
            response.json.return_value = {"price": 2650.5}
            return response
        get.side_effect = fake_get
        self.assertEqual(get_metal_prices(), (2650.5, None))

    @patch("core.api.requests.get")
    def test_nonsense_metal_prices_are_rejected(self, get):
        response = Mock()
        response.json.return_value = {"price": "nan"}
        get.return_value = response
        self.assertEqual(get_metal_prices(), (None, None))


class SnapshotCacheTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / "market.json"
        self.now = datetime(2026, 11, 16, 12, 0, tzinfo=timezone.utc)

    @staticmethod
    def online(usd=35.0, eur=38.0):
        return lambda: {"USD": usd, "EUR": eur, "HUF": None, "TRY": 1.0, "status": "Online"}

    @staticmethod
    def offline():
        return {"USD": None, "EUR": None, "HUF": None, "TRY": 1.0, "status": "Offline"}

    def snapshot(self, rates, metals, now=None):
        return collect_market_snapshot(
            self.cache, rates_fn=rates, metals_fn=metals, now=now or self.now
        )

    def test_online_data_passes_through_unchanged(self):
        data = self.snapshot(self.online(), lambda: (2650.0, 31.0))
        self.assertEqual(data["status"], "Online")
        self.assertEqual((data["USD"], data["gold"], data["silver"]), (35.0, 2650.0, 31.0))
        self.assertIn("fetched_at", data)

    def test_last_good_values_are_used_when_offline(self):
        self.snapshot(self.online(), lambda: (2650.0, 31.0))
        later = self.now + timedelta(hours=5)
        data = self.snapshot(self.offline, lambda: (None, None), now=later)
        self.assertTrue(data["status"].startswith("Offline (önbellek:"))
        self.assertIn("altın/gümüş önbellekten", data["status"])
        self.assertEqual((data["USD"], data["EUR"]), (35.0, 38.0))
        self.assertEqual((data["gold"], data["silver"]), (2650.0, 31.0))
        self.assertIsNone(data["HUF"])  # never cached, never invented

    def test_expired_cache_is_ignored(self):
        self.snapshot(self.online(), lambda: (2650.0, 31.0))
        data = self.snapshot(self.offline, lambda: (None, None), now=self.now + timedelta(days=8))
        self.assertEqual(data["status"], "Offline")
        self.assertIsNone(data["USD"])
        self.assertIsNone(data["gold"])

    def test_only_missing_metal_is_filled_from_cache(self):
        self.snapshot(self.online(), lambda: (2650.0, 31.0))
        data = self.snapshot(self.online(36.0, 39.0), lambda: (2700.0, None),
                             now=self.now + timedelta(hours=1))
        self.assertEqual(data["gold"], 2700.0)
        self.assertEqual(data["silver"], 31.0)
        self.assertEqual(data["USD"], 36.0)
        self.assertEqual(data["status"], "Online · gümüş önbellekten")

    def test_no_cache_and_offline_stays_plain_offline(self):
        data = self.snapshot(self.offline, lambda: (None, None))
        self.assertEqual(data["status"], "Offline")
        self.assertIsNone(data["gold"])

    def test_unexpected_exception_never_escapes(self):
        def boom():
            raise RuntimeError("provider exploded")
        data = self.snapshot(boom, lambda: (None, None))
        self.assertEqual(data["status"], "Offline")
        self.assertEqual(data["TRY"], 1.0)

    def test_corrupt_cache_file_is_tolerated(self):
        self.cache.write_text("<<<garbage>>>", encoding="utf-8")
        data = self.snapshot(self.online(), lambda: (1.0, 2.0))
        self.assertEqual(data["status"], "Online")


if __name__ == "__main__":
    unittest.main()
