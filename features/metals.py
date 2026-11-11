from decimal import Decimal

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

from features.investment_panel import InvestmentPanel
from features.investment_store import format_localized, format_quantity, parse_localized_decimal

GRAM_PER_OZ = Decimal("31.1035")


class Metals(QWidget):
    """Metal value calculator plus persistent gold/silver purchase records."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.gold_input = QLineEdit()
        self.gold_input.setPlaceholderText("Örn. 1.250,5000")
        self.silver_input = QLineEdit()
        self.silver_input.setPlaceholderText("Örn. 10.000,0000")
        self.gold_input.editingFinished.connect(lambda: self._format_quantity_input(self.gold_input))
        self.silver_input.editingFinished.connect(lambda: self._format_quantity_input(self.silver_input))

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

        self.gold_usd_oz = Decimal("0")
        self.silver_usd_oz = Decimal("0")
        self.usd_try = Decimal("0")
        self.eur_try = Decimal("0")

        self.investment_panel = InvestmentPanel(
            asset_group="metals",
            assets={"XAU": ("Altın", "gr"), "XAG": ("Gümüş", "gr")},
            quantity_label="Miktar (gr)",
            title="Altın / Gümüş Alım Kayıtları",
            export_filename="FinanceTerminal_Metal_Portfoyu.xlsx",
        )
        layout.addWidget(self.investment_panel)

    @staticmethod
    def _format_quantity_input(field: QLineEdit) -> None:
        if not field.text().strip():
            return
        try:
            field.setText(format_quantity(parse_localized_decimal(field.text())))
        except ValueError:
            pass

    def set_rates(
        self, gold_usd_oz, silver_usd_oz, usd_try, eur_try=None,
        rates_updated_at=None, rates_status=None,
    ):
        self.gold_usd_oz = self._to_decimal(gold_usd_oz)
        self.silver_usd_oz = self._to_decimal(silver_usd_oz)
        self.usd_try = self._to_decimal(usd_try)
        self.eur_try = self._to_decimal(eur_try)

        prices = {}
        prices["XAU"] = (
            (self.gold_usd_oz / GRAM_PER_OZ) * self.usd_try
            if self.gold_usd_oz > 0 and self.usd_try > 0 else None
        )
        prices["XAG"] = (
            (self.silver_usd_oz / GRAM_PER_OZ) * self.usd_try
            if self.silver_usd_oz > 0 and self.usd_try > 0 else None
        )
        self.investment_panel.set_prices(
            prices, rates_updated_at=rates_updated_at, rates_status=rates_status
        )

    @staticmethod
    def _to_decimal(value) -> Decimal:
        try:
            amount = Decimal(str(value)) if value is not None else Decimal("0")
            return amount if amount.is_finite() and amount > 0 else Decimal("0")
        except Exception:
            return Decimal("0")

    def calc(self):
        try:
            gold_g = parse_localized_decimal(self.gold_input.text()) if self.gold_input.text().strip() else Decimal("0")
            silver_g = parse_localized_decimal(self.silver_input.text()) if self.silver_input.text().strip() else Decimal("0")
            total_usd = (
                (gold_g / GRAM_PER_OZ) * self.gold_usd_oz
                + (silver_g / GRAM_PER_OZ) * self.silver_usd_oz
            )
            total_try = total_usd * self.usd_try

            selected = self.out_currency.currentText()
            if selected == "TRY":
                converted = total_try
            elif selected == "USD":
                converted = total_try / self.usd_try if self.usd_try > 0 else None
            else:
                converted = total_try / self.eur_try if self.eur_try > 0 else None

            if converted is None:
                self.result.setText(f"{format_localized(total_try)} TRY | {selected}: Kur yok")
            else:
                self.result.setText(
                    f"{format_localized(total_try)} TRY | {format_localized(converted)} {selected}"
                )
        except Exception as exc:
            self.result.setText(f"Hata: {exc}")
