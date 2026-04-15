from PySide6.QtCore import QThread, Signal
from core.api import get_all_rates, get_metal_prices


class Worker(QThread):
    result = Signal(dict)

    def run(self):
        data = get_all_rates()
        gold, silver = get_metal_prices()

        data["gold"] = gold
        data["silver"] = silver

        self.result.emit(data)