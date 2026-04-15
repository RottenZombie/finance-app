from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

GRAM_PER_OZ = 31.1035


class Metals(QWidget):
    def __init__(self):
        super().__init__()

        layout = QVBoxLayout(self)

        # INPUTS
        self.gold_input = QLineEdit()
        self.gold_input.setPlaceholderText("Altın (gram)")

        self.silver_input = QLineEdit()
        self.silver_input.setPlaceholderText("Gümüş (gram)")

        # OUTPUT
        self.out_currency = QComboBox()
        self.out_currency.addItems(["TRY", "USD", "EUR"])

        self.result = QLabel("Sonuç: -")

        btn = QPushButton("Hesapla")
        btn.clicked.connect(self.calc)

        layout.addWidget(QLabel("Altın (gram)"))
        layout.addWidget(self.gold_input)

        layout.addWidget(QLabel("Gümüş (gram)"))
        layout.addWidget(self.silver_input)

        layout.addWidget(QLabel("Çıktı"))
        layout.addWidget(self.out_currency)

        layout.addWidget(btn)
        layout.addWidget(self.result)

        # API DATA
        self.gold_usd_oz = 0
        self.silver_usd_oz = 0
        self.usd_try = 0

    # API'den gelen ham veri
    def set_rates(self, gold_usd_oz, silver_usd_oz, usd_try):
        self.gold_usd_oz = gold_usd_oz or 0
        self.silver_usd_oz = silver_usd_oz or 0
        self.usd_try = usd_try or 0

    def calc(self):
        try:
            gold_g = float(self.gold_input.text() or 0)
            silver_g = float(self.silver_input.text() or 0)

            # gram → ons
            gold_oz = gold_g / GRAM_PER_OZ
            silver_oz = silver_g / GRAM_PER_OZ

            # USD değer
            gold_usd = gold_oz * self.gold_usd_oz
            silver_usd = silver_oz * self.silver_usd_oz

            total_usd = gold_usd + silver_usd
            total_try = total_usd * self.usd_try

            selected = self.out_currency.currentText()

            if selected == "TRY":
                result = total_try

            elif selected == "USD":
                result = total_usd

            elif selected == "EUR":
                result = total_usd * 0.92  # yaklaşık dönüşüm

            self.result.setText(
                f"{total_try:.2f} TRY | {result:.2f} {selected}"
            )

        except Exception as e:
            self.result.setText(f"Hata: {e}")