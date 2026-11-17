from __future__ import annotations

import json
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from pathlib import Path

import requests

from features.bist.quotes import (
    CIRCUIT_BREAKER_FAILURES,
    IsYatirimProvider,
    Quote,
    QuoteError,
    QuoteService,
    YahooChartProvider,
    parse_isyatirim,
    parse_yahoo_chart,
    quotes_from_payload,
)


def yahoo_payload(price=314.0, symbol="THYAO.IS", currency="TRY", ts=1_760_000_000):
    return {"chart": {"result": [{"meta": {
        "symbol": symbol, "currency": currency,
        "regularMarketPrice": price, "regularMarketTime": ts,
    }}], "error": None}}


class FakeProvider:
    def __init__(self, name, prices=None, fail_all=False):
        self.name = name
        self.prices = prices or {}
        self.fail_all = fail_all
        self.calls: list[str] = []

    def fetch(self, symbol):
        self.calls.append(symbol)
        if self.fail_all or symbol not in self.prices:
            raise QuoteError("yok")
        return Quote(
            symbol, Decimal(str(self.prices[symbol])), "2026-11-13", self.name,
            datetime.now(timezone.utc).isoformat(timespec="seconds"),
        )


class ParserTests(unittest.TestCase):
    def test_yahoo_valid_quote(self):
        quote = parse_yahoo_chart(yahoo_payload(63.40000152587891, "AKBNK.IS"), "AKBNK")
        self.assertEqual(quote.price, Decimal("63.4000"))
        self.assertEqual(quote.source, "Yahoo Finance")
        self.assertIsNotNone(quote.as_of)
        self.assertFalse(quote.stale)

    def test_yahoo_rejects_untrustworthy_answers(self):
        bad = [
            yahoo_payload(currency="USD"),
            yahoo_payload(price=0),
            yahoo_payload(price=-3),
            yahoo_payload(price=float("nan")),
            yahoo_payload(price=None),
            yahoo_payload(symbol="OTHER.IS"),
            {"chart": {"result": None, "error": {"code": "Not Found"}}},
            {"chart": {"result": [], "error": None}},
            {"unexpected": True},
            None,
            [],
        ]
        for payload in bad:
            with self.subTest(payload=payload), self.assertRaises(QuoteError):
                parse_yahoo_chart(payload, "THYAO")

    def test_isyatirim_picks_latest_valid_row(self):
        payload = {"value": [
            {"HGDG_HS_KODU": "THYAO", "HGDG_KAPANIS": 300, "HGDG_TARIH": "2026-11-10T00:00:00"},
            {"HGDG_HS_KODU": "THYAO", "HGDG_KAPANIS": 305.5, "HGDG_TARIH": "2026-11-12T00:00:00"},
            {"HGDG_HS_KODU": "THYAO", "HGDG_KAPANIS": 0, "HGDG_TARIH": "2026-11-13T00:00:00"},
            {"HGDG_HS_KODU": "OTHER", "HGDG_KAPANIS": 1, "HGDG_TARIH": "2026-11-14T00:00:00"},
        ]}
        quote = parse_isyatirim(payload, "THYAO")
        self.assertEqual(quote.price, Decimal("305.5000"))
        self.assertEqual(quote.as_of, "2026-11-12")

    def test_isyatirim_rejects_empty_or_invalid(self):
        for payload in ({"value": []}, {"value": [{"HGDG_KAPANIS": "x"}]}, {}, None):
            with self.subTest(payload=payload), self.assertRaises(QuoteError):
                parse_isyatirim(payload, "THYAO")


class ProviderTests(unittest.TestCase):
    class Session:
        def __init__(self, behaviours):
            self.behaviours = list(behaviours)
            self.urls = []

        def get(self, url, **_kwargs):
            self.urls.append(url)
            behaviour = self.behaviours.pop(0)
            if isinstance(behaviour, Exception):
                raise behaviour
            response = requests.Response()
            response.status_code = 200
            response._content = json.dumps(behaviour).encode()
            return response

    def test_yahoo_falls_back_to_second_host(self):
        session = self.Session([requests.ConnectionError("down"), yahoo_payload()])
        quote = YahooChartProvider(session=session).fetch("THYAO")
        self.assertEqual(quote.price, Decimal("314.0000"))
        self.assertIn("query1", session.urls[0])
        self.assertIn("query2", session.urls[1])

    def test_yahoo_raises_quote_error_when_all_hosts_fail(self):
        session = self.Session([requests.Timeout("a"), requests.Timeout("b")])
        with self.assertRaises(QuoteError):
            YahooChartProvider(session=session).fetch("THYAO")

    def test_isyatirim_network_failure_becomes_quote_error(self):
        session = self.Session([requests.ConnectionError("down")])
        with self.assertRaises(QuoteError):
            IsYatirimProvider(session=session).fetch("THYAO")


class ServiceTests(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self._tmp.cleanup)
        self.cache = Path(self._tmp.name) / "quotes.json"

    def service(self, providers, **kwargs):
        return QuoteService(providers, cache_path=self.cache, max_workers=1, **kwargs)

    def test_first_provider_wins_and_result_is_cached(self):
        first = FakeProvider("A", {"THYAO": "314"})
        second = FakeProvider("B", {"THYAO": "999"})
        result = self.service([first, second]).fetch(["thyao"])
        self.assertEqual(result.quotes["THYAO"].price, Decimal("314"))
        self.assertEqual(result.live, ["THYAO"])
        self.assertEqual(second.calls, [])
        self.assertIn("THYAO", json.loads(self.cache.read_text(encoding="utf-8"))["quotes"])

    def test_falls_back_to_second_provider(self):
        result = self.service([
            FakeProvider("A", fail_all=True), FakeProvider("B", {"ASELS": "342.25"}),
        ]).fetch(["ASELS"])
        self.assertEqual(result.quotes["ASELS"].source, "B")
        self.assertEqual(result.live, ["ASELS"])

    def test_recent_cache_is_used_and_flagged_stale_when_all_providers_fail(self):
        self.service([FakeProvider("A", {"THYAO": "314"})]).fetch(["THYAO"])
        result = self.service([FakeProvider("A", fail_all=True)]).fetch(["THYAO"])
        quote = result.quotes["THYAO"]
        self.assertTrue(quote.stale)
        self.assertEqual(quote.price, Decimal("314"))
        self.assertEqual(result.cached, ["THYAO"])
        self.assertEqual(result.live, [])

    def test_expired_cache_is_not_used(self):
        old = (datetime.now(timezone.utc) - timedelta(days=30)).isoformat(timespec="seconds")
        self.cache.write_text(json.dumps({"quotes": {"THYAO": {
            "price": "314", "as_of": None, "source": "A", "fetched_at": old,
        }}}), encoding="utf-8")
        result = self.service([FakeProvider("A", fail_all=True)]).fetch(["THYAO"])
        self.assertEqual(result.failed, ["THYAO"])
        self.assertNotIn("THYAO", result.quotes)

    def test_corrupt_cache_file_is_ignored(self):
        self.cache.write_text("{not json", encoding="utf-8")
        result = self.service([FakeProvider("A", {"THYAO": "10"})]).fetch(["THYAO"])
        self.assertEqual(result.live, ["THYAO"])
        # and it is repaired by the successful refresh
        self.assertIn("quotes", json.loads(self.cache.read_text(encoding="utf-8")))

    def test_invalid_cache_entries_are_skipped(self):
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        self.cache.write_text(json.dumps({"quotes": {
            "THYAO": {"price": "-5", "fetched_at": now},
            "ASELS": "garbage",
        }}), encoding="utf-8")
        result = self.service([FakeProvider("A", fail_all=True)]).fetch(["THYAO", "ASELS"])
        self.assertEqual(sorted(result.failed), ["ASELS", "THYAO"])

    def test_circuit_breaker_stops_hammering_a_dead_provider(self):
        symbols = [f"AAA{i}" for i in range(12)]
        dead = FakeProvider("dead", fail_all=True)
        alive = FakeProvider("alive", {s: "10" for s in symbols})
        result = self.service([dead, alive]).fetch(symbols)
        self.assertEqual(len(result.live), 12)
        self.assertEqual(len(dead.calls), CIRCUIT_BREAKER_FAILURES)

    def test_invalid_and_duplicate_symbols_are_ignored(self):
        provider = FakeProvider("A", {"THYAO": "1"})
        result = self.service([provider]).fetch(["THYAO", "thyao.is", "!!", "", None])
        self.assertEqual(provider.calls, ["THYAO"])
        self.assertEqual(list(result.quotes), ["THYAO"])

    def test_empty_symbol_list_makes_no_requests(self):
        provider = FakeProvider("A")
        self.assertEqual(self.service([provider]).fetch([]).quotes, {})
        self.assertEqual(provider.calls, [])

    def test_payload_round_trip_and_garbage_tolerance(self):
        result = self.service([FakeProvider("A", {"THYAO": "314.5"})]).fetch(["THYAO"])
        rebuilt = quotes_from_payload(result.to_payload())
        self.assertEqual(rebuilt["THYAO"].price, Decimal("314.5"))
        self.assertEqual(quotes_from_payload(None), {})
        self.assertEqual(quotes_from_payload({"quotes": {"X": {"price": "abc"}, "Y": 5}}), {})


if __name__ == "__main__":
    unittest.main()
