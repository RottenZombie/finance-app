"""Supported ISO 4217 currencies, their names and the shared display order.

Every currency drop-down in the application uses :data:`CURRENCY_RANKING`, so the
order is identical everywhere. The ranking follows each currency's share of
global foreign-exchange turnover in the BIS Triennial Central Bank Survey
(April 2025): USD, EUR, JPY, GBP, CNY, CHF, AUD, CAD, HKD, ... Beyond the top
ten the order is approximate, and currencies the survey does not break out are
appended by rough economic weight. To change the order, edit the tuple below -
nothing else depends on it.

Rates are retrieved dynamically from the exchange-rate provider; a currency
appears with a live quote only when the provider returns it.
"""
from __future__ import annotations

from core.i18n import get_language

# (Turkish name, English name)
_NAMES: dict[str, tuple[str, str]] = {
    "USD": ("ABD Doları", "US Dollar"),
    "EUR": ("Euro", "Euro"),
    "JPY": ("Japon Yeni", "Japanese Yen"),
    "GBP": ("İngiliz Sterlini", "British Pound"),
    "CNY": ("Çin Yuanı", "Chinese Yuan"),
    "CHF": ("İsviçre Frangı", "Swiss Franc"),
    "AUD": ("Avustralya Doları", "Australian Dollar"),
    "CAD": ("Kanada Doları", "Canadian Dollar"),
    "HKD": ("Hong Kong Doları", "Hong Kong Dollar"),
    "SGD": ("Singapur Doları", "Singapore Dollar"),
    "SEK": ("İsveç Kronu", "Swedish Krona"),
    "KRW": ("Güney Kore Wonu", "South Korean Won"),
    "NOK": ("Norveç Kronu", "Norwegian Krone"),
    "NZD": ("Yeni Zelanda Doları", "New Zealand Dollar"),
    "INR": ("Hindistan Rupisi", "Indian Rupee"),
    "MXN": ("Meksika Pesosu", "Mexican Peso"),
    "TRY": ("Türk Lirası", "Turkish Lira"),
    "ZAR": ("Güney Afrika Randı", "South African Rand"),
    "BRL": ("Brezilya Reali", "Brazilian Real"),
    "DKK": ("Danimarka Kronu", "Danish Krone"),
    "PLN": ("Polonya Zlotisi", "Polish Zloty"),
    "THB": ("Tayland Bahtı", "Thai Baht"),
    "ILS": ("İsrail Şekeli", "Israeli Shekel"),
    "IDR": ("Endonezya Rupisi", "Indonesian Rupiah"),
    "CZK": ("Çek Korunası", "Czech Koruna"),
    "AED": ("BAE Dirhemi", "UAE Dirham"),
    "HUF": ("Macar Forinti", "Hungarian Forint"),
    "SAR": ("Suudi Riyali", "Saudi Riyal"),
    "MYR": ("Malezya Ringgiti", "Malaysian Ringgit"),
    "RON": ("Romen Leyi", "Romanian Leu"),
    "RUB": ("Rus Rublesi", "Russian Ruble"),
    "KWD": ("Kuveyt Dinarı", "Kuwaiti Dinar"),
    "QAR": ("Katar Riyali", "Qatari Riyal"),
    "BHD": ("Bahreyn Dinarı", "Bahraini Dinar"),
    "EGP": ("Mısır Lirası", "Egyptian Pound"),
    "UAH": ("Ukrayna Grivnası", "Ukrainian Hryvnia"),
    "RSD": ("Sırp Dinarı", "Serbian Dinar"),
    "GEL": ("Gürcü Larisi", "Georgian Lari"),
    "AZN": ("Azerbaycan Manatı", "Azerbaijani Manat"),
    "KZT": ("Kazak Tengesi", "Kazakhstani Tenge"),
}

# One ordering for every drop-down (see module docstring). TRY sits at its rank;
# lists where TRY makes no sense (it is the base currency) simply skip it.
CURRENCY_RANKING: tuple[str, ...] = tuple(_NAMES)

# Supported foreign currencies in ranking order: code -> (Turkish name, code).
CURRENCY_INFO: dict[str, tuple[str, str]] = {
    code: (_NAMES[code][0], code) for code in CURRENCY_RANKING if code != "TRY"
}

DEFAULT_CURRENCY_CODES = ["USD", "EUR", "HUF"]
DEFAULT_EXTRA_CURRENCY = "HUF"

_RANK = {code: index for index, code in enumerate(CURRENCY_RANKING)}


def currency_rank(code: str) -> int:
    return _RANK.get(str(code).strip().upper(), len(_RANK))


def sort_currency_codes(codes) -> list[str]:
    """Unique codes in the shared display order (unknown codes keep their place last)."""
    unique = list(dict.fromkeys(str(code).strip().upper() for code in codes))
    return sorted(unique, key=currency_rank)


def currency_choices(*, include_try: bool = False, exclude: tuple[str, ...] = ()) -> list[str]:
    """Codes for a drop-down, already in the shared order."""
    skipped = {str(code).upper() for code in exclude}
    return [
        code for code in CURRENCY_RANKING
        if code not in skipped and (include_try or code != "TRY")
    ]


def currency_display_name(code: str, language: str | None = None) -> str:
    code = str(code).strip().upper()
    names = _NAMES.get(code)
    if names is None:
        return code
    return names[1] if (language or get_language()) == "en" else names[0]


def localized_currency_assets() -> dict[str, tuple[str, str]]:
    """Like CURRENCY_INFO but with names in the active language."""
    return {code: (currency_display_name(code), code) for code in CURRENCY_INFO}


def metal_assets() -> dict[str, tuple[str, str]]:
    """Gold and silver with names in the active language."""
    from core.i18n import tr

    return {"XAU": (tr("Altın"), "gr"), "XAG": (tr("Gümüş"), "gr")}


def asset_display_name(asset_group: str, code: str, stored: str = "") -> str:
    """Name to show for a saved holding, in the active language.

    The database keeps the name that was current when the record was created; this
    always re-derives it so switching language also relabels old records.
    """
    code = str(code).strip().upper()
    if asset_group == "currency" and code in CURRENCY_INFO:
        return currency_display_name(code)
    if asset_group == "metals":
        from core.i18n import tr

        names = {"XAU": tr("Altın"), "XAG": tr("Gümüş")}
        if code in names:
            return names[code]
    return stored or code
