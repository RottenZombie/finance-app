from __future__ import annotations

from decimal import Decimal
from typing import Any

from features.investment_store import format_localized


def current_market_total(
    holdings: list[dict[str, Any]], prices: dict[str, Decimal | None],
) -> Decimal | None:
    """Return a group's current TRY value, or None when a held asset has no quote."""
    total = Decimal("0")
    for holding in holdings:
        price = prices.get(str(holding.get("asset_code", "")))
        if price is None or Decimal(str(price)) <= 0:
            return None
        total += Decimal(str(holding["quantity"])) * Decimal(str(price))
    return total


def cost_total(holdings: list[dict[str, Any]], *, average_cost_key: str) -> Decimal:
    return sum(
        (Decimal(str(row["quantity"])) * Decimal(str(row[average_cost_key])) for row in holdings),
        Decimal("0"),
    )


def group_profit_loss(
    holdings: list[dict[str, Any]],
    prices: dict[str, Decimal | None],
    *,
    average_cost_key: str,
) -> Decimal | None:
    """Calculate unrealized P/L only when every held asset has a valid quote."""
    if not holdings:
        return Decimal("0")
    market_value = current_market_total(holdings, prices)
    if market_value is None:
        return None
    return market_value - cost_total(holdings, average_cost_key=average_cost_key)


def bist_cost_total(holdings: list[dict[str, Any]]) -> Decimal:
    """Total recorded acquisition cost of the BIST holdings."""
    return cost_total(holdings, average_cost_key="average_cost")


def _bist_price(prices: dict[str, Decimal | None] | None, holding: dict[str, Any]) -> Decimal | None:
    if not prices:
        return None
    value = prices.get(str(holding.get("symbol", "")))
    try:
        price = Decimal(str(value)) if value is not None else None
    except Exception:
        return None
    return price if price is not None and price.is_finite() and price > 0 else None


def bist_priced_result(
    holdings: list[dict[str, Any]], prices: dict[str, Decimal | None] | None
) -> tuple[Decimal | None, list[str]]:
    """Return (profit/loss of the priced holdings or None, symbols without a price)."""
    profit_loss = Decimal("0")
    priced = 0
    missing: list[str] = []
    for holding in holdings:
        price = _bist_price(prices, holding)
        if price is None:
            symbol = str(holding.get("symbol", "")).strip()
            if symbol:
                missing.append(symbol)
            continue
        quantity = Decimal(str(holding["quantity"]))
        profit_loss += quantity * (price - Decimal(str(holding["average_cost"])))
        priced += 1
    return (profit_loss if priced else None), missing


def bist_value_and_coverage(
    holdings: list[dict[str, Any]], prices: dict[str, Decimal | None] | None
) -> tuple[Decimal, str]:
    """Return (TRY value, coverage) for the BIST group.

    coverage is "empty" (no holdings), "full" (every holding has a quote),
    "partial" (some do) or "none" (no quotes: value is the recorded cost).
    A holding without a quote is valued at its recorded cost, never guessed.
    """
    if not holdings:
        return Decimal("0"), "empty"
    total = Decimal("0")
    priced = 0
    for holding in holdings:
        quantity = Decimal(str(holding["quantity"]))
        price = _bist_price(prices, holding)
        if price is None:
            total += quantity * Decimal(str(holding["average_cost"]))
        else:
            total += quantity * price
            priced += 1
    if priced == 0:
        return total, "none"
    return total, "full" if priced == len(holdings) else "partial"


def convert_try_total(
    try_value: Decimal | None,
    *,
    try_per_eur: Decimal | None,
    try_per_usd: Decimal | None,
) -> dict[str, str]:
    if try_value is None:
        return {"TRY": "Veri yok", "EUR": "Veri yok", "USD": "Veri yok"}
    return {
        "TRY": format_localized(try_value),
        "EUR": format_localized(try_value / try_per_eur)
        if try_per_eur is not None and try_per_eur > 0 else "Kur yok",
        "USD": format_localized(try_value / try_per_usd)
        if try_per_usd is not None and try_per_usd > 0 else "Kur yok",
    }


def calculate_portfolio_totals(
    *,
    currency_holdings: list[dict[str, Any]],
    currency_prices: dict[str, Decimal | None],
    metal_holdings: list[dict[str, Any]],
    metal_prices: dict[str, Decimal | None],
    bist_holdings: list[dict[str, Any]],
    bist_prices: dict[str, Decimal | None] | None = None,
) -> dict[str, Any]:
    currency = current_market_total(currency_holdings, currency_prices)
    metals = current_market_total(metal_holdings, metal_prices)
    bist, bist_coverage = bist_value_and_coverage(bist_holdings, bist_prices)
    grand = None if currency is None or metals is None else currency + metals + bist

    currency_pl = group_profit_loss(
        currency_holdings, currency_prices, average_cost_key="average_cost_try"
    )
    metals_pl = group_profit_loss(
        metal_holdings, metal_prices, average_cost_key="average_cost_try"
    )
    # BIST P/L covers the holdings that have a current quote; the ones without a
    # quote are reported in "bist_missing" so the UI can warn instead of hiding all.
    bist_priced_pl, bist_missing = bist_priced_result(bist_holdings, bist_prices)
    bist_pl: Decimal | None = Decimal("0") if bist_coverage == "empty" else bist_priced_pl
    total_pl = (
        currency_pl + metals_pl
        if currency_pl is not None and metals_pl is not None
        else None
    )
    if total_pl is not None and bist_coverage in ("full", "partial") and bist_pl is not None:
        total_pl += bist_pl
    return {
        "currency": currency,
        "metals": metals,
        "bist": bist,
        "total": grand,
        "currency_profit_loss": currency_pl,
        "metals_profit_loss": metals_pl,
        "bist_profit_loss": bist_pl,
        "bist_coverage": bist_coverage,
        "bist_missing": bist_missing,
        "total_profit_loss": total_pl,
    }
