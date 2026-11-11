from __future__ import annotations

from typing import Any

import requests

from features.currencies import CURRENCY_INFO

API = "https://open.er-api.com/v6/latest"


def get_all_rates() -> dict[str, Any]:
    """Return TRY prices for supported currencies using the provider's USD base.

    The provider returns the number of foreign-currency units per one USD.
    Dividing USD/TRY by that rate gives the TRY value of one unit of each
    foreign currency. TRY itself is always exactly 1 TRY.
    """
    empty = {code: None for code in CURRENCY_INFO}
    empty.update({"TRY": 1.0, "status": "Offline"})
    try:
        response = requests.get(f"{API}/USD", timeout=8)
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
    except (requests.RequestException, ValueError, TypeError, KeyError):
        return empty
    except Exception:
        # An unexpected provider response must not stop the rest of the app.
        return empty


def get_metal_prices() -> tuple[float, float]:
    try:
        gold_response = requests.get("https://api.gold-api.com/price/XAU", timeout=8)
        silver_response = requests.get("https://api.gold-api.com/price/XAG", timeout=8)
        gold_response.raise_for_status()
        silver_response.raise_for_status()
        gold = gold_response.json()
        silver = silver_response.json()
        gold_price = gold.get("price", 0)
        silver_price = silver.get("price", 0)
        return float(gold_price or 0), float(silver_price or 0)
    except Exception:
        return 0.0, 0.0
