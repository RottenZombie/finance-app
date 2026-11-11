from __future__ import annotations

from decimal import Decimal
from pathlib import Path
import re
import unicodedata
from typing import Any

from openpyxl import Workbook, load_workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from features.export_metadata import add_export_metadata_sheet
from features.investment_store import format_localized, parse_localized_decimal


def _normalise_header(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or ""))
    text = "".join(ch for ch in text if not unicodedata.combining(ch))
    text = text.lower().replace("ı", "i")
    return re.sub(r"[^a-z0-9]", "", text)


HEADER_ALIASES = {
    "asset_code": {"kod", "varlikkodu", "assetcode", "code", "symbol"},
    "quantity": {"miktar", "adet", "quantity", "amount"},
    "average_cost": {
        "ortalamaalisfiyatitl", "ortalamaalisfiyati", "ortalamaalis", "ortalamaalisfiyat",
        "ortalamaaliyat", "ortalamaalisfiyattry",
        "averagecosttry", "averagecost", "avgcost", "unitcosttry", "birimfiyat",
    },
}


def _sheet_header_map(sheet) -> dict[str, int]:
    headers = next(sheet.iter_rows(min_row=1, max_row=1, values_only=True), None)
    if not headers:
        return {}
    mapping: dict[str, int] = {}
    for index, header in enumerate(headers):
        normalised = _normalise_header(header)
        for field, aliases in HEADER_ALIASES.items():
            if normalised in aliases:
                mapping[field] = index
                break
    return mapping


def read_investment_holdings_excel(
    path: str | Path,
    *,
    asset_group: str,
    allowed_assets: dict[str, tuple[str, str]],
) -> list[dict[str, Any]]:
    """Read a standalone or combined FinanceTerminal workbook for one asset group.

    Existing matching asset rows are imported as snapshots (replace), not as new purchases,
    so importing the same workbook twice never doubles quantities.
    """
    group = str(asset_group).strip().lower()
    preferred = {
        "currency": {"doviz", "dovizportfoyu", "currency", "currencies"},
        "metals": {"maden", "metalportfoyu", "metals", "metal"},
    }.get(group)
    if preferred is None:
        raise ValueError("Geçersiz portföy türü.")

    workbook = load_workbook(Path(path), read_only=True, data_only=True)
    try:
        selected_sheet = None
        selected_map: dict[str, int] = {}
        for sheet in workbook.worksheets:
            mapping = _sheet_header_map(sheet)
            if not {"asset_code", "quantity", "average_cost"}.issubset(mapping):
                continue
            if _normalise_header(sheet.title) in preferred:
                selected_sheet, selected_map = sheet, mapping
                break
            if selected_sheet is None:
                selected_sheet, selected_map = sheet, mapping
        if selected_sheet is None:
            raise ValueError("Uygun portföy sayfası veya gerekli sütunlar bulunamadı.")

        aggregated: dict[str, dict[str, Any]] = {}
        errors: list[str] = []
        for row_number, row in enumerate(selected_sheet.iter_rows(min_row=2, values_only=True), start=2):
            if not row or all(value is None or str(value).strip() == "" for value in row):
                continue
            code_index = selected_map["asset_code"]
            code = str(row[code_index] or "").strip().upper() if code_index < len(row) else ""
            if not code:
                continue
            if code not in allowed_assets:
                errors.append(f"Satır {row_number}: Bu bölümde desteklenmeyen varlık kodu: {code}")
                continue
            try:
                quantity_index = selected_map["quantity"]
                cost_index = selected_map["average_cost"]
                quantity = parse_localized_decimal(row[quantity_index] if quantity_index < len(row) else None, field_name="Miktar")
                average_cost = parse_localized_decimal(row[cost_index] if cost_index < len(row) else None, field_name="Ortalama alış fiyatı")
                if quantity <= 0 or average_cost <= 0:
                    raise ValueError("Miktar ve ortalama alış fiyatı sıfırdan büyük olmalıdır.")
            except Exception as exc:
                errors.append(f"Satır {row_number}: {exc}")
                continue

            if code in aggregated:
                current = aggregated[code]
                new_quantity = current["quantity"] + quantity
                new_cost = (current["quantity"] * current["average_cost"] + quantity * average_cost) / new_quantity
                current["quantity"] = new_quantity
                current["average_cost"] = new_cost
            else:
                display_name, unit = allowed_assets[code]
                aggregated[code] = {
                    "asset_code": code,
                    "display_name": display_name,
                    "unit": unit,
                    "quantity": quantity,
                    "average_cost": average_cost,
                }

        if not aggregated and errors:
            raise ValueError("İçe aktarılabilir kayıt bulunamadı.\n" + "\n".join(errors[:10]))
        result = list(aggregated.values())
        # Keep parser diagnostics attached for the UI without breaking the row schema.
        for item in result:
            item["_import_errors"] = errors
        return result
    finally:
        workbook.close()


def _style_sheet(sheet) -> None:
    header_fill = PatternFill("solid", fgColor="203864")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    sheet.sheet_view.showGridLines = False
    for column in sheet.columns:
        max_length = max((len(str(cell.value or "")) for cell in column), default=10)
        sheet.column_dimensions[get_column_letter(column[0].column)].width = min(max(max_length + 2, 12), 30)


def _append_investment_sheet(
    workbook: Workbook,
    *,
    title: str,
    holdings: list[dict[str, Any]],
    current_prices: dict[str, Decimal | None],
) -> tuple[Decimal, Decimal | None]:
    sheet = workbook.create_sheet(title)
    sheet.append([
        "Kod", "Varlık", "Miktar", "Birim", "Ortalama Alış Fiyatı (₺)",
        "Toplam Maliyet (₺)", "Güncel Birim Fiyat (₺)", "Güncel Değer (₺)",
        "Kâr / Zarar (₺)", "Kâr / Zarar (%)",
    ])
    total_cost = Decimal("0")
    total_current_value = Decimal("0")
    all_prices_available = True
    for holding in holdings:
        quantity = Decimal(str(holding["quantity"]))
        average_cost = Decimal(str(holding.get("average_cost_try", holding.get("average_cost", "0"))))
        cost = quantity * average_cost
        total_cost += cost
        code = str(holding.get("asset_code", holding.get("symbol", "")))
        current_price = current_prices.get(code)
        if current_price is not None and current_price > 0:
            current_value = quantity * current_price
            profit = current_value - cost
            profit_pct = (profit / cost * Decimal("100")) if cost else Decimal("0")
            total_current_value += current_value
        else:
            current_value = profit = profit_pct = None
            all_prices_available = False
        sheet.append([
            code,
            holding.get("display_name", holding.get("company", "")),
            float(quantity),
            holding.get("unit", "adet"),
            float(average_cost),
            float(cost),
            float(current_price) if current_price is not None else None,
            float(current_value) if current_value is not None else None,
            float(profit) if profit is not None else None,
            float(profit_pct) if profit_pct is not None else None,
        ])
    if not holdings:
        all_prices_available = True
    _style_sheet(sheet)
    for row in sheet.iter_rows(min_row=2, min_col=5, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.00'
    for row in sheet.iter_rows(min_row=2, min_col=10, max_col=10):
        for cell in row:
            cell.number_format = '0.00"%"'
    for row in sheet.iter_rows(min_row=2, min_col=3, max_col=3):
        for cell in row:
            cell.number_format = '#,##0.####'
    return total_cost, total_current_value if all_prices_available else None


def write_combined_portfolio_excel(
    path: str | Path,
    *,
    currency_holdings: list[dict[str, Any]],
    currency_prices: dict[str, Decimal | None],
    metal_holdings: list[dict[str, Any]],
    metal_prices: dict[str, Decimal | None],
    bist_holdings: list[dict[str, Any]],
    try_per_usd: Decimal | None,
    try_per_eur: Decimal | None,
    rates_updated_at: str | None = None,
    rates_status: str | None = None,
    profile_name: str | None = None,
) -> None:
    """Create one workbook with an executive Summary followed by detailed asset sheets."""
    workbook = Workbook()
    summary = workbook.active
    summary.title = "Summary"
    summary.append(["FinanceTerminal | Portföy Özeti"])
    summary.append(["Anlık kayıt özeti. Döviz ve maden güncel fiyatları; BIST ise canlı fiyat verisi olmadığı için kayıtlı alış maliyeti üzerinden hesaplanır."])
    if profile_name:
        summary.append(["Bu dosya şu profile aittir", profile_name])
    else:
        summary.append([])
    summary.append(["Portföy", "Hesaplama Esası", "TRY", "EUR", "USD"])

    currency_cost, currency_value = _append_investment_sheet(
        workbook, title="Döviz", holdings=currency_holdings, current_prices=currency_prices
    )
    metal_cost, metal_value = _append_investment_sheet(
        workbook, title="Maden", holdings=metal_holdings, current_prices=metal_prices
    )

    bist = workbook.create_sheet("Hisse Senedi")
    bist.append([
        "Hisse Kodu", "Şirket Adı", "Adet", "Ortalama Maliyet (₺)",
        "Kayıtlı Maliyet (₺)", "Sektör", "Notlar", "Güncel Fiyat / Değer",
    ])
    bist_cost = Decimal("0")
    for holding in bist_holdings:
        quantity = Decimal(str(holding["quantity"]))
        average_cost = Decimal(str(holding["average_cost"]))
        cost = quantity * average_cost
        bist_cost += cost
        bist.append([
            holding["symbol"], holding.get("company", ""), float(quantity),
            float(average_cost), float(cost), holding.get("sector", ""),
            holding.get("notes", ""), "Canlı fiyat verisi yok",
        ])
    _style_sheet(bist)
    for row in bist.iter_rows(min_row=2, min_col=3, max_col=5):
        for cell in row:
            cell.number_format = '#,##0.00'

    def currencies(try_value: Decimal | None) -> tuple[float | None, float | None, float | None]:
        if try_value is None:
            return None, None, None
        eur_value = try_value / try_per_eur if try_per_eur and try_per_eur > 0 else None
        usd_value = try_value / try_per_usd if try_per_usd and try_per_usd > 0 else None
        return float(try_value), float(eur_value) if eur_value is not None else None, float(usd_value) if usd_value is not None else None

    summary_rows = [
        ("Döviz", "Güncel piyasa değeri", currency_value),
        ("Maden", "Güncel piyasa değeri", metal_value),
        ("Hisse Senedi", "Kayıtlı alış maliyeti (canlı fiyat yok)", bist_cost),
    ]
    available_totals = [value for _name, _basis, value in summary_rows if value is not None]
    grand_total = sum(available_totals, Decimal("0")) if len(available_totals) == len(summary_rows) else None

    for name, basis, value in summary_rows:
        try_value, eur_value, usd_value = currencies(value)
        summary.append([name, basis, try_value, eur_value, usd_value])
    try_value, eur_value, usd_value = currencies(grand_total)
    summary.append(["GENEL TOPLAM", "Döviz + maden güncel değerleri ve hisse kayıtlı maliyeti", try_value, eur_value, usd_value])

    note_row = summary.max_row + 2
    summary.cell(note_row, 1, "Not:")
    summary.cell(note_row, 2, "BIST sekmesinde henüz canlı hisse fiyatı bulunmadığından hisse toplamı alış maliyetidir. Genel toplam, tüm grupların güncel değerleri mevcutsa hesaplanır.")
    summary.cell(note_row + 1, 2, "EUR ve USD karşılıkları dışa aktarma anındaki döviz kurlarıyla çevrilmiştir.")
    summary.cell(note_row + 2, 2, "İlgili fiyat veya kur verisi yoksa grup ve genel toplam değerleri eksik hesaplanmaması için boş bırakılır.")
    summary.merge_cells(start_row=1, start_column=1, end_row=1, end_column=5)
    summary.merge_cells(start_row=2, start_column=1, end_row=2, end_column=5)
    summary.merge_cells(start_row=note_row, start_column=2, end_row=note_row, end_column=5)
    summary.merge_cells(start_row=note_row + 1, start_column=2, end_row=note_row + 1, end_column=5)
    summary.merge_cells(start_row=note_row + 2, start_column=2, end_row=note_row + 2, end_column=5)
    summary["A1"].font = Font(size=16, bold=True, color="FFFFFF")
    summary["A1"].fill = PatternFill("solid", fgColor="203864")
    summary["A2"].alignment = Alignment(wrap_text=True, vertical="center")
    summary.row_dimensions[2].height = 34
    if profile_name:
        summary["A3"].font = Font(bold=True, color="203864")
        summary["B3"].font = Font(bold=True, color="172033")
        summary["A3"].alignment = Alignment(vertical="center", wrap_text=True)
        summary["B3"].alignment = Alignment(vertical="center", wrap_text=True)
        summary.row_dimensions[3].height = 30
    for cell in summary[4]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = PatternFill("solid", fgColor="203864")
        cell.alignment = Alignment(horizontal="center")
    for row in summary.iter_rows(min_row=5, max_row=8, min_col=3, max_col=5):
        for cell in row:
            cell.number_format = '#,##0.00'
    for cell in summary[8]:
        cell.font = Font(bold=True)
        cell.fill = PatternFill("solid", fgColor="D9EAF7")
    summary.column_dimensions["A"].width = 22
    summary.column_dimensions["B"].width = 58
    for col in ("C", "D", "E"):
        summary.column_dimensions[col].width = 18
    summary.sheet_view.showGridLines = False
    summary.freeze_panes = "A5"

    add_export_metadata_sheet(
        workbook, rates_updated_at=rates_updated_at, rates_status=rates_status,
        profile_name=profile_name,
    )

    # Summary must always be the first worksheet.
    workbook.active = 0
    workbook.save(path)
    workbook.close()
