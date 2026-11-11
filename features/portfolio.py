from decimal import Decimal

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

from features.currencies import CURRENCY_INFO
from features.investment_panel import InvestmentPanel
from features.investment_store import format_localized, parse_localized_decimal


class Portfolio(QWidget):
    """Currency calculator plus a persistent foreign-currency investment register."""

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.usd = QLineEdit()
        self.eur = QLineEdit()
        self.huf = QLineEdit()
        self.try_in = QLineEdit()
        for edit, placeholder in (
            (self.usd, "Örn. 1.250,00"),
            (self.eur, "Örn. 500,00"),
            (self.huf, "Örn. 100.000,00"),
            (self.try_in, "Örn. 25.000,00"),
        ):
            edit.setPlaceholderText(placeholder)
            edit.editingFinished.connect(lambda field=edit: self._format_money_input(field))

        self.out_currency = QComboBox()
        self.out_currency.addItems(list(CURRENCY_INFO))
        self.out_currency.setCurrentText("EUR")
        self.result = QLabel("Sonuç: -")

        btn = QPushButton("Hesapla")
        btn.clicked.connect(self.calc)

        for label, field in (("USD", self.usd), ("EUR", self.eur), ("HUF", self.huf), ("TRY", self.try_in)):
            layout.addWidget(QLabel(label))
            layout.addWidget(field)
        layout.addWidget(QLabel("Çıktı Para Birimi"))
        layout.addWidget(self.out_currency)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.rates: dict[str, object] = {}
        self.investment_panel = InvestmentPanel(
            asset_group="currency",
            assets=CURRENCY_INFO,
            quantity_label="Miktar",
            title="Döviz Alım Kayıtları",
            export_filename="FinanceTerminal_Doviz_Portfoyu.xlsx",
        )
        layout.addWidget(self.investment_panel)

    @staticmethod
    def _format_money_input(field: QLineEdit) -> None:
        if not field.text().strip():
            return
        try:
            field.setText(format_localized(parse_localized_decimal(field.text()), decimals=2))
        except ValueError:
            # Leave invalid input visible so calc() can report a useful message.
            pass

    def set_rates(self, rates):
        self.rates = rates or {}
        self.investment_panel.set_prices(
            {code: self.rates.get(code) for code in self.investment_panel.assets},
            rates_updated_at=self.rates.get("fetched_at"),
            rates_status=self.rates.get("status"),
        )

    def calc(self):
        try:
            def amount(field: QLineEdit) -> Decimal:
                return parse_localized_decimal(field.text()) if field.text().strip() else Decimal("0")

            usd = amount(self.usd)
            eur = amount(self.eur)
            huf = amount(self.huf)
            try_value = amount(self.try_in)

            def rate(code: str) -> Decimal:
                raw = self.rates.get(code)
                parsed = Decimal(str(raw)) if raw is not None else Decimal("0")
                return parsed if parsed > 0 else Decimal("0")

            usd_rate = rate("USD")
            eur_rate = rate("EUR")
            huf_rate = rate("HUF")
            total_try = usd * usd_rate + eur * eur_rate + huf * huf_rate + try_value

            selected = self.out_currency.currentText()
            selected_rate = rate(selected)
            if selected_rate <= 0:
                self.result.setText(f"{format_localized(total_try)} TRY | {selected}: Kur yok")
                return
            converted = total_try / selected_rate
            self.result.setText(
                f"{format_localized(total_try)} TRY | {format_localized(converted)} {selected}"
            )
        except Exception as exc:
            self.result.setText(f"Hata: {exc}")
