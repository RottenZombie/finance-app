from decimal import Decimal

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QLineEdit, QPushButton, QComboBox

from core.i18n import tr
from features.currencies import (
    DEFAULT_EXTRA_CURRENCY,
    currency_choices,
    currency_display_name,
    localized_currency_assets,
)
from features.investment_panel import InvestmentPanel
from features.investment_store import format_localized, parse_localized_decimal

FIXED_CALCULATOR_CURRENCIES = ("USD", "EUR")


def _fill_currency_combo(combo: QComboBox, codes: list[str]) -> None:
    for code in codes:
        combo.addItem(f"{code} — {currency_display_name(code)}", code)


def _select_code(combo: QComboBox, code: str) -> None:
    index = combo.findData(code)
    if index >= 0:
        combo.setCurrentIndex(index)


class Portfolio(QWidget):
    """Currency calculator plus a persistent foreign-currency investment register.

    The calculator has three fixed inputs (USD, EUR, TRY) and one extra currency
    the user can freely choose (default HUF), so any supported currency can be
    entered, not just displayed.
    """

    extra_currency_changed = Signal(str)

    def __init__(self, extra_currency: str = DEFAULT_EXTRA_CURRENCY):
        super().__init__()
        layout = QVBoxLayout(self)

        self.usd = QLineEdit()
        self.eur = QLineEdit()
        self.try_in = QLineEdit()
        self.extra = QLineEdit()
        for edit, placeholder in (
            (self.usd, tr("Örn. 1.250,00")),
            (self.eur, tr("Örn. 500,00")),
            (self.try_in, tr("Örn. 25.000,00")),
            (self.extra, tr("Örn. 100.000,00")),
        ):
            edit.setPlaceholderText(placeholder)
            edit.editingFinished.connect(lambda field=edit: self._format_money_input(field))

        # The extra currency: any supported currency except the two fixed ones.
        self.extra_currency = QComboBox()
        _fill_currency_combo(self.extra_currency, currency_choices(exclude=FIXED_CALCULATOR_CURRENCIES))
        wanted = str(extra_currency or DEFAULT_EXTRA_CURRENCY).upper()
        # An unknown/obsolete saved code must not silently pick the first list entry.
        _select_code(
            self.extra_currency,
            wanted if self.extra_currency.findData(wanted) >= 0 else DEFAULT_EXTRA_CURRENCY,
        )
        self.extra_currency.currentIndexChanged.connect(
            lambda _index: self.extra_currency_changed.emit(self.selected_extra_code())
        )

        self.out_currency = QComboBox()
        _fill_currency_combo(self.out_currency, currency_choices())
        _select_code(self.out_currency, "EUR")
        self.result = QLabel(tr("Sonuç: -"))

        btn = QPushButton(tr("Hesapla"))
        btn.clicked.connect(self.calc)

        for label, field in (("USD", self.usd), ("EUR", self.eur), ("TRY", self.try_in)):
            layout.addWidget(QLabel(label))
            layout.addWidget(field)
        layout.addWidget(QLabel(tr("Ek para birimi (listeden değiştirebilirsiniz)")))
        layout.addWidget(self.extra_currency)
        layout.addWidget(self.extra)
        layout.addWidget(QLabel(tr("Çıktı Para Birimi")))
        layout.addWidget(self.out_currency)
        layout.addWidget(btn)
        layout.addWidget(self.result)

        self.rates: dict[str, object] = {}
        self.investment_panel = InvestmentPanel(
            asset_group="currency",
            assets=localized_currency_assets(),
            quantity_label=tr("Miktar"),
            title=tr("Döviz Alım Kayıtları"),
            export_filename=tr("FinanceTerminal_Doviz_Portfoyu.xlsx"),
        )
        layout.addWidget(self.investment_panel)

    def selected_extra_code(self) -> str:
        return str(self.extra_currency.currentData() or DEFAULT_EXTRA_CURRENCY)

    def selected_output_code(self) -> str:
        return str(self.out_currency.currentData() or "EUR")

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

    def _rate(self, code: str) -> Decimal:
        if code == "TRY":
            return Decimal("1")
        raw = self.rates.get(code)
        try:
            parsed = Decimal(str(raw)) if raw is not None else Decimal("0")
        except Exception:
            return Decimal("0")
        return parsed if parsed.is_finite() and parsed > 0 else Decimal("0")

    def calc(self):
        try:
            def amount(field: QLineEdit) -> Decimal:
                return parse_localized_decimal(field.text()) if field.text().strip() else Decimal("0")

            extra_code = self.selected_extra_code()
            entries = (
                ("USD", amount(self.usd)),
                ("EUR", amount(self.eur)),
                (extra_code, amount(self.extra)),
            )
            # An amount in a currency without a rate must not silently count as zero.
            missing = [code for code, value in entries if value != 0 and self._rate(code) <= 0]
            if missing:
                self.result.setText(tr("Kur bilgisi yok: {0}").format(", ".join(missing)))
                return

            total_try = sum((value * self._rate(code) for code, value in entries), Decimal("0"))
            total_try += amount(self.try_in)

            selected = self.selected_output_code()
            selected_rate = self._rate(selected)
            if selected_rate <= 0:
                self.result.setText(tr("{0} TRY | {1}: Kur yok").format(format_localized(total_try), selected))
                return
            converted = total_try / selected_rate
            self.result.setText(
                f"{format_localized(total_try)} TRY | {format_localized(converted)} {selected}"
            )
        except Exception as exc:
            self.result.setText(tr("Hata: {0}").format(exc))
