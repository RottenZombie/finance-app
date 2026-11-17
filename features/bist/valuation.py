"""Pure (Qt-free) BIST holding valuation against current quotes."""
from __future__ import annotations

from decimal import Decimal
from typing import Any, Mapping


def _valid_price(value: object) -> Decimal | None:
    if value is None:
        return None
    try:
        price = Decimal(str(value))
    except Exception:
        return None
    return price if price.is_finite() and price > 0 else None


def value_holdings(
    holdings: list[dict[str, Any]], prices: Mapping[str, Decimal | None] | None
) -> dict[str, Any]:
    """Return per-row and total valuation.

    ``market_value`` and ``profit_loss`` cover only the holdings that have a
    price; ``missing`` names the others and ``complete`` tells the caller whether
    the figures describe the whole portfolio. Nothing is guessed for a holding
    without a price.
    """
    prices = prices or {}
    rows: list[dict[str, Any]] = []
    total_cost = Decimal("0")
    priced_value = Decimal("0")
    priced_cost = Decimal("0")
    missing: list[str] = []

    for holding in holdings:
        symbol = str(holding.get("symbol", ""))
        quantity = Decimal(str(holding["quantity"]))
        average_cost = Decimal(str(holding["average_cost"]))
        cost = quantity * average_cost
        total_cost += cost
        price = _valid_price(prices.get(symbol))
        row: dict[str, Any] = {
            "symbol": symbol, "quantity": quantity, "average_cost": average_cost,
            "cost": cost, "price": price, "market_value": None,
            "profit_loss": None, "profit_loss_pct": None,
        }
        if price is None:
            missing.append(symbol)
        else:
            market_value = quantity * price
            row["market_value"] = market_value
            row["profit_loss"] = market_value - cost
            row["profit_loss_pct"] = ((market_value - cost) / cost * 100) if cost > 0 else None
            priced_value += market_value
            priced_cost += cost
        rows.append(row)

    priced_count = len(rows) - len(missing)
    complete = bool(rows) and not missing
    # Profit/loss covers the holdings that have a price. Holdings without a price
    # are listed in ``missing`` (the UI warns about them) and never guessed.
    profit_loss = priced_value - priced_cost if priced_count else None
    profit_loss_pct = (
        profit_loss / priced_cost * 100
        if profit_loss is not None and priced_cost > 0 else None
    )
    return {
        "rows": rows,
        "total_cost": total_cost,
        "market_value": priced_value if priced_count else None,
        "priced_count": priced_count,
        "holding_count": len(rows),
        "missing": missing,
        "complete": complete,
        "profit_loss": profit_loss,
        "profit_loss_pct": profit_loss_pct,
    }
