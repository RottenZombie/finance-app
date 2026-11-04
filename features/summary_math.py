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
    """BIST is still cost-based until live quote support is added."""
    return cost_total(holdings, average_cost_key="average_cost")


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
) -> dict[str, Decimal | None]:
    currency = current_market_total(currency_holdings, currency_prices)
    metals = current_market_total(metal_holdings, metal_prices)
    bist = bist_cost_total(bist_holdings)
    grand = None if currency is None or metals is None else currency + metals + bist

    currency_pl = group_profit_loss(
        currency_holdings, currency_prices, average_cost_key="average_cost_try"
    )
    metals_pl = group_profit_loss(
        metal_holdings, metal_prices, average_cost_key="average_cost_try"
    )
    # BIST has no live quote source yet, so its unrealized P/L must not be guessed.
    total_pl = (
        currency_pl + metals_pl
        if currency_pl is not None and metals_pl is not None
        else None
    )
    return {
        "currency": currency,
        "metals": metals,
        "bist": bist,
        "total": grand,
        "currency_profit_loss": currency_pl,
        "metals_profit_loss": metals_pl,
        "bist_profit_loss": None if bist_holdings else Decimal("0"),
        "total_profit_loss": total_pl,
    }
