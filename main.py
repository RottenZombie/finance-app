import sys
import requests
from datetime import datetime

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton,
    QFrame, QTabWidget, QLineEdit, QComboBox, QDialog
)
from PySide6.QtCore import QThread, Signal


VERSION = "2.1.0"
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
            "HUF": usd_try / rates.get("HUF") if rates.get("HUF") else None,
            "status": "Online"
        }
    except:
        return {"USD": None, "EUR": None, "HUF": None, "status": "Offline"}


def get_metal_prices():
    try:
        gold = requests.get("https://api.gold-api.com/price/XAU", timeout=5).json()
        silver = requests.get("https://api.gold-api.com/price/XAG", timeout=5).json()

        return gold.get("price"), silver.get("price")
    except:
        return None, None


def safe_format(val, digits=2):
    try:
        return f"{val:.{digits}f}" if val is not None else "N/A"
    except:
        return "N/A"


# ---------------- WORKER ----------------
class Worker(QThread):
    result = Signal(dict)

    def run(self):
        data = get_all_rates()
        gold, silver = get_metal_prices()

        data["gold"] = gold
        data["silver"] = silver

        self.result.emit(data)


# ---------------- CARD ----------------
class Card(QFrame):
    from PySide6.QtCore import QPropertyAnimation

    def flash(self):
        self.anim = QPropertyAnimation(self, b"windowOpacity")
        self.anim.setDuration(200)
        self.anim.setStartValue(0.6)
        self.anim.setEndValue(1.0)
        self.anim.start()

    def __init__(self, title):
        super().__init__()
        layout = QVBoxLayout()

        self.title = QLabel(title)
        self.value = QLabel("...")

        layout.addWidget(self.title)
        layout.addWidget(self.value)
        self.setLayout(layout)

    def apply_theme(self, theme):
        if theme == "Blue":
            self.setStyleSheet("""
                QFrame {
                    background-color: #1a1f2e;
                    border: 1px solid #3a86ff;
                    border-radius: 10px;
                    padding: 10px;
                }
                QLabel { color: white; }
            """)
        else:
            self.setStyleSheet("""
                QFrame {
                    background-color: #2a2a2a;
                    border-radius: 10px;
                    padding: 10px;
                }
                QLabel { color: white; }
            """)

    from PySide6.QtWidgets import QGraphicsDropShadowEffect

    def highlight(self):
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(20)
        effect.setXOffset(0)
        effect.setYOffset(0)
        effect.setColor("#3a86ff")

        self.setGraphicsEffect(effect)


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

        note = QLabel("*Hesaplama ons üzerinden USD bazlı yapılır. Sonuçta küçük farklılıklar olabilir.")
        note.setStyleSheet("font-size: 10px; color: gray;")
        note.setWordWrap(True)

        layout.addWidget(note)

        self.setLayout(layout)

        self.gold_rate = 0
        self.silver_rate = 0
        self.precision = 2

    def set_rates(self, gold_oz, silver_oz):
        GRAM = 31.1035
        self.gold_rate = (gold_oz / GRAM) if gold_oz else 0
        self.silver_rate = (silver_oz / GRAM) if silver_oz else 0

    def set_precision(self, p):
        self.precision = p

    def calc(self):
        try:
            gold_g = float(self.gold_input.text() or 0)
            silver_g = float(self.silver_input.text() or 0)

            gold_total = gold_g * self.gold_rate
            silver_total = silver_g * self.silver_rate

            self.result.setText(
                f"Altın: {safe_format(gold_total, self.precision)} TRY | "
                f"Gümüş: {safe_format(silver_total, self.precision)} TRY | "
                f"Toplam: {safe_format(gold_total + silver_total, self.precision)} TRY"
            )
        except:
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
        self.precision = 2

    def set_rates(self, r):
        self.rates = r

    def set_precision(self, p):
        self.precision = p

    def calc(self):
        try:
            usd = float(self.usd.text() or 0)
            eur = float(self.eur.text() or 0)
            tr = float(self.try_in.text() or 0)

            total_try = (usd * (self.rates.get("USD") or 0)) + (eur * (self.rates.get("EUR") or 0)) + tr

            sel = self.rate_box.currentText()
            rate = self.rates.get(sel)

            converted = total_try / rate if rate else 0

            self.result.setText(
                f"{safe_format(total_try, self.precision)} TRY | "
                f"{safe_format(converted, self.precision)} {sel}"
            )
        except:
            self.result.setText("Hata")


# ---------------- SETTINGS ----------------
class SettingsDialog(QDialog):
    def __init__(self, parent):
        super().__init__(parent)

        self.setWindowTitle("Ayarlar")
        self.setFixedSize(280, 260)

        layout = QVBoxLayout()

        self.theme = QComboBox()
        self.theme.addItems(["Dark", "Blue"])
        self.theme.setCurrentText(parent.theme)

        self.start_tab = QComboBox()
        self.start_tab.addItems(["Currency", "Portfolio", "Madenler"])

        self.precision = QComboBox()
        self.precision.addItems(["2", "3", "4"])
        self.precision.setCurrentText(str(parent.precision))

        self.api_status = QLabel(f"API Durumu: {parent.api_status}")

        btn = QPushButton("Uygula")
        btn.clicked.connect(self.apply)

        layout.addWidget(QLabel(f"Version: {VERSION}"))
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(self.theme)
        layout.addWidget(QLabel("Başlangıç Sekmesi"))
        layout.addWidget(self.start_tab)
        layout.addWidget(QLabel("Ondalık Hassasiyet"))
        layout.addWidget(self.precision)
        layout.addWidget(self.api_status)
        layout.addWidget(btn)

        self.setLayout(layout)

    def apply(self):
        p = self.parent()
        p.set_theme(self.theme.currentText())
        p.set_precision(int(self.precision.currentText()))

        tab_map = {"Currency": 0, "Portfolio": 1, "Madenler": 2}
        p.tabs.setCurrentIndex(tab_map[self.start_tab.currentText()])

        self.close()


# ---------------- MAIN ----------------
class App(QWidget):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Finance Terminal")
        self.setGeometry(200, 200, 460, 520)

        self.theme = "Dark"
        self.precision = 2
        self.api_status = "..."

        self.tabs = QTabWidget()

        # TAB1
        self.tab1 = QWidget()
        l1 = QVBoxLayout()

        self.usd = Card("USD/TRY")
        self.eur = Card("EUR/TRY")
        self.huf = Card("HUF/TRY")

        self.mode_box = QComboBox()
        self.mode_box.addItems(["Normal", "Ters"])
        self.mode_box.currentIndexChanged.connect(self.refresh_ui_only)

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

        self.tab2 = Portfolio()
        self.tab3 = Metals()

        self.tabs.addTab(self.tab1, "Currency")
        self.tabs.addTab(self.tab2, "Portfolio")
        self.tabs.addTab(self.tab3, "Madenler")

        layout = QVBoxLayout()
        layout.addWidget(self.tabs)
        self.setLayout(layout)

        self.apply_theme()
        self.update()

    def refresh_ui_only(self):
        if hasattr(self, "last_data"):
            self.on_data(self.last_data)

            # animasyon
            self.usd.flash()
            self.eur.flash()
            self.huf.flash()

            # glow
            self.usd.highlight()
            self.eur.highlight()
            self.huf.highlight()

    def open_settings(self):
        SettingsDialog(self).exec()

    def set_theme(self, t):
        self.theme = t
        self.apply_theme()

    def set_precision(self, p):
        self.precision = p
        self.tab2.set_precision(p)
        self.tab3.set_precision(p)

    def apply_theme(self):
        if self.theme == "Dark":
            self.setStyleSheet("""
                QWidget { background:#121212; color:white; }
                QPushButton { background:#2a2a2a; color:white; }
                QLineEdit {
                    background:#2a2a2a;
                    color:white;
                    border:1px solid #444;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget { background:#0f172a; color:white; }
                QPushButton { background:#3a86ff; color:white; }
                QLineEdit {
                    background:#1a1f2e;
                    color:white;
                    border:1px solid #3a86ff;
                }
            """)

        self.usd.apply_theme(self.theme)
        self.eur.apply_theme(self.theme)
        self.huf.apply_theme(self.theme)

    def update(self):
        if hasattr(self, "worker") and self.worker.isRunning():
            return  # thread çalışıyorsa yenisini başlatma

        self.worker = Worker()
        self.worker.result.connect(self.on_data)
        self.worker.start()

    def on_data(self, d):
        self.last_data = d
        self.api_status = d.get("status")
        
        mode = self.mode_box.currentText()

        if mode == "Ters":
            usd = 1 / d['USD'] if d['USD'] else None
            eur = 1 / d['EUR'] if d['EUR'] else None
            huf = 1 / d['HUF'] if d['HUF'] else None

            self.usd.title.setText("TRY/USD")
            self.eur.title.setText("TRY/EUR")
            self.huf.title.setText("TRY/HUF")

            self.usd.value.setText(f"{safe_format(usd, self.precision)} USD")
            self.eur.value.setText(f"{safe_format(eur, self.precision)} EUR")
            self.huf.value.setText(f"{safe_format(huf, self.precision)} HUF")
        
        else:
            self.usd.title.setText("USD/TRY")
            self.eur.title.setText("EUR/TRY")
            self.huf.title.setText("HUF/TRY")

            self.usd.value.setText(f"{safe_format(d['USD'], self.precision)} TRY")
            self.eur.value.setText(f"{safe_format(d['EUR'], self.precision)} TRY")
            self.huf.value.setText(f"{safe_format(d['HUF'], self.precision)} TRY")


        self.tab2.set_rates(d)

        usd_try = d.get("USD")

        gold_try = d.get("gold") * usd_try if d.get("gold") and usd_try else 0
        silver_try = d.get("silver") * usd_try if d.get("silver") and usd_try else 0

        self.tab3.set_rates(gold_try, silver_try)

        self.last.setText(f"Güncelleme: {datetime.now().strftime('%H:%M:%S')}")


app = QApplication(sys.argv)
w = App()
w.show()
sys.exit(app.exec())