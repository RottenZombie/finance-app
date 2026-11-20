from __future__ import annotations

from decimal import Decimal
from typing import Any

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QGridLayout, QLabel, QVBoxLayout, QWidget

from features.summary_math import calculate_portfolio_totals, convert_try_total
from features.investment_store import format_localized
from core.i18n import tr


def format_profit_loss(value: Decimal) -> str:
    sign = "+" if value > 0 else ""
    return f"{sign}{format_localized(value)} ₺"


class SummaryPage(QWidget):
    """Simple live portfolio totals in TRY, EUR and USD."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._value_labels: dict[tuple[str, str], QLabel] = {}
        self._bist_name_label: QLabel | None = None
        self._bist_warning: QLabel | None = None
        self._build_ui()
        self.update_summary(
            currency_holdings=[], currency_prices={}, metal_holdings=[],
            metal_prices={}, bist_holdings=[], try_per_usd=None, try_per_eur=None,
        )

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(20, 18, 20, 20)
        root.setSpacing(12)

        title = QLabel(tr("Portföy Özeti"))
        title.setObjectName("summaryTitle")
        root.addWidget(title)

        subtitle = QLabel(tr("Döviz ve maden güncel piyasa değeriyle gösterilir. BIST hisseleri güncel fiyat alındığında piyasa değeriyle, alınamadığında kayıtlı alış maliyetiyle gösterilir."))
        subtitle.setObjectName("summarySubtitle")
        subtitle.setWordWrap(True)
        root.addWidget(subtitle)

        frame = QFrame()
        frame.setObjectName("summaryFrame")
        grid = QGridLayout(frame)
        grid.setContentsMargins(16, 14, 16, 14)
        grid.setHorizontalSpacing(20)
        grid.setVerticalSpacing(14)

        headers = [tr("Portföy"), "TRY", "EUR", "USD", "K/Z (TRY)"]
        for col, text in enumerate(headers):
            label = QLabel(text)
            label.setObjectName("summaryHeader")
            label.setAlignment(Qt.AlignLeft if col == 0 else Qt.AlignRight | Qt.AlignVCenter)
            grid.addWidget(label, 0, col)

        rows = [
            ("currency", tr("Toplam Döviz")),
            ("metals", tr("Toplam Maden")),
            ("bist", tr("Toplam Hisse Senedi (maliyet)")),
            ("total", tr("GENEL TOPLAM*")),
        ]
        for row_index, (key, title_text) in enumerate(rows, start=1):
            name = QLabel(title_text)
            name.setObjectName("summaryTotalName" if key == "total" else "summaryRowName")
            grid.addWidget(name, row_index, 0)
            if key == "bist":
                self._bist_name_label = name
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
        # Names the shares whose price could not be fetched (hidden when all is well).
        self._bist_warning = QLabel("")
        self._bist_warning.setObjectName("summaryWarning")
        self._bist_warning.setWordWrap(True)
        self._bist_warning.setStyleSheet("color: #b45309; font-weight: 600;")
        self._bist_warning.setVisible(False)
        root.addWidget(self._bist_warning)
        note = QLabel(
            tr("K/Z sütunu gerçekleşmemiş kâr/zararı TL olarak gösterir. BIST hisselerinin kâr/zararı güncel fiyatı alınabilen hisseleri kapsar; fiyatı alınamayan hisseler uyarıda belirtilir, kayıtlı alış maliyetiyle toplanır ve kâr/zarara dahil edilmez. Hisse fiyatları gecikmeli ve resmi olmayan kaynaklardan gelir. Döviz veya maden grubunda bir varlığın güncel fiyatı eksikse o grubun toplamı ve K/Z değeri eksik gösterilir; eksik fiyat varsayılarak kâr hesaplanmaz.")
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
        bist_prices: dict[str, Decimal | None] | None = None,
    ) -> None:
        totals = calculate_portfolio_totals(
            currency_holdings=currency_holdings,
            currency_prices=currency_prices,
            metal_holdings=metal_holdings,
            metal_prices=metal_prices,
            bist_holdings=bist_holdings,
            bist_prices=bist_prices,
        )
        coverage = totals.get("bist_coverage", "none")
        if self._bist_name_label is not None:
            self._bist_name_label.setText({
                "full": tr("Toplam Hisse Senedi (güncel)"),
                "partial": tr("Toplam Hisse Senedi (kısmen güncel)"),
            }.get(coverage, tr("Toplam Hisse Senedi (maliyet)")))
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
            if row_key == "bist" and coverage == "partial" and value is not None:
                text = tr("{0} (kısmi)").format(format_profit_loss(value))
            elif row_key == "bist" and coverage == "none" and bist_holdings:
                text = tr("Canlı fiyat yok")
            elif value is None:
                text = tr("Veri yok")
            else:
                text = format_profit_loss(value)
            label = self._value_labels[(row_key, "PL")]
            label.setText(text)
            if value is not None:
                color = "#16a34a" if value >= 0 else "#dc2626"
                label.setStyleSheet(f"font-weight: 700; color: {color};")
            else:
                label.setStyleSheet("")

        self._update_bist_warning(
            totals.get("bist_missing", []), coverage, lookup_done=bist_prices is not None
        )

    def _update_bist_warning(self, missing: list[str], coverage: str, *, lookup_done: bool) -> None:
        """Warn about shares without a price instead of hiding every result."""
        if self._bist_warning is None:
            return
        # Before the first price lookup finishes nothing is "missing" yet.
        if not lookup_done or not missing or coverage not in ("partial", "none"):
            self._bist_warning.setText("")
            self._bist_warning.setVisible(False)
            return
        names = ", ".join(missing)
        if coverage == "partial":
            text = (
                tr("⚠ Şu hisse senetlerinin fiyatı alınamıyor: {0}. Bu hisseler kayıtlı alış maliyetiyle toplandı; BIST kâr/zararı yalnızca fiyatı alınan hisseleri kapsar.").format(names)
            )
        else:
            text = (
                tr("⚠ Hiçbir hisse için güncel fiyat alınamadı ({0}). Hisseler kayıtlı alış maliyetiyle gösteriliyor; kâr/zarar hesaplanamadı.").format(names)
            )
        self._bist_warning.setText(text)
        self._bist_warning.setVisible(True)
