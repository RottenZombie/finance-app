import sys
import requests
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QLineEdit, QComboBox, QDialog
)
from PySide6.QtCore import QThread, Signal


VERSION = "1.8.1"
API = "https://open.er-api.com/v6/latest"


# ---------------- API ----------------
def get_all_rates():
    try:
        data = requests.get(f"{API}/USD", timeout=5).json()
        rates = data.get("rates", {})

        usd_try = rates.get("TRY")

        return {
            "USD": usd_try,
            "EUR": usd_try / rates.get("EUR") if rates.get("EUR") else None,
            "HUF": usd_try / rates.get("HUF") if rates.get("HUF") else None
        }
    except Exception as e:
        print("API ERROR:", e)
        return {"USD": None, "EUR": None, "HUF": None}

def safe_format(val, digits=2):
    try:
        return f"{val:.{digits}f}" if val else "N/A"
    except:
        return "N/A"


# ---------------- WORKER ----------------
class Worker(QThread):
    result = Signal(dict)

    def run(self):
        data = get_all_rates()
        self.result.emit(data)


# ---------------- CARD ----------------
class Card(QFrame):
    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout()

        self.title = QLabel(title)
        self.value = QLabel("...")

        layout.addWidget(self.title)
        layout.addWidget(self.value)

        self.setLayout(layout)

    def apply_theme(self, theme):
        if theme == "Neon":
            self.setStyleSheet("""
                QFrame {
                    background-color: #0f1020;
                    border: 1px solid #00f5ff;
                    border-radius: 10px;
                    padding: 10px;
                }
                QLabel { color: white; }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #333;
                    border-radius: 10px;
                    padding: 10px;
                }
                QLabel { color: white; }
            """)


# ---------------- METALS ----------------
class Metals(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.gold_input = QLineEdit()
        self.gold_input.setPlaceholderText("Altın (gram)")

        self.silver_input = QLineEdit()
        self.silver_input.setPlaceholderText("Gümüş (gram)")

        self.result = QLabel("Sonuç: -")

        btn = QPushButton("Hesapla")
        btn.clicked.connect(self.calc)

        layout.addWidget(QLabel("Madenler"))
        layout.addWidget(self.gold_input)
        layout.addWidget(self.silver_input)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.setLayout(layout)

        self.gold_rate = 0
        self.silver_rate = 0

    def set_rates(self, gold_oz, silver_oz):
        GRAM = 31.1035
        self.gold_rate = (gold_oz / GRAM) if gold_oz else 0
        self.silver_rate = (silver_oz / GRAM) if silver_oz else 0

    def calc(self):
        try:
            gold_g = float(self.gold_input.text() or 0)
            silver_g = float(self.silver_input.text() or 0)

            gold_total = gold_g * self.gold_rate
            silver_total = silver_g * self.silver_rate

            self.result.setText(
                f"Altın: {safe_format(gold_total)} TRY | "
                f"Gümüş: {safe_format(silver_total)} TRY | "
                f"Toplam: {safe_format(gold_total + silver_total)} TRY"
            )
        except Exception as e:
            print(e)
            self.result.setText("Hata")


# ---------------- PORTFOLIO ----------------
class Portfolio(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout()

        self.usd = QLineEdit()
        self.eur = QLineEdit()
        self.try_in = QLineEdit()

        self.usd.setPlaceholderText("USD")
        self.eur.setPlaceholderText("EUR")
        self.try_in.setPlaceholderText("TRY")

        self.rate_box = QComboBox()
        self.rate_box.addItems(["USD", "EUR", "HUF"])

        self.result = QLabel("Sonuç: -")

        btn = QPushButton("Hesapla")
        btn.clicked.connect(self.calc)

        layout.addWidget(QLabel("Portfolio"))
        layout.addWidget(self.usd)
        layout.addWidget(self.eur)
        layout.addWidget(self.try_in)
        layout.addWidget(self.rate_box)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.setLayout(layout)

        self.rates = {}

    def set_rates(self, r):
        self.rates = r

    def calc(self):
        try:
            usd = float(self.usd.text() or 0)
            eur = float(self.eur.text() or 0)
            tr = float(self.try_in.text() or 0)

            usd_rate = self.rates.get("USD") or 0
            eur_rate = self.rates.get("EUR") or 0

            total_try = (usd * usd_rate) + (eur * eur_rate) + tr

            selected = self.rate_box.currentText()
            sel_rate = self.rates.get(selected)

            converted = total_try / sel_rate if sel_rate else 0

            self.result.setText(
                f"{safe_format(total_try)} TRY | {safe_format(converted)} {selected}"
            )
        except Exception as e:
            print(e)
            self.result.setText("Hata")


# ---------------- SETTINGS ----------------
class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Ayarlar")
        self.setFixedSize(250, 180)

        layout = QVBoxLayout()

        self.theme = QComboBox()
        self.theme.addItems(["Neon", "Dark"])
        self.theme.setCurrentText(parent.theme)

        btn = QPushButton("Uygula")
        btn.clicked.connect(self.apply)

        layout.addWidget(QLabel(f"Version: {VERSION}"))
        layout.addWidget(QLabel(f"API: {API}"))
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(self.theme)
        layout.addWidget(btn)

        self.setLayout(layout)

    def apply(self):
        self.parent().set_theme(self.theme.currentText())
        self.close()


# ---------------- MAIN APP ----------------
class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Finance Terminal")
        self.setGeometry(200, 200, 460, 520)

        self.theme = "Neon"

        self.tabs = QTabWidget()

        # TAB 1
        self.tab1 = QWidget()
        l1 = QVBoxLayout()

        self.usd = Card("USD/TRY")
        self.eur = Card("EUR/TRY")
        self.huf = Card("HUF/TRY")

        self.mode_box = QComboBox()
        self.mode_box.addItems(["Normal", "Ters"])

        self.last = QLabel("Son güncelleme: -")

        btn = QPushButton("Güncelle")
        btn.clicked.connect(self.update)

        settings_btn = QPushButton("Ayarlar ⚙️")
        settings_btn.clicked.connect(self.open_settings)

        l1.addWidget(self.usd)
        l1.addWidget(self.eur)
        l1.addWidget(self.huf)
        l1.addWidget(self.mode_box)
        l1.addWidget(self.last)
        l1.addWidget(btn)
        l1.addWidget(settings_btn)

        self.tab1.setLayout(l1)

        # TABS
        self.tab2 = Portfolio()
        self.tab3 = Metals()

        self.tabs.addTab(self.tab1, "Currency")
        self.tabs.addTab(self.tab2, "Portfolio")
        self.tabs.addTab(self.tab3, "Madenler")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.worker = None

        self.apply_theme()
        self.update()

    def open_settings(self):
        dlg = SettingsDialog(self)
        dlg.exec()

    def set_theme(self, theme):
        self.theme = theme
        self.apply_theme()

    def apply_theme(self):
        if self.theme == "Neon":
            self.setStyleSheet("""
                QWidget {
                    background-color: #0a0a0f;
                    color: white;
                }
                QPushButton {
                    background-color: #00f5ff;
                    color: black;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: #f0f0f0;
                    color: black;
                }
            """)

        self.usd.apply_theme(self.theme)
        self.eur.apply_theme(self.theme)
        self.huf.apply_theme(self.theme)

    def update(self):
        if self.worker and self.worker.isRunning():
            return

        self.worker = Worker()
        self.worker.result.connect(self.on_data)
        self.worker.start()

    def on_data(self, d):
        mode = self.mode_box.currentText()

        if mode == "Normal":
            self.usd.value.setText(f"{safe_format(d['USD'])} TRY")
            self.eur.value.setText(f"{safe_format(d['EUR'])} TRY")
            self.huf.value.setText(f"{safe_format(d['HUF'])} TRY")
        else:
            self.usd.value.setText(
                f"{safe_format(1/d['USD'],4) if d['USD'] else 'N/A'} USD"
            )
            self.eur.value.setText(
                f"{safe_format(1/d['EUR'],4) if d['EUR'] else 'N/A'} EUR"
            )
            self.huf.value.setText(
                f"{safe_format(1/d['HUF'],4) if d['HUF'] else 'N/A'} HUF"
            )

        self.tab2.set_rates(d)

        self.tab3.set_rates(
            gold_oz=70000,
            silver_oz=800
        )

        self.last.setText(
            f"Güncelleme: {datetime.now().strftime('%H:%M:%S')}"
        )


app = QApplication(sys.argv)
w = App()
w.show()
sys.exit(app.exec())