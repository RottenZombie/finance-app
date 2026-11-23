from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone, tzinfo

from core.timefmt import format_local


class TurkishNameZone(tzinfo):
    """Time zone whose *name* is localised, like Windows' 'Türkiye Standart Saati'."""

    def utcoffset(self, dt):
        return timedelta(hours=3)

    def dst(self, dt):
        return timedelta(0)

    def tzname(self, dt):
        return "Türkiye Standart Saati"


class TimeFormatTests(unittest.TestCase):
    MOMENT = datetime(2026, 11, 20, 6, 53, 40, tzinfo=timezone.utc)

    def test_offset_is_numeric(self):
        self.assertEqual(format_local(self.MOMENT, timezone(timedelta(hours=3))), "20.11.2026 09:53:40 (UTC+03:00)")
        self.assertEqual(format_local(self.MOMENT, timezone.utc), "20.11.2026 06:53:40 (UTC+00:00)")
        self.assertEqual(format_local(self.MOMENT, timezone(timedelta(hours=-5, minutes=-30))), "20.11.2026 01:23:40 (UTC-05:30)")

    def test_a_localised_zone_name_never_reaches_the_text(self):
        text = format_local(self.MOMENT, TurkishNameZone())
        self.assertEqual(text, "20.11.2026 09:53:40 (UTC+03:00)")
        self.assertNotIn("Türkiye", text)

    def test_local_timestamps_in_exports_have_no_zone_name(self):
        from features.export_metadata import local_timestamp

        text = local_timestamp()
        self.assertRegex(text, r"^\d{2}\.\d{2}\.\d{4} \d{2}:\d{2}:\d{2} \(UTC[+-]\d{2}:\d{2}\)$")


if __name__ == "__main__":
    unittest.main()
