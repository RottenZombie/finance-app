"""Manual live check of the free BIST price providers (needs internet).

Usage (from the project folder):
    python tools/check_quotes.py THYAO ASELS AKBNK

It queries every provider separately so you can see which one works from your
connection. It does not touch your portfolio or the price cache.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from features.bist.quotes import IsYatirimProvider, YahooChartProvider  # noqa: E402
from features.bist.utils import normalize_symbol  # noqa: E402


def main(argv: list[str]) -> int:
    symbols = argv or ["THYAO", "ASELS", "AKBNK"]
    providers = [YahooChartProvider(), IsYatirimProvider()]
    failures = 0
    for symbol in symbols:
        ticker = normalize_symbol(symbol)
        print(f"\n{ticker}")
        for provider in providers:
            try:
                quote = provider.fetch(ticker)
                print(f"  OK    {provider.name:<14} {quote.price} TRY  (zaman: {quote.as_of})")
            except Exception as exc:  # noqa: BLE001 - diagnostic tool
                failures += 1
                print(f"  FAIL  {provider.name:<14} {exc}")
    print("\nSonuç: en az bir sağlayıcı çalışıyorsa uygulama fiyat alabilir.")
    return 0 if failures < len(symbols) * len(providers) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
