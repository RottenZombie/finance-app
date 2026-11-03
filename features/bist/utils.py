from __future__ import annotations

from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import re


def parse_localized_decimal(value: object, *, field_name: str = "Değer") -> Decimal:
    """Parse common Turkish/English numeric formats into Decimal.

    Examples:
        "1.234,56" -> Decimal("1234.56")
        "1234,56"  -> Decimal("1234.56")
        "1,234.56" -> Decimal("1234.56")
        "1234.56"  -> Decimal("1234.56")
    """
    if isinstance(value, Decimal):
        number = value
    elif value is None:
        raise ValueError(f"{field_name} boş bırakılamaz.")
    else:
        raw = str(value).strip()
        if not raw:
            raise ValueError(f"{field_name} boş bırakılamaz.")

        negative = raw.startswith("(") and raw.endswith(")")
        if negative:
            raw = raw[1:-1]

        raw = raw.replace("₺", "").replace("TL", "").replace("TRY", "")
        raw = raw.replace(" ", "").replace("\u00a0", "")
        raw = raw.replace("'", "").replace("’", "")

        # If both separators exist, the last one is treated as decimal separator.
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

        if negative:
            raw = "-" + raw

        # Reject unexpected symbols instead of silently producing a wrong amount.
        if not re.fullmatch(r"[+-]?\d+(?:\.\d+)?", raw):
            raise ValueError(f"{field_name} geçerli bir sayı değil: {value}")
        try:
            number = Decimal(raw)
        except InvalidOperation as exc:
            raise ValueError(f"{field_name} geçerli bir sayı değil: {value}") from exc

    if not number.is_finite():
        raise ValueError(f"{field_name} sonlu bir sayı olmalı.")
    return number


def normalize_symbol(value: object) -> str:
    symbol = str(value or "").strip().upper()
    if symbol.startswith("BIST:"):
        symbol = symbol[5:]
    if symbol.endswith(".IS"):
        symbol = symbol[:-3]
    if not re.fullmatch(r"[A-Z0-9]{2,12}", symbol):
        raise ValueError("Hisse kodu 2–12 karakterli harf/rakam içermelidir.")
    return symbol


def format_tl(value: Decimal | str | int | float, decimals: int = 2) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    quantum = Decimal("1").scaleb(-decimals)
    rounded = amount.quantize(quantum, rounding=ROUND_HALF_UP)
    formatted = f"{rounded:,.{decimals}f}"
    return formatted.replace(",", "X").replace(".", ",").replace("X", ".")


def format_quantity(value: Decimal | str | int | float) -> str:
    amount = value if isinstance(value, Decimal) else Decimal(str(value))
    if amount == amount.to_integral_value():
        return format_tl(amount, 0)
    return format_tl(amount, 4).rstrip("0").rstrip(",")
