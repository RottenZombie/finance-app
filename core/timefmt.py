"""Locale-independent time formatting.

``strftime('%Z')`` prints the time-zone *name* in the operating-system language
(for example "Türkiye Standart Saati"), which leaked Turkish text into English
exports. A numeric UTC offset is the same on every system.
"""
from __future__ import annotations

from datetime import datetime, timedelta, tzinfo


def format_local(moment: datetime, tz: tzinfo | None = None) -> str:
    """``20.11.2026 09:53:40 (UTC+03:00)`` in the local (or given) time zone."""
    local = moment.astimezone(tz)
    offset = local.utcoffset() or timedelta(0)
    minutes = int(offset.total_seconds() // 60)
    sign = "+" if minutes >= 0 else "-"
    hours, rest = divmod(abs(minutes), 60)
    return f"{local:%d.%m.%Y %H:%M:%S} (UTC{sign}{hours:02d}:{rest:02d})"
