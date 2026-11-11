from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import os
from pathlib import Path
import re
import sqlite3
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill
from openpyxl.utils import get_column_letter

from features.export_metadata import add_export_metadata_sheet
from core.app_paths import data_directory
from features.currencies import CURRENCY_INFO


ALLOWED_ASSETS = {
    "currency": set(CURRENCY_INFO),
    "metals": {"XAU", "XAG"},
}


def default_database_path() -> Path:
    """Keep holdings in the user's application-data directory, not beside the EXE."""
    return data_directory() / "investment_holdings.db"


def parse_localized_decimal(value: object, *, field_name: str = "Değer") -> Decimal:
    """Parse Turkish and English decimal formats without using binary floats."""
    if isinstance(value, Decimal):
        number = value
    elif value is None:
        raise ValueError(f"{field_name} boş bırakılamaz.")
    else:
        raw = str(value).strip()
        if not raw:
            raise ValueError(f"{field_name} boş bırakılamaz.")
        raw = raw.replace("₺", "").replace("TL", "").replace("TRY", "")
        raw = raw.replace(" ", "").replace("\u00a0", "")
        if "," in raw and "." in raw:
            if raw.rfind(",") > raw.rfind("."):
                raw = raw.replace(".", "").replace(",", ".")
            else:
                raw = raw.replace(",", "")
        elif "," in raw:
            raw = raw.replace(".", "").replace(",", ".")
        elif raw.count(".") > 1:
            parts = raw.split(".")
            raw = "".join(parts[:-1]) + "." + parts[-1]
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", raw):
            raise ValueError(f"{field_name} geçerli bir sayı değil: {value}")
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(f"{field_name} geçerli bir sayı değil: {value}") from exc

    if not number.is_finite():
        raise ValueError(f"{field_name} sonlu bir sayı olmalı.")
    return number


def format_localized(value: Decimal | str | int | float, decimals: int = 2) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    formatted = f"{amount:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_quantity(value: Decimal | str | int | float) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    formatted = f"{amount:,.4f}".rstrip("0").rstrip(".")
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


class InvestmentStore:
    """Local SQLite store that merges repeat purchases using weighted average cost."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else default_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self):
        connection = sqlite3.connect(self.db_path, timeout=15)
        connection.row_factory = sqlite3.Row
        try:
            yield connection
            connection.commit()
        except Exception:
            connection.rollback()
            raise
        finally:
            connection.close()

    def _initialize(self) -> None:
        with self._connection() as connection:
            connection.execute("PRAGMA journal_mode = WAL")
            connection.execute(
                """
                CREATE TABLE IF NOT EXISTS investment_holdings (
                    asset_group TEXT NOT NULL,
                    asset_code TEXT NOT NULL,
                    display_name TEXT NOT NULL,
                    unit TEXT NOT NULL,
                    quantity TEXT NOT NULL,
                    average_cost_try TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (asset_group, asset_code)
                )
                """
            )

    def add_purchase(
        self,
        asset_group: str,
        asset_code: str,
        quantity: object,
        unit_cost_try: object,
        *,
        display_name: str,
        unit: str,
    ) -> dict[str, Any]:
        group = str(asset_group).strip().lower()
        code = str(asset_code).strip().upper()
        if group not in ALLOWED_ASSETS or code not in ALLOWED_ASSETS[group]:
            raise ValueError("Geçersiz varlık türü veya kodu.")
        qty = parse_localized_decimal(quantity, field_name="Miktar")
        price = parse_localized_decimal(unit_cost_try, field_name="Alış birim fiyatı")
        if qty <= 0:
            raise ValueError("Miktar sıfırdan büyük olmalıdır.")
        if price <= 0:
            raise ValueError("Alış birim fiyatı sıfırdan büyük olmalıdır.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connection() as connection:
            row = connection.execute(
                "SELECT quantity, average_cost_try, created_at FROM investment_holdings "
                "WHERE asset_group = ? AND asset_code = ?",
                (group, code),
            ).fetchone()

            if row:
                old_quantity = Decimal(row["quantity"])
                old_average = Decimal(row["average_cost_try"])
                new_quantity = old_quantity + qty
                new_average = ((old_quantity * old_average) + (qty * price)) / new_quantity
                created_at = row["created_at"]
            else:
                new_quantity = qty
                new_average = price
                created_at = now

            connection.execute(
                """
                INSERT INTO investment_holdings
                    (asset_group, asset_code, display_name, unit, quantity,
                     average_cost_try, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_group, asset_code) DO UPDATE SET
                    display_name = excluded.display_name,
                    unit = excluded.unit,
                    quantity = excluded.quantity,
                    average_cost_try = excluded.average_cost_try,
                    updated_at = excluded.updated_at
                """,
                (
                    group,
                    code,
                    str(display_name).strip(),
                    str(unit).strip(),
                    str(new_quantity),
                    str(new_average),
                    created_at,
                    now,
                ),
            )
        return self.get_holding(group, code)  # type: ignore[return-value]

    def set_holding(
        self,
        asset_group: str,
        asset_code: str,
        quantity: object,
        average_cost_try: object,
        *,
        display_name: str,
        unit: str,
    ) -> dict[str, Any]:
        """Replace a holding with an imported snapshot without adding to it."""
        group = str(asset_group).strip().lower()
        code = str(asset_code).strip().upper()
        if group not in ALLOWED_ASSETS or code not in ALLOWED_ASSETS[group]:
            raise ValueError("Geçersiz varlık türü veya kodu.")
        qty = parse_localized_decimal(quantity, field_name="Miktar")
        average = parse_localized_decimal(average_cost_try, field_name="Ortalama alış fiyatı")
        if qty <= 0 or average <= 0:
            raise ValueError("Miktar ve ortalama alış fiyatı sıfırdan büyük olmalıdır.")

        now = datetime.now(timezone.utc).isoformat(timespec="seconds")
        with self._connection() as connection:
            connection.execute(
                """
                INSERT INTO investment_holdings
                    (asset_group, asset_code, display_name, unit, quantity,
                     average_cost_try, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(asset_group, asset_code) DO UPDATE SET
                    display_name = excluded.display_name,
                    unit = excluded.unit,
                    quantity = excluded.quantity,
                    average_cost_try = excluded.average_cost_try,
                    updated_at = excluded.updated_at
                """,
                (group, code, str(display_name).strip(), str(unit).strip(),
                 str(qty), str(average), now, now),
            )
        return self.get_holding(group, code)  # type: ignore[return-value]

    def get_holding(self, asset_group: str, asset_code: str) -> dict[str, Any] | None:
        with self._connection() as connection:
            row = connection.execute(
                "SELECT * FROM investment_holdings WHERE asset_group = ? AND asset_code = ?",
                (str(asset_group).strip().lower(), str(asset_code).strip().upper()),
            ).fetchone()
        return dict(row) if row else None

    def list_holdings(self, asset_group: str) -> list[dict[str, Any]]:
        group = str(asset_group).strip().lower()
        if group not in ALLOWED_ASSETS:
            raise ValueError("Geçersiz portföy türü.")
        with self._connection() as connection:
            rows = connection.execute(
                "SELECT * FROM investment_holdings WHERE asset_group = ? "
                "ORDER BY asset_code COLLATE NOCASE",
                (group,),
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_holding(self, asset_group: str, asset_code: str) -> bool:
        return self.delete_holdings(asset_group, [asset_code]) > 0

    def delete_holdings(
        self, asset_group: str, asset_codes: list[str] | None = None
    ) -> int:
        """Delete selected assets, or every holding in a group when codes is None."""
        group = str(asset_group).strip().lower()
        if group not in ALLOWED_ASSETS:
            raise ValueError("Geçersiz portföy türü.")

        with self._connection() as connection:
            if asset_codes is None:
                cursor = connection.execute(
                    "DELETE FROM investment_holdings WHERE asset_group = ?", (group,)
                )
            else:
                codes = list(dict.fromkeys(str(code).strip().upper() for code in asset_codes))
                if not codes:
                    return 0
                invalid = [code for code in codes if code not in ALLOWED_ASSETS[group]]
                if invalid:
                    raise ValueError("Silinecek varlık kodu geçersiz.")
                placeholders = ",".join("?" for _ in codes)
                cursor = connection.execute(
                    f"DELETE FROM investment_holdings WHERE asset_group = ? AND asset_code IN ({placeholders})",
                    [group, *codes],
                )
        return max(cursor.rowcount, 0)

    def delete_all(self, asset_group: str) -> int:
        return self.delete_holdings(asset_group, None)


def write_holdings_excel(
    path: str | Path,
    holdings: list[dict[str, Any]],
    current_prices: dict[str, Decimal | None],
    *,
    title: str,
    rates_updated_at: str | None = None,
    rates_status: str | None = None,
) -> None:
    """Export a point-in-time view; this does not create a price-history series."""
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = title[:31]
    sheet.append([
        "Kod",
        "Varlık",
        "Miktar",
        "Birim",
        "Ortalama Alış Fiyatı (₺)",
        "Toplam Maliyet (₺)",
        "Güncel Birim Fiyat (₺)",
        "Güncel Değer (₺)",
        "Kâr / Zarar (₺)",
        "Kâr / Zarar (%)",
    ])

    for holding in holdings:
        quantity = Decimal(holding["quantity"])
        average_cost = Decimal(holding["average_cost_try"])
        total_cost = quantity * average_cost
        current_price = current_prices.get(holding["asset_code"])
        if current_price is not None and current_price > 0:
            current_value = quantity * current_price
            profit_loss = current_value - total_cost
            profit_percent = (profit_loss / total_cost * Decimal("100")) if total_cost else Decimal("0")
        else:
            current_value = profit_loss = profit_percent = None

        sheet.append([
            holding["asset_code"],
            holding["display_name"],
            float(quantity),
            holding["unit"],
            float(average_cost),
            float(total_cost),
            float(current_price) if current_price is not None else None,
            float(current_value) if current_value is not None else None,
            float(profit_loss) if profit_loss is not None else None,
            float(profit_percent) if profit_percent is not None else None,
        ])

    header_fill = PatternFill("solid", fgColor="203864")
    for cell in sheet[1]:
        cell.font = Font(bold=True, color="FFFFFF")
        cell.fill = header_fill
        cell.alignment = Alignment(horizontal="center")
    for row in sheet.iter_rows(min_row=2, min_col=5, max_col=9):
        for cell in row:
            cell.number_format = '#,##0.00'
    for row in sheet.iter_rows(min_row=2, min_col=10, max_col=10):
        for cell in row:
            cell.number_format = '0.00"%"'
    sheet.freeze_panes = "A2"
    sheet.auto_filter.ref = sheet.dimensions
    for column in sheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column)
        sheet.column_dimensions[get_column_letter(column[0].column)].width = min(max(max_length + 2, 12), 28)
    sheet.sheet_view.showGridLines = False
    add_export_metadata_sheet(
        workbook, rates_updated_at=rates_updated_at, rates_status=rates_status,
        include_bist_note=False,
    )
    workbook.active = 0
    workbook.save(path)
