from decimal import Decimal

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

from core.i18n import tr
from features.currencies import currency_choices, currency_display_name, metal_assets
from features.investment_panel import InvestmentPanel
from features.investment_store import format_localized, format_quantity, parse_localized_decimal

GRAM_PER_OZ = Decimal("31.1035")


class Metals(QWidget):
    """Metal value calculator plus persistent gold/silver purchase records.

    The result can be shown in any supported currency (same list and order as
    every other currency drop-down), not only TRY/USD/EUR.
    """

    def __init__(self):
        super().__init__()
        layout = QVBoxLayout(self)

        self.gold_input = QLineEdit()
        self.gold_input.setPlaceholderText(tr("Örn. 1.250,5000"))
        self.silver_input = QLineEdit()
        self.silver_input.setPlaceholderText(tr("Örn. 10.000,0000"))
        self.gold_input.editingFinished.connect(lambda: self._format_quantity_input(self.gold_input))
        self.silver_input.editingFinished.connect(lambda: self._format_quantity_input(self.silver_input))

        self.out_currency = QComboBox()
        for code in currency_choices(include_try=True):
            self.out_currency.addItem(f"{code} — {currency_display_name(code)}", code)
        self.out_currency.setCurrentIndex(max(0, self.out_currency.findData("TRY")))
        self.result = QLabel(tr("Sonuç: -"))

        btn = QPushButton(tr("Hesapla"))
        btn.clicked.connect(self.calc)

        layout.addWidget(QLabel(tr("Altın (gram)")))
        layout.addWidget(self.gold_input)
        layout.addWidget(QLabel(tr("Gümüş (gram)")))
        layout.addWidget(self.silver_input)
        layout.addWidget(QLabel(tr("Çıktı")))
        layout.addWidget(self.out_currency)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.gold_usd_oz = Decimal("0")
        self.silver_usd_oz = Decimal("0")
        self.usd_try = Decimal("0")
        self.eur_try = Decimal("0")
        self.rates: dict = {}

        self.investment_panel = InvestmentPanel(
            asset_group="metals",
            assets=metal_assets(),
            quantity_label=tr("Miktar (gr)"),
            title=tr("Altın / Gümüş Alım Kayıtları"),
            export_filename=tr("FinanceTerminal_Metal_Portfoyu.xlsx"),
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
        rates_updated_at=None, rates_status=None, rates=None,
    ):
        """``rates`` is the full TRY-per-unit table; it feeds every output currency."""
        self.gold_usd_oz = self._to_decimal(gold_usd_oz)
        self.silver_usd_oz = self._to_decimal(silver_usd_oz)
        self.usd_try = self._to_decimal(usd_try)
        self.eur_try = self._to_decimal(eur_try)
        self.rates = dict(rates or {})

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

    def _try_per_unit(self, code: str) -> Decimal:
        """TRY value of one unit of ``code`` (0 when there is no rate)."""
        if code == "TRY":
            return Decimal("1")
        if code == "USD" and self.usd_try > 0:
            return self.usd_try
        if code == "EUR" and self.eur_try > 0:
            return self.eur_try
        return self._to_decimal(self.rates.get(code))

    def calc(self):
        try:
            gold_g = parse_localized_decimal(self.gold_input.text()) if self.gold_input.text().strip() else Decimal("0")
            silver_g = parse_localized_decimal(self.silver_input.text()) if self.silver_input.text().strip() else Decimal("0")
            total_usd = (
                (gold_g / GRAM_PER_OZ) * self.gold_usd_oz
                + (silver_g / GRAM_PER_OZ) * self.silver_usd_oz
            )
            total_try = total_usd * self.usd_try

            selected = str(self.out_currency.currentData() or "TRY")
            rate = self._try_per_unit(selected)
            if rate <= 0:
                self.result.setText(tr("{0} TRY | {1}: Kur yok").format(format_localized(total_try), selected))
                return
            converted = total_try / rate
            self.result.setText(
                f"{format_localized(total_try)} TRY | {format_localized(converted)} {selected}"
            )
        except Exception as exc:
            self.result.setText(tr("Hata: {0}").format(exc))
