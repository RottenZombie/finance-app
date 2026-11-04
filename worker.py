from datetime import datetime

from PySide6.QtCore import QThread, Signal
from core.api import get_all_rates, get_metal_prices


class Worker(QThread):
    result = Signal(dict)

    def run(self):
        try:
            data = get_all_rates()
            gold, silver = get_metal_prices()
            data["gold"] = gold
            data["silver"] = silver
            data["fetched_at"] = datetime.now().astimezone().strftime(
                "%d.%m.%Y %H:%M:%S %Z"
            ).strip()
            self.result.emit(data)
        except Exception:
            # Keep the UI and refresh lifecycle alive even if a provider fails.
            self.result.emit({
                "USD": None,
                "EUR": None,
                "HUF": None,
                "gold": None,
                "silver": None,
                "status": "Offline",
                "fetched_at": datetime.now().astimezone().strftime(
                    "%d.%m.%Y %H:%M:%S %Z"
                ).strip(),
            })
