"""Sample-template workbooks for every Excel export.

A template is the normal export file filled with one example row per sheet, so
the user can see the exact layout, replace the example with their own data and
load it back with "Excel'den İçe Aktar". No real portfolio data is used.
"""
from __future__ import annotations

from decimal import Decimal
from pathlib import Path
from typing import Any

from features.bist.excel_io import write_portfolio_excel
from features.investment_excel import write_combined_portfolio_excel
from features.investment_store import write_holdings_excel

TEMPLATE_STATUS = "Örnek şablon (gerçek veri değildir)"

# (asset code, quantity, average cost in TRY, sample current price in TRY)
_SAMPLES = {
    "currency": ("USD", "100", "30", "35"),
    "metals": ("XAU", "10", "2800", "3000"),
}
_TITLES = {"currency": "Döviz Portföyü", "metals": "Metal Portföyü"}

SAMPLE_BIST_HOLDING: dict[str, Any] = {
    "symbol": "ASELS",
    "company": "Aselsan Elektronik",
    "quantity": "10",
    "average_cost": "75.50",
    "sector": "Savunma",
    "notes": "Örnek kayıt - kendi verinizle değiştirin",
}
SAMPLE_BIST_PRICE = Decimal("80")
SAMPLE_BIST_NOTE = "Örnek fiyat"


def template_filename(filename: str) -> str:
    """``X.xlsx`` -> ``X_Ornek_Sablon.xlsx``."""
    path = Path(filename)
    return f"{path.stem}_Ornek_Sablon{path.suffix or '.xlsx'}"


def _sample_holding(asset_group: str, assets: dict[str, tuple[str, str]]) -> tuple[dict[str, Any], Decimal]:
    code, quantity, cost, price = _SAMPLES[asset_group]
    if code not in assets:  # defensive: fall back to the first supported asset
        code = next(iter(assets))
    name, unit = assets[code]
    holding = {
        "asset_code": code, "display_name": name, "unit": unit,
        "quantity": quantity, "average_cost_try": cost,
    }
    return holding, Decimal(price)


def write_investment_template(
    path: str | Path, asset_group: str, assets: dict[str, tuple[str, str]]
) -> None:
    """Currency or metals template: the normal export with one example row."""
    if asset_group not in _SAMPLES:
        raise ValueError("Geçersiz portföy türü.")
    holding, price = _sample_holding(asset_group, assets)
    write_holdings_excel(
        path, [holding], {holding["asset_code"]: price},
        title=_TITLES[asset_group],
        rates_updated_at=TEMPLATE_STATUS, rates_status=TEMPLATE_STATUS,
    )


def write_bist_template(path: str | Path) -> None:
    write_portfolio_excel(
        path, [dict(SAMPLE_BIST_HOLDING)],
        prices={SAMPLE_BIST_HOLDING["symbol"]: SAMPLE_BIST_PRICE},
        price_notes={SAMPLE_BIST_HOLDING["symbol"]: SAMPLE_BIST_NOTE},
        rates_updated_at=TEMPLATE_STATUS, rates_status=TEMPLATE_STATUS,
    )


def write_combined_template(
    path: str | Path,
    currency_assets: dict[str, tuple[str, str]],
    metal_assets: dict[str, tuple[str, str]],
) -> None:
    """All-in-one template: Summary, Döviz, Maden, Hisse Senedi with one example each."""
    currency, currency_price = _sample_holding("currency", currency_assets)
    metal, metal_price = _sample_holding("metals", metal_assets)
    symbol = SAMPLE_BIST_HOLDING["symbol"]
    write_combined_portfolio_excel(
        path,
        currency_holdings=[currency],
        currency_prices={currency["asset_code"]: currency_price},
        metal_holdings=[metal],
        metal_prices={metal["asset_code"]: metal_price},
        bist_holdings=[dict(SAMPLE_BIST_HOLDING)],
        try_per_usd=Decimal("35"),
        try_per_eur=Decimal("38"),
        bist_prices={symbol: SAMPLE_BIST_PRICE},
        bist_price_notes={symbol: SAMPLE_BIST_NOTE},
        rates_updated_at=TEMPLATE_STATUS,
        rates_status=TEMPLATE_STATUS,
    )
