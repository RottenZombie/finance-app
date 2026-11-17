from PySide6.QtCore import QThread, Signal

from core.log_setup import get_logger
from core.market_refresh import collect_market_snapshot, offline_snapshot
from features.bist.quotes import fetch_bist_quotes

log = get_logger("worker")


class Worker(QThread):
    """Refresh market data off the GUI thread.

    The result signal can fire twice: first with currency/metal data (fast), then
    again with the same data plus ``bist_quotes`` once share prices have arrived,
    so a slow BIST provider never delays the currency cards.
    """

    result = Signal(dict)

    def __init__(self, parent=None, bist_symbols=None):
        super().__init__(parent)
        self._bist_symbols = list(bist_symbols or [])

    def run(self):
        try:
            data = collect_market_snapshot()
        except Exception:
            # Keep the UI and refresh lifecycle alive even if a provider fails.
            log.error("Piyasa verisi alınamadı", exc_info=True)
            data = offline_snapshot()
        self.result.emit(dict(data))

        if not self._bist_symbols:
            return
        try:
            quotes = fetch_bist_quotes(self._bist_symbols)
        except Exception:
            log.error("BIST fiyatları alınamadı", exc_info=True)
            quotes = {"quotes": {}, "live": [], "cached": [], "failed": list(self._bist_symbols)}
        final = dict(data)
        final["bist_quotes"] = quotes
        self.result.emit(final)
