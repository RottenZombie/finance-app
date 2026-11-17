"""Free, keyless BIST share-price lookup with a provider chain and local cache.

There is no official free BIST price API, so stability comes from layering:

1. Providers are tried in order (Yahoo Finance chart endpoint, then İş Yatırım's
   public daily data). The first valid answer wins.
2. A provider that keeps failing during one refresh is skipped for the rest of
   that refresh, so an outage costs seconds instead of minutes.
3. Every successful quote is cached on disk. If all providers fail, a recent
   cached quote is returned and clearly flagged as ``stale``.
4. Quotes are strictly validated (finite, positive, TRY-denominated, expected
   symbol). Anything else is rejected rather than shown as a wrong value.

Prices are delayed and unofficial; they are for personal tracking only.
"""
from __future__ import annotations

import threading
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Any, Iterable, Protocol

import requests

from core.app_paths import app_data_directory
from core.cache import load_json, save_json_atomic
from core.log_setup import get_logger
from .utils import normalize_symbol

log = get_logger("bist.quotes")

REQUEST_TIMEOUT = 8
CACHE_MAX_AGE = timedelta(days=7)
CIRCUIT_BREAKER_FAILURES = 5
PRICE_QUANTUM = Decimal("0.0001")
_HEADERS = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
        "(KHTML, like Gecko) Chrome/124.0 Safari/537.36 FinanceTerminal/2.4"
    ),
    "Accept": "application/json,text/plain,*/*",
}


class QuoteError(RuntimeError):
    """A provider answer was missing, malformed or untrustworthy."""


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _parse_iso(value: object) -> datetime | None:
    try:
        parsed = datetime.fromisoformat(str(value))
    except (TypeError, ValueError):
        return None
    return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)


def _price(value: object) -> Decimal:
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        raise QuoteError(f"Geçersiz fiyat: {value!r}") from None
    if not number.is_finite() or number <= 0:
        raise QuoteError(f"Geçersiz fiyat: {value!r}")
    return number.quantize(PRICE_QUANTUM)


@dataclass(frozen=True)
class Quote:
    symbol: str
    price: Decimal
    as_of: str | None
    source: str
    fetched_at: str
    stale: bool = False

    def to_payload(self) -> dict[str, Any]:
        return {
            "price": str(self.price),
            "as_of": self.as_of,
            "source": self.source,
            "fetched_at": self.fetched_at,
            "stale": self.stale,
        }

    @classmethod
    def from_payload(cls, symbol: str, data: dict[str, Any]) -> "Quote":
        return cls(
            symbol=symbol,
            price=_price(data.get("price")),
            as_of=data.get("as_of") or None,
            source=str(data.get("source") or "Bilinmiyor"),
            fetched_at=str(data.get("fetched_at") or ""),
            stale=bool(data.get("stale", False)),
        )


# --------------------------------------------------------------------- parsing
def parse_yahoo_chart(payload: Any, symbol: str, source: str = "Yahoo Finance") -> Quote:
    chart = payload.get("chart") if isinstance(payload, dict) else None
    if not isinstance(chart, dict):
        raise QuoteError("Yahoo yanıtı beklenen biçimde değil.")
    if chart.get("error"):
        raise QuoteError("Yahoo bu hisse için hata döndürdü.")
    results = chart.get("result")
    if not isinstance(results, list) or not results or not isinstance(results[0], dict):
        raise QuoteError("Yahoo yanıtında sonuç yok.")
    meta = results[0].get("meta")
    if not isinstance(meta, dict):
        raise QuoteError("Yahoo yanıtında fiyat bilgisi yok.")

    returned = str(meta.get("symbol") or "").upper()
    if returned and returned != f"{symbol}.IS":
        raise QuoteError(f"Beklenmeyen sembol: {returned}")
    currency = str(meta.get("currency") or "").upper()
    if currency and currency not in {"TRY", "TRL"}:
        raise QuoteError(f"Beklenmeyen para birimi: {currency}")

    price = _price(meta.get("regularMarketPrice"))
    as_of = None
    timestamp = meta.get("regularMarketTime")
    if isinstance(timestamp, (int, float)) and not isinstance(timestamp, bool):
        try:
            as_of = datetime.fromtimestamp(timestamp, tz=timezone.utc).isoformat(
                timespec="seconds"
            )
        except (OverflowError, OSError, ValueError):
            as_of = None
    return Quote(symbol, price, as_of, source, _now_iso())


_ISY_DATE_FORMATS = ("%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%d-%m-%Y", "%d.%m.%Y")


def _parse_isy_date(value: object) -> date | None:
    text = str(value or "").strip()
    for fmt in _ISY_DATE_FORMATS:
        try:
            return datetime.strptime(text[:19] if "T" in fmt else text[:10], fmt).date()
        except ValueError:
            continue
    return None


def parse_isyatirim(payload: Any, symbol: str, source: str = "İş Yatırım") -> Quote:
    rows = payload.get("value") if isinstance(payload, dict) else None
    if not isinstance(rows, list) or not rows:
        raise QuoteError("İş Yatırım yanıtında veri yok.")

    candidates: list[tuple[date | None, int, Decimal]] = []
    for index, row in enumerate(rows):
        if not isinstance(row, dict):
            continue
        code = str(row.get("HGDG_HS_KODU") or "").upper()
        if code and code != symbol:
            continue
        try:
            price = _price(row.get("HGDG_KAPANIS"))
        except QuoteError:
            continue
        candidates.append((_parse_isy_date(row.get("HGDG_TARIH")), index, price))
    if not candidates:
        raise QuoteError("İş Yatırım yanıtında geçerli kapanış fiyatı yok.")

    # Latest dated row; rows without a parsable date fall back to list order.
    best = max(candidates, key=lambda item: (item[0] or date.min, item[1]))
    as_of = best[0].isoformat() if best[0] else None
    return Quote(symbol, best[2], as_of, source, _now_iso())


# ------------------------------------------------------------------- providers
class QuoteProvider(Protocol):
    name: str

    def fetch(self, symbol: str) -> Quote: ...


class YahooChartProvider:
    """Yahoo Finance public chart endpoint (unofficial, delayed)."""

    name = "Yahoo Finance"
    hosts = ("query1.finance.yahoo.com", "query2.finance.yahoo.com")

    def __init__(self, session: Any = None, timeout: float = REQUEST_TIMEOUT):
        self._session = session
        self._timeout = timeout

    def fetch(self, symbol: str) -> Quote:
        client = self._session or requests
        last_error: Exception | None = None
        for host in self.hosts:
            try:
                response = client.get(
                    f"https://{host}/v8/finance/chart/{symbol}.IS",
                    params={"range": "1d", "interval": "1d"},
                    headers=_HEADERS,
                    timeout=self._timeout,
                )
                response.raise_for_status()
                return parse_yahoo_chart(response.json(), symbol, self.name)
            except (requests.RequestException, ValueError, QuoteError) as exc:
                last_error = exc
        raise QuoteError(f"{self.name} fiyat vermedi: {last_error}")


class IsYatirimProvider:
    """İş Yatırım public daily BIST data (unofficial, daily close)."""

    name = "İş Yatırım"
    url = "https://www.isyatirim.com.tr/_layouts/15/Isyatirim.Website/Common/Data.aspx/HisseTekil"

    def __init__(self, session: Any = None, timeout: float = REQUEST_TIMEOUT):
        self._session = session
        self._timeout = timeout

    def fetch(self, symbol: str) -> Quote:
        client = self._session or requests
        end = date.today()
        start = end - timedelta(days=10)
        try:
            response = client.get(
                self.url,
                params={
                    "hisse": symbol,
                    "startdate": start.strftime("%d-%m-%Y"),
                    "enddate": end.strftime("%d-%m-%Y"),
                },
                headers=_HEADERS,
                timeout=self._timeout,
            )
            response.raise_for_status()
            return parse_isyatirim(response.json(), symbol, self.name)
        except (requests.RequestException, ValueError) as exc:
            raise QuoteError(f"{self.name} fiyat vermedi: {exc}") from exc


# --------------------------------------------------------------------- service
@dataclass
class QuoteResult:
    quotes: dict[str, Quote] = field(default_factory=dict)
    live: list[str] = field(default_factory=list)
    cached: list[str] = field(default_factory=list)
    failed: list[str] = field(default_factory=list)

    def to_payload(self) -> dict[str, Any]:
        """Plain-dict form that is safe to send through a Qt signal."""
        return {
            "quotes": {symbol: quote.to_payload() for symbol, quote in self.quotes.items()},
            "live": list(self.live),
            "cached": list(self.cached),
            "failed": list(self.failed),
        }


def default_cache_path() -> Path:
    return app_data_directory() / "cache" / "bist_quotes.json"


class QuoteService:
    def __init__(
        self,
        providers: Iterable[QuoteProvider] | None = None,
        cache_path: str | Path | None = None,
        max_workers: int = 4,
        max_cache_age: timedelta = CACHE_MAX_AGE,
    ):
        self.providers: list[QuoteProvider] = (
            list(providers) if providers is not None
            else [YahooChartProvider(), IsYatirimProvider()]
        )
        self.cache_path = Path(cache_path) if cache_path else default_cache_path()
        self.max_workers = max(1, int(max_workers))
        self.max_cache_age = max_cache_age

    # -- cache
    def _load_cache(self) -> dict[str, dict[str, Any]]:
        entries = load_json(self.cache_path).get("quotes")
        return entries if isinstance(entries, dict) else {}

    def _cached_quote(self, symbol: str, entries: dict[str, dict[str, Any]]) -> Quote | None:
        entry = entries.get(symbol)
        if not isinstance(entry, dict):
            return None
        fetched = _parse_iso(entry.get("fetched_at"))
        if fetched is None or datetime.now(timezone.utc) - fetched > self.max_cache_age:
            return None
        try:
            quote = Quote.from_payload(symbol, entry)
        except QuoteError:
            return None
        return Quote(
            quote.symbol, quote.price, quote.as_of, quote.source, quote.fetched_at, stale=True
        )

    # -- fetching
    def fetch(self, symbols: Iterable[object]) -> QuoteResult:
        tickers: list[str] = []
        for raw in symbols:
            try:
                ticker = normalize_symbol(raw)
            except ValueError:
                log.warning("Geçersiz hisse kodu atlandı: %r", raw)
                continue
            if ticker not in tickers:
                tickers.append(ticker)

        result = QuoteResult()
        if not tickers:
            return result

        lock = threading.Lock()
        failures = {provider.name: 0 for provider in self.providers}
        successes = {provider.name: 0 for provider in self.providers}

        def fetch_one(symbol: str) -> Quote | None:
            for provider in self.providers:
                with lock:
                    # Circuit breaker: a provider that has not answered even once
                    # during this refresh is skipped after repeated failures.
                    if (
                        failures[provider.name] >= CIRCUIT_BREAKER_FAILURES
                        and successes[provider.name] == 0
                    ):
                        continue
                try:
                    quote = provider.fetch(symbol)
                except Exception as exc:
                    with lock:
                        failures[provider.name] += 1
                    log.info("%s / %s: %s", provider.name, symbol, exc)
                    continue
                with lock:
                    successes[provider.name] += 1
                return quote
            return None

        workers = min(self.max_workers, len(tickers))
        with ThreadPoolExecutor(max_workers=workers) as pool:
            fetched = list(pool.map(fetch_one, tickers))

        entries = self._load_cache()
        cache_changed = False
        for symbol, quote in zip(tickers, fetched):
            if quote is not None:
                result.quotes[symbol] = quote
                result.live.append(symbol)
                entries[symbol] = quote.to_payload()
                cache_changed = True
                continue
            stale = self._cached_quote(symbol, entries)
            if stale is not None:
                result.quotes[symbol] = stale
                result.cached.append(symbol)
            else:
                result.failed.append(symbol)

        if cache_changed:
            save_json_atomic(self.cache_path, {"version": 1, "quotes": entries})
        if result.failed or result.cached:
            log.warning(
                "BIST fiyatları: canlı=%d, önbellek=%d, alınamadı=%s",
                len(result.live), len(result.cached), result.failed,
            )
        return result


def _format_when(value: object) -> str | None:
    text = str(value or "").strip()
    if not text:
        return None
    parsed = _parse_iso(text)
    if parsed is None:
        return None
    if len(text) <= 10:  # a plain date (daily close)
        return parsed.strftime("%d.%m.%Y")
    return parsed.astimezone().strftime("%d.%m.%Y %H:%M")


def describe_quote(quote: Quote) -> str:
    """Short human text for exports/tooltips, e.g. 'Yahoo Finance · 13.11.2026 10:00'."""
    when = _format_when(quote.as_of) or _format_when(quote.fetched_at)
    text = quote.source + (f" · {when}" if when else "")
    return text + " (eski fiyat)" if quote.stale else text


def fetch_bist_quotes(symbols: Iterable[object], service: QuoteService | None = None) -> dict[str, Any]:
    """Fetch quotes and return a signal-safe payload dictionary."""
    return (service or QuoteService()).fetch(symbols).to_payload()


def quotes_from_payload(payload: dict[str, Any] | None) -> dict[str, Quote]:
    """Rebuild Quote objects from ``QuoteResult.to_payload()['quotes']`` safely."""
    quotes: dict[str, Quote] = {}
    entries = (payload or {}).get("quotes") if isinstance(payload, dict) else None
    if not isinstance(entries, dict):
        return quotes
    for symbol, data in entries.items():
        try:
            quotes[str(symbol)] = Quote.from_payload(str(symbol), data)
        except (QuoteError, AttributeError, TypeError):
            continue
    return quotes
