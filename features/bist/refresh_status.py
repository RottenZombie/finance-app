"""What happened in the last BIST price refresh, in words the user can read.

Pressing "update prices" used to give no visible reaction when the prices had not
moved (for example while the exchange is closed). The summary says when the refresh
finished, how many prices changed and when the latest trade happened.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from typing import Any, Mapping

from core.i18n import tr
from .quotes import Quote, format_quote_time, quote_time


@dataclass(frozen=True)
class RefreshSummary:
    finished_at: str
    live: int
    cached: int
    failed: tuple[str, ...]
    changed: int
    unchanged: int
    latest_trade: str | None
    changes: Mapping[str, Decimal] = field(default_factory=dict)  # symbol -> new - previous

    @property
    def compared(self) -> bool:
        """False on the first refresh: there is nothing to compare with yet."""
        return bool(self.changed or self.unchanged)


def summarize_refresh(
    previous: Mapping[str, Quote],
    current: Mapping[str, Quote],
    payload: Mapping[str, Any] | None,
    finished_at: datetime | None = None,
) -> RefreshSummary:
    info = payload if isinstance(payload, Mapping) else {}
    live_symbols = [s for s in (info.get("live") or []) if s in current]
    changes: dict[str, Decimal] = {}
    for symbol in live_symbols:
        before = previous.get(symbol)
        if before is not None:
            changes[symbol] = current[symbol].price - before.price

    latest: Quote | None = None
    latest_time: datetime | None = None
    for symbol in live_symbols:
        moment = quote_time(current[symbol])
        if moment is not None and (latest_time is None or moment > latest_time):
            latest, latest_time = current[symbol], moment

    moment_now = finished_at or datetime.now()
    return RefreshSummary(
        finished_at=moment_now.strftime("%d.%m.%Y %H:%M:%S"),
        live=len(live_symbols),
        cached=len(info.get("cached") or []),
        failed=tuple(info.get("failed") or ()),
        changed=sum(1 for delta in changes.values() if delta != 0),
        unchanged=sum(1 for delta in changes.values() if delta == 0),
        latest_trade=format_quote_time(latest) if latest else None,
        changes=changes,
    )


def status_text(summary: RefreshSummary) -> str:
    parts = [tr("Son güncelleme: {0}").format(summary.finished_at)]
    if summary.live:
        parts.append(tr("{0} hisse güncel").format(summary.live))
    if summary.cached:
        parts.append(tr("{0} hisse önbellekten (eski fiyat)").format(summary.cached))
    if summary.failed:
        parts.append(tr("fiyat alınamayan: ") + ", ".join(summary.failed))
    if summary.compared:
        parts.append(tr("{0} fiyat değişti, {1} aynı kaldı").format(summary.changed, summary.unchanged))
    if summary.latest_trade:
        parts.append(tr("Son işlem zamanı: {0}").format(summary.latest_trade))
    text = " · ".join(parts)
    if summary.live and summary.compared and summary.changed == 0:
        text += ". " + tr("Fiyatlar aynı kaldı: piyasa kapalıysa veya son işlem fiyatı değişmediyse bu normaldir.")
    elif not summary.live and summary.cached:
        text += ". " + tr("İnternet bağlantınızı kontrol edin; son bilinen fiyatlar gösteriliyor.")
    elif not summary.live and summary.failed:
        text += ". " + tr("Fiyat alınamadı. İnternet bağlantınızı kontrol edin.")
    return text
