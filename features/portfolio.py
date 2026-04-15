from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox


class Portfolio(QWidget):
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

    def set_rates(self, r):
        self.rates = r

    def calc(self):
        try:
            usd = float(self.usd.text() or 0)
            eur = float(self.eur.text() or 0)
            huf = float(self.huf.text() or 0)

            # ⚠️ TRY input varsa al
            try_value = float(self.try_in.text() or 0)

            usd_rate = self.rates.get("USD") or 0
            eur_rate = self.rates.get("EUR") or 0
            huf_rate = self.rates.get("HUF") or 0

            total_try = (
                usd * usd_rate +
                eur * eur_rate +
                huf * huf_rate +
                try_value   # ✅ KRİTİK EKLENTİ
            )

            selected = self.out_currency.currentText()

            if selected == "USD":
                result = total_try / usd_rate if usd_rate else 0

            elif selected == "EUR":
                result = total_try / eur_rate if eur_rate else 0

            elif selected == "HUF":
                result = total_try / huf_rate if huf_rate else 0

            self.result.setText(
                f"{total_try:.2f} TRY | {result:.2f} {selected}"
            )

        except Exception as e:
            self.result.setText(f"Hata: {e}")