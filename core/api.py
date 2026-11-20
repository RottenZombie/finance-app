from __future__ import annotations

import math
import xml.etree.ElementTree as ET
from typing import Any

import requests

from core.log_setup import get_logger
from features.currencies import CURRENCY_INFO
from core.i18n import tr

log = get_logger("api")

API = "https://open.er-api.com/v6/latest"
# Official Turkish central bank daily rates: free, keyless and very stable.
# It is used only as a fallback when the primary provider is unavailable.
TCMB_URL = "https://www.tcmb.gov.tr/kurlar/today.xml"
METAL_URL = "https://api.gold-api.com/price/{symbol}"
REQUEST_TIMEOUT = 8
MAX_XML_BYTES = 1_000_000
HEADERS = {"User-Agent": "FinanceTerminal/2.4 (+https://github.com/RottenZombie/finance-app)"}


def _offline_result() -> dict[str, Any]:
    empty: dict[str, Any] = {code: None for code in CURRENCY_INFO}
    empty.update({"TRY": 1.0, "status": "Offline"})
    return empty


def _fetch_open_er_api() -> dict[str, Any]:
    """Primary provider. Returns the number of TRY per one foreign-currency unit.

    The provider returns foreign-currency units per one USD, so dividing USD/TRY
    by that rate gives the TRY value of one unit of each foreign currency.
    """
    response = requests.get(f"{API}/USD", timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    data = response.json()
    rates = data.get("rates") or {}
    usd_try = rates.get("TRY")
    if not isinstance(usd_try, (int, float)) or usd_try <= 0:
        raise ValueError("Kur sağlayıcısından USD/TRY bilgisi alınamadı.")

    result: dict[str, Any] = {"TRY": 1.0, "USD": float(usd_try)}
    for code in CURRENCY_INFO:
        if code == "USD":
            continue
        foreign_per_usd = rates.get(code)
        if isinstance(foreign_per_usd, (int, float)) and foreign_per_usd > 0:
            result[code] = float(usd_try) / float(foreign_per_usd)
        else:
            result[code] = None
    result["status"] = "Online"
    return result


def parse_tcmb_xml(content: bytes) -> dict[str, float]:
    """Parse TCMB ``today.xml`` into {currency: TRY per one unit}.

    The mid value of ForexBuying/ForexSelling is used and the quoted ``Unit``
    (for example 100 for JPY) is divided out.
    """
    if len(content) > MAX_XML_BYTES:
        raise ValueError("TCMB yanıtı beklenenden büyük.")
    lowered = content.lower()
    # Refuse DTD/entity declarations (entity-expansion attacks); TCMB sends none.
    if b"<!doctype" in lowered or b"<!entity" in lowered:
        raise ValueError("TCMB yanıtında izin verilmeyen XML tanımı var.")
    root = ET.fromstring(content)

    rates: dict[str, float] = {}
    for node in root.iter("Currency"):
        code = str(node.get("Kod") or node.get("CurrencyCode") or "").strip().upper()
        if code not in CURRENCY_INFO or code == "TRY":
            continue
        try:
            unit = float((node.findtext("Unit") or "1").strip())
            values = [
                float(text.strip())
                for text in (node.findtext("ForexBuying"), node.findtext("ForexSelling"))
                if text and text.strip()
            ]
        except ValueError:
            continue
        values = [value for value in values if math.isfinite(value) and value > 0]
        if not values or unit <= 0:
            continue
        rates[code] = (sum(values) / len(values)) / unit
    return rates


def _fetch_tcmb() -> dict[str, Any]:
    response = requests.get(TCMB_URL, timeout=REQUEST_TIMEOUT, headers=HEADERS)
    response.raise_for_status()
    rates = parse_tcmb_xml(response.content)
    if "USD" not in rates:
        raise ValueError("TCMB yanıtında USD/TRY bulunamadı.")
    result: dict[str, Any] = {"TRY": 1.0}
    for code in CURRENCY_INFO:
        result[code] = rates.get(code)
    result["status"] = tr("Online (TCMB yedek)")
    return result


def get_all_rates() -> dict[str, Any]:
    """Return TRY prices for supported currencies.

    Providers are tried in order; the first usable answer wins. TRY itself is
    always exactly 1 TRY. If every provider fails an "Offline" result with the
    expected keys is returned so the rest of the app keeps working.
    """
    for name, fetch in (("open.er-api.com", _fetch_open_er_api), ("TCMB", _fetch_tcmb)):
        try:
            return fetch()
        except Exception:
            # An unexpected provider response must not stop the rest of the app.
            log.warning("Kur sağlayıcısı başarısız: %s", name, exc_info=True)
    return _offline_result()


def _fetch_metal(symbol: str) -> float | None:
    try:
        response = requests.get(
            METAL_URL.format(symbol=symbol), timeout=REQUEST_TIMEOUT, headers=HEADERS
        )
        response.raise_for_status()
        price = float(response.json().get("price") or 0)
        return price if math.isfinite(price) and price > 0 else None
    except Exception:
        log.warning("Maden fiyatı alınamadı: %s", symbol, exc_info=True)
        return None


def get_metal_prices() -> tuple[float | None, float | None]:
    """Return (gold, silver) in USD per troy ounce; ``None`` when unavailable."""
    return _fetch_metal("XAU"), _fetch_metal("XAG")
