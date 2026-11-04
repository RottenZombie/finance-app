from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

from features.investment_panel import InvestmentPanel


class Portfolio(QWidget):
    """Currency calculator plus a persistent foreign-currency investment register."""

    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        self.usd = QLineEdit()
        self.eur = QLineEdit()
        self.huf = QLineEdit()
        self.try_in = QLineEdit()
        self.out_currency = QComboBox()
        self.out_currency.addItems(["EUR", "USD", "HUF"])

        self.result = QLabel("Sonuç: -")

        btn = QPushButton("Hesapla")
        btn.clicked.connect(self.calc)

        layout.addWidget(QLabel("USD"))
        layout.addWidget(self.usd)
        layout.addWidget(QLabel("EUR"))
        layout.addWidget(self.eur)
        layout.addWidget(QLabel("HUF"))
        layout.addWidget(self.huf)
        layout.addWidget(QLabel("TRY"))
        layout.addWidget(self.try_in)
        layout.addWidget(QLabel("Çıktı Para Birimi (TRY yanına)"))
        layout.addWidget(self.out_currency)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.rates = {}
        self.investment_panel = InvestmentPanel(
            asset_group="currency",
            assets={
                "USD": ("ABD Doları", "USD"),
                "EUR": ("Euro", "EUR"),
                "HUF": ("Macar Forinti", "HUF"),
            },
            quantity_label="Miktar",
            title="Döviz Alım Kayıtları",
            export_filename="FinanceTerminal_Doviz_Portfoyu.xlsx",
        )
        layout.addWidget(self.investment_panel)

    def set_rates(self, rates):
        self.rates = rates or {}
        self.investment_panel.set_prices(
            {
                "USD": self.rates.get("USD"),
                "EUR": self.rates.get("EUR"),
                "HUF": self.rates.get("HUF"),
            },
            rates_updated_at=self.rates.get("fetched_at"),
            rates_status=self.rates.get("status"),
        )

    def calc(self):
        try:
            usd = float(self.usd.text() or 0)
            eur = float(self.eur.text() or 0)
            huf = float(self.huf.text() or 0)
            try_value = float(self.try_in.text() or 0)

            usd_rate = self.rates.get("USD") or 0
            eur_rate = self.rates.get("EUR") or 0
            huf_rate = self.rates.get("HUF") or 0

            total_try = (
                usd * usd_rate
                + eur * eur_rate
                + huf * huf_rate
                + try_value
            )

            selected = self.out_currency.currentText()
            if selected == "USD":
                result = total_try / usd_rate if usd_rate else 0
            elif selected == "EUR":
                result = total_try / eur_rate if eur_rate else 0
            else:
                result = total_try / huf_rate if huf_rate else 0

            self.result.setText(f"{total_try:.2f} TRY | {result:.2f} {selected}")
        except Exception as exc:
            self.result.setText(f"Hata: {exc}")
