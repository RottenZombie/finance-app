"""Supported ISO 4217 currencies and their Turkish display names."""

# Keep this list focused on currencies commonly useful to FinanceTerminal users.
# Rates are retrieved dynamically from the exchange-rate provider; a currency
# appears with a live quote only when the provider returns it.
CURRENCY_INFO: dict[str, tuple[str, str]] = {
    "USD": ("ABD Doları", "USD"),
    "EUR": ("Euro", "EUR"),
    "HUF": ("Macar Forinti", "HUF"),
    "GBP": ("İngiliz Sterlini", "GBP"),
    "CHF": ("İsviçre Frangı", "CHF"),
    "JPY": ("Japon Yeni", "JPY"),
    "CAD": ("Kanada Doları", "CAD"),
    "AUD": ("Avustralya Doları", "AUD"),
    "CNY": ("Çin Yuanı", "CNY"),
    "RUB": ("Rus Rublesi", "RUB"),
    "SEK": ("İsveç Kronu", "SEK"),
    "NOK": ("Norveç Kronu", "NOK"),
    "DKK": ("Danimarka Kronu", "DKK"),
    "PLN": ("Polonya Zlotisi", "PLN"),
    "CZK": ("Çek Korunası", "CZK"),
    "AED": ("BAE Dirhemi", "AED"),
    "SAR": ("Suudi Riyali", "SAR"),
    "QAR": ("Katar Riyali", "QAR"),
    "KWD": ("Kuveyt Dinarı", "KWD"),
    "BHD": ("Bahreyn Dinarı", "BHD"),
    "INR": ("Hindistan Rupisi", "INR"),
    "KRW": ("Güney Kore Wonu", "KRW"),
    "SGD": ("Singapur Doları", "SGD"),
    "HKD": ("Hong Kong Doları", "HKD"),
    "NZD": ("Yeni Zelanda Doları", "NZD"),
    "ZAR": ("Güney Afrika Randı", "ZAR"),
    "BRL": ("Brezilya Reali", "BRL"),
    "MXN": ("Meksika Pesosu", "MXN"),
    "IDR": ("Endonezya Rupisi", "IDR"),
    "THB": ("Tayland Bahtı", "THB"),
}

DEFAULT_CURRENCY_CODES = ["USD", "EUR", "HUF"]


def currency_display_name(code: str) -> str:
    code = str(code).strip().upper()
    return CURRENCY_INFO.get(code, (code, code))[0]
