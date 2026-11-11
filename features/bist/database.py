from __future__ import annotations

from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal
import os
from pathlib import Path
import sqlite3
from typing import Any

from .utils import normalize_symbol, parse_localized_decimal
from core.app_paths import data_directory


def default_database_path() -> Path:
    """Return a per-user data location; never write portfolio data beside the EXE."""
    return data_directory() / "bist_portfolio.db"


class BistDatabase:
    """Small SQLite repository for local BIST holdings."""

    def __init__(self, db_path: str | Path | None = None):
        self.db_path = Path(db_path) if db_path else default_database_path()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._initialize()

    @contextmanager
    def _connection(self):
        conn = sqlite3.connect(self.db_path, timeout=15)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _initialize(self) -> None:
        with self._connection() as conn:
            conn.execute("PRAGMA journal_mode = WAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS bist_holdings (
                    symbol TEXT PRIMARY KEY,
                    company TEXT NOT NULL DEFAULT '',
                    quantity TEXT NOT NULL,
                    average_cost TEXT NOT NULL,
                    sector TEXT NOT NULL DEFAULT '',
                    notes TEXT NOT NULL DEFAULT '',
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_bist_holdings_updated "
                "ON bist_holdings(updated_at)"
            )

    def upsert_holding(
        self,
        symbol: object,
        quantity: object,
        average_cost: object,
        company: object = "",
        sector: object = "",
        notes: object = "",
    ) -> dict[str, Any]:
        ticker = normalize_symbol(symbol)
        qty = parse_localized_decimal(quantity, field_name="Adet")
        cost = parse_localized_decimal(average_cost, field_name="Ortalama maliyet")
        if qty <= 0:
            raise ValueError("Adet sıfırdan büyük olmalıdır.")
        if cost < 0:
            raise ValueError("Ortalama maliyet negatif olamaz.")

        company_text = str(company or "").strip() or ticker
        sector_text = str(sector or "").strip()
        notes_text = str(notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with self._connection() as conn:
            conn.execute(
                """
                INSERT INTO bist_holdings
                    (symbol, company, quantity, average_cost, sector, notes, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(symbol) DO UPDATE SET
                    company=excluded.company,
                    quantity=excluded.quantity,
                    average_cost=excluded.average_cost,
                    sector=excluded.sector,
                    notes=excluded.notes,
                    updated_at=excluded.updated_at
                """,
                (
                    ticker,
                    company_text,
                    str(qty),
                    str(cost),
                    sector_text,
                    notes_text,
                    now,
                    now,
                ),
            )
        return self.get_holding(ticker)  # type: ignore[return-value]

    def update_holding(
        self,
        original_symbol: object,
        *,
        symbol: object,
        quantity: object,
        average_cost: object,
        company: object = "",
        sector: object = "",
        notes: object = "",
    ) -> dict[str, Any]:
        """Update every editable field of an existing BIST holding.

        The ticker may be renamed, but an existing ticker is never overwritten.
        The original created_at timestamp is retained.
        """
        old_ticker = normalize_symbol(original_symbol)
        new_ticker = normalize_symbol(symbol)
        qty = parse_localized_decimal(quantity, field_name="Adet")
        cost = parse_localized_decimal(average_cost, field_name="Ortalama maliyet")
        if qty <= 0:
            raise ValueError("Adet sıfırdan büyük olmalıdır.")
        if cost < 0:
            raise ValueError("Ortalama maliyet negatif olamaz.")

        company_text = str(company or "").strip() or new_ticker
        sector_text = str(sector or "").strip()
        notes_text = str(notes or "").strip()
        now = datetime.now(timezone.utc).isoformat(timespec="seconds")

        with self._connection() as conn:
            existing = conn.execute(
                "SELECT symbol FROM bist_holdings WHERE symbol = ?", (old_ticker,)
            ).fetchone()
            if existing is None:
                raise ValueError(f"Düzenlenecek kayıt bulunamadı: {old_ticker}")

            if new_ticker != old_ticker:
                collision = conn.execute(
                    "SELECT symbol FROM bist_holdings WHERE symbol = ?", (new_ticker,)
                ).fetchone()
                if collision is not None:
                    raise ValueError(
                        f"{new_ticker} koduyla başka bir kayıt zaten mevcut. "
                        "Mevcut kaydı ezmemek için değişiklik yapılmadı."
                    )

            conn.execute(
                """
                UPDATE bist_holdings
                SET symbol = ?, company = ?, quantity = ?, average_cost = ?,
                    sector = ?, notes = ?, updated_at = ?
                WHERE symbol = ?
                """,
                (
                    new_ticker, company_text, str(qty), str(cost),
                    sector_text, notes_text, now, old_ticker,
                ),
            )
        return self.get_holding(new_ticker)  # type: ignore[return-value]

    def get_holding(self, symbol: object) -> dict[str, Any] | None:
        ticker = normalize_symbol(symbol)
        with self._connection() as conn:
            row = conn.execute(
                "SELECT * FROM bist_holdings WHERE symbol = ?", (ticker,)
            ).fetchone()
        return dict(row) if row else None

    def list_holdings(self) -> list[dict[str, Any]]:
        with self._connection() as conn:
            rows = conn.execute(
                "SELECT * FROM bist_holdings ORDER BY symbol COLLATE NOCASE"
            ).fetchall()
        return [dict(row) for row in rows]

    def delete_holding(self, symbol: object) -> bool:
        return self.delete_holdings([symbol]) > 0

    def delete_holdings(self, symbols: list[object] | None = None) -> int:
        """Delete selected BIST tickers, or the entire BIST portfolio if None."""
        with self._connection() as conn:
            if symbols is None:
                cursor = conn.execute("DELETE FROM bist_holdings")
            else:
                tickers = list(dict.fromkeys(normalize_symbol(symbol) for symbol in symbols))
                if not tickers:
                    return 0
                placeholders = ",".join("?" for _ in tickers)
                cursor = conn.execute(
                    f"DELETE FROM bist_holdings WHERE symbol IN ({placeholders})", tickers
                )
            return max(cursor.rowcount, 0)

    def delete_all(self) -> int:
        return self.delete_holdings(None)

    def summary(self) -> dict[str, Any]:
        rows = self.list_holdings()
        total_cost = sum(
            (Decimal(row["quantity"]) * Decimal(row["average_cost"]) for row in rows),
            Decimal("0"),
        )
        return {"holding_count": len(rows), "total_cost": total_cost}

    def import_rows(self, rows: list[dict[str, Any]]) -> tuple[int, list[str]]:
        """Import normalized row dictionaries. Existing symbols are updated."""
        imported = 0
        errors: list[str] = []
        for row_number, row in enumerate(rows, start=2):
            try:
                self.upsert_holding(
                    symbol=row.get("symbol", ""),
                    company=row.get("company", ""),
                    quantity=row.get("quantity", ""),
                    average_cost=row.get("average_cost", ""),
                    sector=row.get("sector", ""),
                    notes=row.get("notes", ""),
                )
                imported += 1
            except Exception as exc:
                errors.append(f"Satır {row_number}: {exc}")
        return imported, errors
