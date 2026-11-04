from __future__ import annotations

from pathlib import Path
import unicodedata
from typing import Any

from openpyxl import load_workbook

from features.investment_excel import read_investment_holdings_excel
from features.bist.excel_io import read_portfolio_excel


def _normalise_sheet_name(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    return text.lower().replace("ı", "i").replace("İ", "i").replace(" ", "")


SHEET_ALIASES = {
    "currency": {"doviz", "currency", "currencies"},
    "metals": {"maden", "metals", "metal"},
    "bist": {"hissesenedi", "bistportfoy", "bistai"},
}


def read_combined_portfolio_excel(
    path: str | Path,
    *,
    currency_assets: dict[str, tuple[str, str]],
    metal_assets: dict[str, tuple[str, str]],
) -> dict[str, Any]:
    """Read all supported investment sections from a FinanceTerminal workbook.

    Missing sections are returned as empty lists and are left untouched by the caller.
    Matching assets are imported as snapshots (replace), never added as new purchases.
    """
    source = Path(path)
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        available = {
            _normalise_sheet_name(sheet.title)
            for sheet in workbook.worksheets
        }
    finally:
        workbook.close()

    found: dict[str, bool] = {
        section: bool(available.intersection(aliases))
        for section, aliases in SHEET_ALIASES.items()
    }
    if not any(found.values()):
        raise ValueError(
            "Dosyada tanınan portföy sayfası bulunamadı. Beklenen sayfalar: "
            "Döviz, Maden ve Hisse Senedi."
        )

    result: dict[str, Any] = {
        "currency": [],
        "metals": [],
        "bist": [],
        "warnings": [],
        "found_sheets": [name for name, present in found.items() if present],
    }

    if found["currency"]:
        rows = read_investment_holdings_excel(
            source, asset_group="currency", allowed_assets=currency_assets
        )
        result["currency"] = rows
        for row in rows:
            result["warnings"].extend(row.get("_import_errors", []))

    if found["metals"]:
        rows = read_investment_holdings_excel(
            source, asset_group="metals", allowed_assets=metal_assets
        )
        result["metals"] = rows
        for row in rows:
            result["warnings"].extend(row.get("_import_errors", []))

    if found["bist"]:
        result["bist"] = read_portfolio_excel(source)

    # Preserve warning order while removing repeated parser diagnostics.
    result["warnings"] = list(dict.fromkeys(result["warnings"]))
    return result


def apply_combined_portfolio_import(
    imported_data: dict[str, Any],
    *,
    currency_store,
    metal_store,
    bist_database,
) -> tuple[dict[str, int], list[str]]:
    """Apply a parsed workbook snapshot to the three local portfolio stores."""
    counts = {"currency": 0, "metals": 0, "bist": 0}
    errors: list[str] = []

    for group, store in (("currency", currency_store), ("metals", metal_store)):
        for row in imported_data.get(group, []):
            try:
                store.set_holding(
                    group,
                    row["asset_code"],
                    row["quantity"],
                    row["average_cost"],
                    display_name=row["display_name"],
                    unit=row["unit"],
                )
                counts[group] += 1
            except Exception as exc:
                errors.append(f"{group} / {row.get('asset_code', '?')}: {exc}")

    bist_rows = imported_data.get("bist", [])
    if bist_rows:
        counts["bist"], bist_errors = bist_database.import_rows(bist_rows)
        errors.extend(f"BIST: {item}" for item in bist_errors)

    return counts, errors
