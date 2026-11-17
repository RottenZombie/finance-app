"""Qt-free market refresh logic (currency rates + metals) with a last-good cache.

Keeping this outside the QThread worker makes it unit-testable. When a provider
is down, the last successful value (at most seven days old) is shown and the
status text says so explicitly, instead of leaving the whole app without data.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Callable

from core.api import get_all_rates, get_metal_prices
from core.app_paths import app_data_directory
from core.cache import load_json, save_json_atomic
from core.log_setup import get_logger
from features.currencies import CURRENCY_INFO

log = get_logger("market")

CACHE_MAX_AGE = timedelta(days=7)
METAL_LABELS = {"gold": "altın", "silver": "gümüş"}


def default_cache_path() -> Path:
    return app_data_directory() / "cache" / "market_cache.json"


def _parse_iso(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _positive(value: object) -> float | None:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return None
    number = float(value)
    return number if number > 0 and number == number and number != float("inf") else None


def _entry_value(entry: object, now: datetime) -> tuple[float, datetime] | None:
    """Return (value, saved_at) for a cache entry that is valid and fresh."""
    if not isinstance(entry, dict):
        return None
    value = _positive(entry.get("v"))
    saved = _parse_iso(entry.get("at"))
    if value is None or saved is None or now - saved > CACHE_MAX_AGE:
        return None
    return value, saved


def _local_text(moment: datetime) -> str:
    return moment.astimezone().strftime("%d.%m.%Y %H:%M")


def apply_cache(data: dict[str, Any], cache_path: Path, now: datetime) -> dict[str, Any]:
    """Store fresh values in the cache and fill missing ones from it."""
    cache = load_json(cache_path)
    rate_entries = cache.get("rates") if isinstance(cache.get("rates"), dict) else {}
    metal_entries = cache.get("metals") if isinstance(cache.get("metals"), dict) else {}
    stamp = now.isoformat(timespec="seconds")
    changed = False

    online = str(data.get("status", "")).startswith("Online")
    if online:
        for code in CURRENCY_INFO:
            value = _positive(data.get(code))
            if code != "TRY" and value is not None:
                rate_entries[code] = {"v": value, "at": stamp}
                changed = True
    else:
        oldest: datetime | None = None
        for code in CURRENCY_INFO:
            if code == "TRY":
                continue
            found = _entry_value(rate_entries.get(code), now)
            if found is not None:
                data[code] = found[0]
                oldest = found[1] if oldest is None else min(oldest, found[1])
        if oldest is not None:
            data["status"] = f"Offline (önbellek: {_local_text(oldest)})"

    cached_metals: list[str] = []
    for key in METAL_LABELS:
        value = _positive(data.get(key))
        if value is not None:
            metal_entries[key] = {"v": value, "at": stamp}
            changed = True
            continue
        found = _entry_value(metal_entries.get(key), now)
        if found is not None:
            data[key] = found[0]
            cached_metals.append(METAL_LABELS[key])
        else:
            data[key] = None
    if cached_metals:
        data["status"] = f"{data.get('status', '')} · {'/'.join(cached_metals)} önbellekten".strip(" ·")

    if changed:
        cache["version"] = 1
        cache["rates"] = rate_entries
        cache["metals"] = metal_entries
        save_json_atomic(cache_path, cache)
    return data


def offline_snapshot() -> dict[str, Any]:
    now = datetime.now(timezone.utc)
    data: dict[str, Any] = {code: None for code in CURRENCY_INFO}
    data.update({"TRY": 1.0, "gold": None, "silver": None, "status": "Offline"})
    data["fetched_at"] = now.astimezone().strftime("%d.%m.%Y %H:%M:%S %Z").strip()
    return data


def collect_market_snapshot(
    cache_path: str | Path | None = None,
    *,
    rates_fn: Callable[[], dict[str, Any]] = get_all_rates,
    metals_fn: Callable[[], tuple[float | None, float | None]] = get_metal_prices,
    now: datetime | None = None,
) -> dict[str, Any]:
    """Fetch rates and metals, then apply the last-good cache. Never raises."""
    moment = now or datetime.now(timezone.utc)
    try:
        data = dict(rates_fn())
        gold, silver = metals_fn()
        data["gold"], data["silver"] = gold, silver
        data["fetched_at"] = moment.astimezone().strftime("%d.%m.%Y %H:%M:%S %Z").strip()
        return apply_cache(data, Path(cache_path) if cache_path else default_cache_path(), moment)
    except Exception:
        log.error("Piyasa verisi toplanamadı", exc_info=True)
        return offline_snapshot()
