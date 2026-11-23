from __future__ import annotations

import unittest
from datetime import datetime
from decimal import Decimal

from core.i18n import set_language
from features.bist.quotes import Quote
from features.bist.refresh_status import status_text, summarize_refresh


def quote(symbol, price, as_of="2026-11-20T14:59:00+00:00", stale=False):
    return Quote(symbol, Decimal(str(price)), as_of, "Test", "2026-11-20T15:00:00+00:00", stale)


def payload(live=(), cached=(), failed=()):
    return {"live": list(live), "cached": list(cached), "failed": list(failed)}


NOW = datetime(2026, 11, 20, 12, 5, 33)


class SummaryTests(unittest.TestCase):
    def tearDown(self):
        set_language("tr")

    def test_first_refresh_has_nothing_to_compare(self):
        summary = summarize_refresh({}, {"A": quote("A", 10)}, payload(live=["A"]), NOW)
        self.assertFalse(summary.compared)
        text = status_text(summary)
        self.assertIn("Son güncelleme: 20.11.2026 12:05:33", text)
        self.assertIn("1 hisse güncel", text)
        self.assertNotIn("aynı kaldı", text)

    def test_changed_and_unchanged_prices_are_counted_with_direction(self):
        before = {"A": quote("A", 10), "B": quote("B", 20), "C": quote("C", 30)}
        after = {"A": quote("A", 11), "B": quote("B", 20), "C": quote("C", 28.5)}
        summary = summarize_refresh(before, after, payload(live=["A", "B", "C"]), NOW)
        self.assertEqual((summary.changed, summary.unchanged), (2, 1))
        self.assertEqual(summary.changes["A"], Decimal("1"))
        self.assertEqual(summary.changes["C"], Decimal("-1.5"))
        self.assertIn("2 fiyat değişti, 1 aynı kaldı", status_text(summary))

    def test_unchanged_prices_explain_why_nothing_moved(self):
        same = {"A": quote("A", 10)}
        text = status_text(summarize_refresh(same, same, payload(live=["A"]), NOW))
        self.assertIn("0 fiyat değişti, 1 aynı kaldı", text)
        self.assertIn("piyasa kapalıysa", text)

    def test_latest_trade_time_is_shown_from_the_newest_live_quote(self):
        current = {
            "A": quote("A", 1, "2026-11-19T14:00:00+00:00"),
            "B": quote("B", 1, "2026-11-20T14:59:00+00:00"),
            "C": quote("C", 1, "2026-11-10", stale=True),       # cached: must not count
        }
        summary = summarize_refresh({}, current, payload(live=["A", "B"], cached=["C"]), NOW)
        self.assertIn("Son işlem zamanı:", status_text(summary))
        self.assertTrue(summary.latest_trade.startswith("20.11.2026"))

    def test_failures_and_cache_get_a_helpful_hint(self):
        failed = status_text(summarize_refresh({}, {}, payload(failed=["A"]), NOW))
        self.assertIn("fiyat alınamayan: A", failed)
        self.assertIn("İnternet bağlantınızı kontrol edin", failed)
        cached = status_text(summarize_refresh({}, {"A": quote("A", 1, stale=True)}, payload(cached=["A"]), NOW))
        self.assertIn("1 hisse önbellekten", cached)
        self.assertIn("son bilinen fiyatlar", cached)

    def test_cached_prices_never_count_as_changes(self):
        before = {"A": quote("A", 10)}
        after = {"A": quote("A", 12, stale=True)}
        summary = summarize_refresh(before, after, payload(cached=["A"]), NOW)
        self.assertEqual(summary.changes, {})
        self.assertFalse(summary.compared)

    def test_garbage_payload_does_not_crash(self):
        summary = summarize_refresh({}, {}, None, NOW)
        self.assertEqual((summary.live, summary.cached, summary.failed), (0, 0, ()))
        self.assertTrue(status_text(summary).startswith("Son güncelleme:"))

    def test_english_text(self):
        set_language("en")
        before = {"A": quote("A", 10)}
        text = status_text(summarize_refresh(before, {"A": quote("A", 11)}, payload(live=["A"]), NOW))
        self.assertIn("Last update: 20.11.2026 12:05:33", text)
        self.assertIn("1 changed, 0 unchanged", text)
        self.assertIn("Latest trade time:", text)


if __name__ == "__main__":
    unittest.main()
