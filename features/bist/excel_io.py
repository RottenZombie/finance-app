from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from decimal import Decimal
from typing import Any, Mapping

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

from features.export_metadata import add_export_metadata_sheet, local_timestamp
from .valuation import value_holdings
from core.i18n import tr


def headers() -> list[str]:
    """Columns the importer understands (names follow the active language)."""
    return [
        tr("Hisse Kodu"), tr("Şirket Adı"), tr("Adet"), tr("Ortalama Maliyet (TL)"),
        tr("Toplam Maliyet (TL)"), tr("Sektör"), tr("Notlar"),
    ]


def export_headers() -> list[str]:
    """The export adds price/profit-loss columns after the import columns.

    The reader only looks columns up by header name, so these extra columns never
    affect import.
    """
    return headers() + [
        tr("Güncel Fiyat (TL)"), tr("Güncel Değer (TL)"), tr("Kâr / Zarar (TL)"),
        tr("Kâr / Zarar (%)"), tr("Fiyat Kaynağı / Zamanı"),
    ]


def _normalise_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("ı", "i")
    return re.sub(r"[^a-z0-9]", "", text)


ALIASES = {
    "symbol": {"hissekodu", "sembol", "hisse", "kod", "ticker", "symbol"},
    "company": {"sirketadi", "sirket", "company", "name"},
    "quantity": {"adet", "lot", "miktar", "quantity", "shares"},
    "average_cost": {
        "ortalamamaliyettl", "ortalamamaliyet", "maliyet", "alismaliyeti",
        "averagecost", "averagecosttry", "cost", "avgcost",
    },
    "sector": {"sektor", "sector"},
    "notes": {"notlar", "not", "aciklama", "notes", "description"},
}


def read_portfolio_excel(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = None
        mapping: dict[str, int] = {}
        required = {"symbol", "quantity", "average_cost"}
        # Combined FinanceTerminal workbooks have Summary as the first sheet.
        # Scan sheets and select the first one that actually contains BIST columns.
        for candidate in workbook.worksheets:
            headers = next(candidate.iter_rows(min_row=1, max_row=1, values_only=True), None)
            candidate_mapping: dict[str, int] = {}
            for index, header in enumerate(headers or []):
                normalised = _normalise_header(header)
                for field, aliases in ALIASES.items():
                    if normalised in aliases:
                        candidate_mapping[field] = index
                        break
            if required.issubset(candidate_mapping):
                sheet = candidate
                mapping = candidate_mapping
                if _normalise_header(candidate.title) in {"hissesenedi", "bistportfoy", "bistportfolio", "stocks"}:
                    break

        if sheet is None:
            names = {"symbol": tr("Hisse Kodu"), "quantity": tr("Adet"), "average_cost": tr("Ortalama Maliyet")}
            raise ValueError(tr("Gerekli BIST sütunlarını içeren sayfa bulunamadı: ") + ", ".join(names[item] for item in required))

        iterator = sheet.iter_rows(min_row=2, values_only=True)
        results: list[dict[str, Any]] = []
        for row in iterator:
            if not row or all(value is None or str(value).strip() == "" for value in row):
                continue

            def cell(field: str, default: object = "") -> object:
                index = mapping.get(field)
                return row[index] if index is not None and index < len(row) and row[index] is not None else default

            # Ignore summary/footer rows that do not contain a ticker.
            if cell("symbol", None) in (None, ""):
                continue

            results.append(
                {
                    "symbol": cell("symbol"),
                    "company": cell("company"),
                    "quantity": cell("quantity"),
                    "average_cost": cell("average_cost"),
                    "sector": cell("sector"),
                    "notes": cell("notes"),
                }
            )
        return results
    finally:
        workbook.close()


def write_portfolio_excel(
    path: str | Path, holdings: list[dict[str, Any]], *,
    prices: Mapping[str, Decimal] | None = None,
    price_notes: Mapping[str, str] | None = None,
    rates_updated_at: str | None = None, rates_status: str | None = None
) -> None:
    """Export the BIST portfolio as a point-in-time view.

    ``prices`` are the current quotes at export time (symbol -> TRY price) and
    ``price_notes`` say where/when each came from. Profit/loss covers the holdings
    that have a price; holdings without one are named in a warning row and are
    never guessed.
    """
    valuation = value_holdings(holdings, prices)
    notes = price_notes or {}
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = tr("BIST Portföy")
    sheet.append(export_headers())

    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center", wrap_text=True)

    for holding, row in zip(holdings, valuation["rows"]):
        price = row["price"]
        sheet.append(
            [
                holding["symbol"],
                holding.get("company", ""),
                float(row["quantity"]),
                float(row["average_cost"]),
                float(row["cost"]),
                holding.get("sector", ""),
                holding.get("notes", ""),
                float(price) if price is not None else None,
                float(row["market_value"]) if row["market_value"] is not None else None,
                float(row["profit_loss"]) if row["profit_loss"] is not None else None,
                float(row["profit_loss_pct"]) if row["profit_loss_pct"] is not None else None,
                notes.get(row["symbol"]) or (tr("Fiyat alınamadı") if price is None else ""),
            ]
        )

    # Footer rows carry no ticker in column A, so the importer skips them.
    footer = sheet.max_row + 2

    def footer_line(label: str, value: object = None, number_format: str | None = None) -> None:
        nonlocal footer
        sheet.cell(footer, 4, label).font = Font(bold=True)
        if value is not None:
            cell = sheet.cell(footer, 5, value)
            cell.font = Font(bold=True)
            if number_format:
                cell.number_format = number_format
        footer += 1

    footer_line(tr("Toplam Maliyet"), float(valuation["total_cost"]), "#,##0.00")
    if valuation["market_value"] is not None:
        footer_line(tr("Güncel Değer (fiyatı alınan hisseler)"), float(valuation["market_value"]), "#,##0.00")
        footer_line(tr("Kâr / Zarar (TL)"), float(valuation["profit_loss"]), "#,##0.00")
        if valuation["profit_loss_pct"] is not None:
            footer_line(tr("Kâr / Zarar (%)"), float(valuation["profit_loss_pct"]), '0.00"%"')
    if valuation["missing"]:
        footer_line(
            tr("⚠ Fiyatı alınamayan hisseler: ") + ", ".join(valuation["missing"])
            + tr(" (kâr/zarar yalnızca fiyatı alınan hisseleri kapsar)")
        )
    footer_line(tr("Hesaplama zamanı"), local_timestamp())

    for row in sheet.iter_rows(min_row=2, max_row=1 + len(holdings)):
        for cell in row:
            if cell.column in (4, 5, 8, 9, 10) and isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.00'
            elif cell.column == 3 and isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.####'
            elif cell.column == 11 and isinstance(cell.value, (int, float)):
                cell.number_format = '0.00"%"'

    widths = [16, 26, 14, 22, 22, 20, 36, 18, 18, 18, 14, 34]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:L{max(1, len(holdings) + 1)}"

    add_export_metadata_sheet(
        workbook, rates_updated_at=rates_updated_at, rates_status=rates_status
    )
    workbook.active = 0
    workbook.save(path)
    workbook.close()
