from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTabWidget,
    QComboBox, QLabel, QPushButton, QDialog, QSizePolicy
)

from worker import Worker
from ui.card import Card
from features.metals import Metals
from features.portfolio import Portfolio
from settings import load, save


class MainWindow(QWidget):
    def __init__(self):
        super().__init__()

        # ---------------- SETTINGS ----------------
        self.VERSION = "2.1.2"
        self.settings = load()

        self.theme = self.settings.get("theme", "White")
        self.precision = self.settings.get("precision", 2)
        self.start_tab = self.settings.get("start_tab", 0)

        # ---------------- WINDOW BEHAVIOR ----------------
        self.setMinimumSize(400, 500)

        # ---------------- TABS ----------------
        self.tabs = QTabWidget()
        self.tabs.setCurrentIndex(self.start_tab)
        self.tabs.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        # ---------------- CURRENCY ----------------
        self.tab1 = QWidget()
        l1 = QVBoxLayout(self.tab1)

        self.usd = Card("USD/TRY")
        self.eur = Card("EUR/TRY")
        self.huf = Card("HUF/TRY")

        self.mode = QComboBox()
        self.mode.addItems(["Normal", "Ters"])
        self.mode.currentIndexChanged.connect(self.refresh)

        self.last = QLabel("-")

        btn = QPushButton("Güncelle")
        btn.clicked.connect(self.update)

        settings_btn = QPushButton("Ayarlar ⚙️")
        settings_btn.clicked.connect(self.open_settings)

        l1.addWidget(self.usd)
        l1.addWidget(self.eur)
        l1.addWidget(self.huf)
        l1.addWidget(self.mode)
        l1.addWidget(self.last)
        l1.addWidget(btn)
        l1.addWidget(settings_btn)

        l1.addStretch()

        # ---------------- OTHER TABS ----------------
        self.portfolio = Portfolio()
        self.metals = Metals()

        self.tabs.addTab(self.tab1, "Currency")
        self.tabs.addTab(self.portfolio, "Portfolio")
        self.tabs.addTab(self.metals, "Metals")

        layout = QVBoxLayout(self)
        layout.addWidget(self.tabs)

        self.apply_theme()
        self.update()

    # ---------------- FORMAT ----------------
    def fmt(self, v):
        if v is None:
            return "N/A"
        return f"{v:.{self.precision}f}"

    # ---------------- UPDATE ----------------
    def update(self):
        self.worker = Worker()
        self.worker.result.connect(self.on_data)
        self.worker.start()

    # ---------------- DATA ----------------
    def on_data(self, d):
        self.last_data = d

        if self.mode.currentText() == "Ters":
            self.usd.title.setText("TRY/USD")
            self.eur.title.setText("TRY/EUR")
            self.huf.title.setText("TRY/HUF")

            self.usd.value.setText(self.fmt(1 / d["USD"]))
            self.eur.value.setText(self.fmt(1 / d["EUR"]))
            self.huf.value.setText(self.fmt(1 / d["HUF"]))
        else:
            self.usd.title.setText("USD/TRY")
            self.eur.title.setText("EUR/TRY")
            self.huf.title.setText("HUF/TRY")

            self.usd.value.setText(self.fmt(d["USD"]))
            self.eur.value.setText(self.fmt(d["EUR"]))
            self.huf.value.setText(self.fmt(d["HUF"]))

        self.portfolio.set_rates(d)
        self.metals.set_rates(
            d.get("gold"),
            d.get("silver"),
            d.get("USD")
        )
    
        self.last.setText(d.get("status", "-"))

    # ---------------- REFRESH ----------------
    def refresh(self):
        if hasattr(self, "last_data"):
            self.on_data(self.last_data)

    # ---------------- THEME ----------------
    def apply_theme(self):
        if self.theme == "Dark":
            self.setStyleSheet("""
                QWidget { background:#121212; color:white; }
                QPushButton { background:#2a2a2a; color:white; }
                QLineEdit { background:#2a2a2a; color:white; }
            """)

        elif self.theme == "Blue":
            self.setStyleSheet("""
                QWidget { background:#0f172a; color:white; }
                QPushButton { background:#3a86ff; color:white; }
                QLineEdit { background:#1a1f2e; color:white; }
            """)

        elif self.theme == "White":
            self.setStyleSheet("""
                QWidget { background:#f5f5f5; color:#111; }
                QPushButton { 
                    background:#e0e0e0; color:#111; 
                    border:1px solid;
                }
                QLineEdit {
                    background:white;
                    color:black;
                    border:1px solid #ccc;
                }
                QLabel { color:#111; }
                QTabWidget::pane { border:1px solid #ccc; }
            """)

    # ---------------- SETTINGS ----------------
    def open_settings(self):
        dlg = QDialog(self)
        dlg.setWindowTitle("Ayarlar")
        dlg.setFixedSize(300, 200)

        layout = QVBoxLayout()

        version = QLabel(f"Version: {self.VERSION}")

        start_tab = QComboBox()
        start_tab.addItems(["Currency", "Portfolio", "Metals"])
        start_tab.setCurrentIndex(self.tabs.currentIndex())

        precision = QComboBox()
        precision.addItems(["2", "3", "4"])
        precision.setCurrentText(str(self.precision))

        theme = QComboBox()
        theme.addItems(["Dark", "Blue", "White"])
        theme.setCurrentText(self.theme)

        btn = QPushButton("Kaydet")

        def save_all():
            self.precision = int(precision.currentText())

            tab_map = {"Currency": 0, "Portfolio": 1, "Metals": 2}
            self.tabs.setCurrentIndex(tab_map[start_tab.currentText()])
            self.theme = theme.currentText()

            self.settings["precision"] = self.precision
            self.settings["start_tab"] = self.tabs.currentIndex()
            self.settings["theme"] = self.theme
            self.apply_theme()
            save(self.settings)

            dlg.close()

        btn.clicked.connect(save_all)

        layout.addWidget(version)
        layout.addWidget(QLabel("Başlangıç Sekmesi"))
        layout.addWidget(start_tab)
        layout.addWidget(QLabel("Hassasiyet"))
        layout.addWidget(precision)
        layout.addWidget(btn)
        layout.addWidget(QLabel("Tema"))
        layout.addWidget(theme)

        dlg.setLayout(layout)
        dlg.exec()