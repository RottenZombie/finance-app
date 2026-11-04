from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from features.summary_math import calculate_portfolio_totals, convert_try_total
from features.investment_store import format_localized


def format_profit_loss(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{format_localized(value)} ₺"


class SummaryPage(QWidget):
    """Simple live portfolio totals in TRY, EUR and USD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_labels: dict[tuple[str, str], QLabel] = {}
        self._build_ui()
        self.update_summary(
            currency_holdings=[], currency_prices={}, metal_holdings=[],
            metal_prices={}, bist_holdings=[], try_per_usd=None, try_per_eur=None,
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        title = QLabel("Portföy Özeti")
        title.setObjectName("summaryTitle")
        root.addWidget(title)

        subtitle = QLabel("Döviz ve maden güncel değerleri, hisse senetleri kayıtlı maliyet üzerinden gösterilir.")
        subtitle.setObjectName("summarySubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        frame = QFrame()
        frame.setObjectName("summaryFrame")
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)

        headers = ["Portföy", "TRY", "EUR", "USD", "K/Z (TRY)"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("summaryHeader")
            label.setAlignment(Qt.AlignLeft if col == 0 else Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, 0, col)

        rows = [
            ("currency", "Toplam Döviz"),
            ("metals", "Toplam Maden"),
            ("bist", "Toplam Hisse Senedi*"),
            ("total", "GENEL TOPLAM"),
        ]
        for row_index, (key, title_text) in enumerate(rows, start=1):
            name = QLabel(title_text)
            name.setObjectName("summaryTotalName" if key == "total" else "summaryRowName")
            grid.addWidget(name, row_index, 0)
            for col, currency in enumerate(("TRY", "EUR", "USD"), start=1):
                value = QLabel("0,00")
                value.setObjectName("summaryTotalValue" if key == "total" else "summaryValue")
                value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
                grid.addWidget(value, row_index, col)
                self._value_labels[(key, currency)] = value

            profit_value = QLabel("0,00")
            profit_value.setObjectName("summaryProfitValue")
            profit_value.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(profit_value, row_index, 4)
            self._value_labels[(key, "PL")] = profit_value

        root.addWidget(frame)
        note = QLabel(
            "K/Z sütunu gerçekleşmemiş kâr/zararı TL olarak gösterir. Genel K/Z toplamı "
            "yalnızca güncel fiyatı bulunan Döviz ve Maden varlıklarını kapsar; BIST AI "
            "bölümünde canlı hisse fiyatı henüz bulunmadığı için hisse kâr/zararı hesaplanmaz. "
            "Hisse senedi toplamı kayıtlı alış maliyetidir."
        )
        note.setObjectName("summaryNote")
        note.setWordWrap(True)
        root.addWidget(note)
        root.addStretch(1)

    def update_summary(
        self,
        *,
        currency_holdings: list[dict[str, Any]],
        currency_prices: dict[str, Decimal | None],
        metal_holdings: list[dict[str, Any]],
        metal_prices: dict[str, Decimal | None],
        bist_holdings: list[dict[str, Any]],
        try_per_usd: Decimal | None,
        try_per_eur: Decimal | None,
    ) -> None:
        totals = calculate_portfolio_totals(
            currency_holdings=currency_holdings,
            currency_prices=currency_prices,
            metal_holdings=metal_holdings,
            metal_prices=metal_prices,
            bist_holdings=bist_holdings,
        )
        for key in ("currency", "metals", "bist", "total"):
            values = convert_try_total(
                totals[key], try_per_eur=try_per_eur, try_per_usd=try_per_usd
            )
            for currency, value in values.items():
                self._value_labels[(key, currency)].setText(value)

        profit_keys = {
            "currency": "currency_profit_loss",
            "metals": "metals_profit_loss",
            "bist": "bist_profit_loss",
            "total": "total_profit_loss",
        }
        for row_key, total_key in profit_keys.items():
            value = totals[total_key]
            if row_key == "bist" and bist_holdings:
                text = "Canlı fiyat yok"
            elif value is None:
                text = "Veri yok"
            else:
                text = format_profit_loss(value)
            label = self._value_labels[(row_key, "PL")]
            label.setText(text)
            if value is not None:
                color = "#16a34a" if value >= 0 else "#dc2626"
                label.setStyleSheet(f"font-weight: 700; color: {color};")
            else:
                label.setStyleSheet("")
