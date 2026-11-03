from __future__ import annotations

from pathlib import Path
import re
import unicodedata
from decimal import Decimal
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter


HEADERS = [
    "Hisse Kodu",
    "Şirket Adı",
    "Adet",
    "Ortalama Maliyet (TL)",
    "Toplam Maliyet (TL)",
    "Sektör",
    "Notlar",
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
        "averagecost", "cost", "avgcost",
    },
    "sector": {"sektor", "sector"},
    "notes": {"notlar", "not", "aciklama", "notes", "description"},
}


def read_portfolio_excel(path: str | Path) -> list[dict[str, Any]]:
    source = Path(path)
    workbook = load_workbook(source, read_only=True, data_only=True)
    try:
        sheet = workbook.active
        iterator = sheet.iter_rows(values_only=True)
        headers = next(iterator, None)
        if not headers:
            raise ValueError("Excel dosyası boş.")

        mapping: dict[str, int] = {}
        for index, header in enumerate(headers):
            normalised = _normalise_header(header)
            for field, aliases in ALIASES.items():
                if normalised in aliases:
                    mapping[field] = index
                    break

        missing = [field for field in ("symbol", "quantity", "average_cost") if field not in mapping]
        if missing:
            names = {"symbol": "Hisse Kodu", "quantity": "Adet", "average_cost": "Ortalama Maliyet"}
            raise ValueError("Gerekli sütunlar bulunamadı: " + ", ".join(names[item] for item in missing))

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


def write_portfolio_excel(path: str | Path, holdings: list[dict[str, Any]]) -> None:
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "BIST Portföy"
    sheet.append(HEADERS)

    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="1F4E78")
        cell.alignment = Alignment(horizontal="center")

    total = Decimal("0")
    for holding in holdings:
        quantity = Decimal(str(holding["quantity"]))
        average_cost = Decimal(str(holding["average_cost"]))
        cost_total = quantity * average_cost
        total += cost_total
        sheet.append(
            [
                holding["symbol"],
                holding.get("company", ""),
                float(quantity),
                float(average_cost),
                float(cost_total),
                holding.get("sector", ""),
                holding.get("notes", ""),
            ]
        )

    summary_row = sheet.max_row + 2
    sheet.cell(summary_row, 4, "Toplam Maliyet")
    sheet.cell(summary_row, 5, float(total))
    sheet.cell(summary_row, 4).font = Font(bold=True)
    sheet.cell(summary_row, 5).font = Font(bold=True)

    for row in sheet.iter_rows(min_row=2, max_row=sheet.max_row):
        for cell in row:
            if cell.column in (4, 5) and isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.00'
            elif cell.column == 3 and isinstance(cell.value, (int, float)):
                cell.number_format = '#,##0.####'

    widths = [16, 26, 14, 22, 22, 20, 36]
    for index, width in enumerate(widths, start=1):
        sheet.column_dimensions[get_column_letter(index)].width = width
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = f"A1:G{max(1, len(holdings) + 1)}"

    workbook.save(path)
    workbook.close()
