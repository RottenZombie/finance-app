from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QGridLayout,
    QFormLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QHeaderView,
    QFileDialog,
    QMessageBox,
    QAbstractItemView,
    QFrame,
    QDialog,
    QDialogButtonBox,
)

from .database import BistDatabase
from .excel_io import read_portfolio_excel, write_portfolio_excel
from features.export_dialog import EXPORT, TEMPLATE, ask_export_mode, run_template_export
from features.export_templates import write_bist_template
from .quotes import Quote, describe_quote, format_quote_time, quotes_from_payload
from .refresh_status import status_text, summarize_refresh
from .valuation import value_holdings
from .utils import format_quantity, format_tl, normalize_symbol, parse_localized_decimal
from core.i18n import tr, tr_noop
from features.dialogs import ask_question, ask_warning_question, localize_dialog_buttons, localize_message_buttons


class BistPortfolioTab(QWidget):
    """BIST holdings tab with delayed market prices. AI analysis is a later stage."""

    portfolio_changed = Signal()
    refresh_requested = Signal()

    COLUMNS = (
        tr_noop("Hisse"), tr_noop("Şirket"), tr_noop("Adet"), tr_noop("Ort. maliyet"), tr_noop("Toplam maliyet"), tr_noop("Güncel fiyat"),
        tr_noop("Piyasa değeri"), tr_noop("K/Z (TL)"), tr_noop("K/Z %"), tr_noop("Sektör"), tr_noop("Not"), tr_noop("Son güncelleme"),
    )
    NUMERIC_COLUMNS = (2, 3, 4, 5, 6, 7, 8)

    PROFIT_COLOR = "#16a34a"
    LOSS_COLOR = "#dc2626"

    def __init__(self, parent=None, database: BistDatabase | None = None):
        super().__init__(parent)
        self.database = database or BistDatabase()
        self._quotes: dict[str, Quote] = {}
        self._quote_info: dict | None = None
        self._refreshing = False
        self._status_text = ""
        self._changes: dict[str, Decimal] = {}  # price change in the last refresh
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel(tr("BIST AI · Portföy"))
        title.setObjectName("bistTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel(tr("Hisselerini kaydet, maliyetini takip et ve analiz modüllerine hazırla."))
        subtitle.setObjectName("bistSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.storage_label = QLabel(tr("Veriler bu bilgisayarda saklanır"))
        self.storage_label.setObjectName("bistStorageLabel")
        self.storage_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)
        header.addWidget(self.storage_label)
        root.addLayout(header)

        metrics = QGridLayout()
        metrics.setHorizontalSpacing(8)
        metrics.setVerticalSpacing(6)
        # Keep explicit references to both the card frames and their labels.
        # Returning only the QLabel from _metric_card allowed its local QFrame
        # parent to be garbage-collected, which deleted the underlying C++ label.
        self.count_card, self.count_value = self._metric_card(tr("Hisse sayısı"), "0")
        self.cost_card, self.cost_value = self._metric_card(tr("Toplam maliyet"), "0,00 ₺")
        self.market_card, self.market_value = self._metric_card(tr("Piyasa değeri"), tr("Fiyat yok"))
        self.pl_card, self.pl_value = self._metric_card(tr("Kâr / Zarar"), tr("Veri yok"))
        metrics.addWidget(self.count_card, 0, 0)
        metrics.addWidget(self.cost_card, 0, 1)
        metrics.addWidget(self.market_card, 0, 2)
        metrics.addWidget(self.pl_card, 0, 3)
        root.addLayout(metrics)

        form_frame = QFrame()
        form_frame.setObjectName("bistFormFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(10, 9, 10, 9)
        form_layout.setSpacing(7)
        form_title = QLabel(tr("Hisse kaydı"))
        form_title.setStyleSheet("font-weight: 700;")
        form_layout.addWidget(form_title)

        fields = QGridLayout()
        fields.setHorizontalSpacing(8)
        fields.setVerticalSpacing(6)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText(tr("Örn. ASELS"))
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText(tr("Şirket adı (isteğe bağlı)"))
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText(tr("Örn. 250"))
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText(tr("Örn. 74,50"))
        self.sector_input = QLineEdit()
        self.sector_input.setPlaceholderText(tr("Örn. Savunma"))
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText(tr("İsteğe bağlı not"))

        fields.addWidget(QLabel(tr("Hisse kodu *")), 0, 0)
        fields.addWidget(QLabel(tr("Şirket")), 0, 1)
        fields.addWidget(self.symbol_input, 1, 0)
        fields.addWidget(self.company_input, 1, 1)
        fields.addWidget(QLabel(tr("Adet *")), 2, 0)
        fields.addWidget(QLabel(tr("Ortalama maliyet (TL) *")), 2, 1)
        fields.addWidget(self.quantity_input, 3, 0)
        fields.addWidget(self.cost_input, 3, 1)
        fields.addWidget(QLabel(tr("Sektör")), 4, 0)
        fields.addWidget(QLabel(tr("Not")), 4, 1)
        fields.addWidget(self.sector_input, 5, 0)
        fields.addWidget(self.notes_input, 5, 1)
        form_layout.addLayout(fields)

        buttons = QHBoxLayout()
        self.save_button = QPushButton(tr("Ekle / Güncelle"))
        self.save_button.clicked.connect(self.save_holding)
        buttons.addWidget(self.save_button)
        buttons.addStretch(1)
        form_layout.addLayout(buttons)
        root.addWidget(form_frame)

        toolbar = QHBoxLayout()
        self.clear_button = QPushButton(tr("Formu Temizle"))
        self.clear_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton(tr("Seçili Kayıtları Sil"))
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_all_button = QPushButton(tr("Tüm Kayıtları Sil"))
        self.delete_all_button.clicked.connect(self.delete_all)
        self.refresh_prices_button = QPushButton(tr("Fiyatları Güncelle"))
        self.refresh_prices_button.clicked.connect(self.refresh_requested.emit)
        self.import_button = QPushButton(tr("Excel'den İçe Aktar"))
        self.import_button.clicked.connect(self.import_excel)
        self.export_button = QPushButton(tr("Excel'e Aktar"))
        self.export_button.clicked.connect(self.export_excel)
        toolbar.addWidget(self.clear_button)
        toolbar.addWidget(self.delete_button)
        toolbar.addWidget(self.delete_all_button)
        toolbar.addWidget(self.refresh_prices_button)
        toolbar.addStretch(1)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.export_button)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, len(self.COLUMNS))
        self.table.setHorizontalHeaderLabels([tr(title) for title in self.COLUMNS])
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        for column, width in enumerate((90, 220, 80, 110, 130, 110, 130, 120, 80, 130, 200, 115)):
            self.table.setColumnWidth(column, width)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.itemDoubleClicked.connect(self.edit_holding)
        root.addWidget(self.table, 1)

        # One clear line about the last price refresh (time, how many prices moved).
        self.price_status = QLabel(tr("Fiyatlar henüz alınmadı."))
        self.price_status.setObjectName("bistPriceStatus")
        self.price_status.setWordWrap(True)
        self.price_status.setStyleSheet("font-weight: 600;")
        root.addWidget(self.price_status)
        self.notice = QLabel("")
        self.notice.setObjectName("bistNotice")
        self.notice.setWordWrap(True)
        root.addWidget(self.notice)
        self._update_notice()

    def _metric_card(self, label_text: str, initial_value: str) -> tuple[QFrame, QLabel]:
        frame = QFrame()
        frame.setObjectName("bistMetricCard")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 7, 10, 7)
        caption = QLabel(label_text)
        caption.setObjectName("bistMetricCaption")
        value = QLabel(initial_value)
        value.setObjectName("bistMetricValue")
        value.setStyleSheet("font-size: 17px; font-weight: 700;")
        layout.addWidget(caption)
        layout.addWidget(value)
        return frame, value

    def _set_metric(self, metric_label: QLabel, text: str) -> None:
        metric_label.setText(text)

    # ------------------------------------------------------------ prices
    def set_quotes(self, payload: dict | None) -> None:
        """Receive the quote payload produced by the refresh worker."""
        previous = self._quotes
        self._quotes = quotes_from_payload(payload)
        info = payload if isinstance(payload, dict) else {}
        self._quote_info = {
            "live": len(info.get("live") or []),
            "cached": len(info.get("cached") or []),
            "failed": list(info.get("failed") or []),
        }
        summary = summarize_refresh(previous, self._quotes, info)
        self._changes = dict(summary.changes)
        self._status_text = status_text(summary)
        self._refreshing = False
        self._apply_refresh_state()
        self._update_notice()
        self.refresh_table()
        self.portfolio_changed.emit()

    def set_refreshing(self, active: bool) -> None:
        """Show that a price refresh is running (button + status line)."""
        self._refreshing = bool(active)
        self._apply_refresh_state()

    def show_no_holdings(self) -> None:
        self._refreshing = False
        self._status_text = tr("Fiyat alınacak hisse yok. Önce bir hisse ekleyin.")
        self._apply_refresh_state()

    def _apply_refresh_state(self) -> None:
        self.refresh_prices_button.setEnabled(not self._refreshing)
        self.refresh_prices_button.setText(
            tr("Güncelleniyor…") if self._refreshing else tr("Fiyatları Güncelle")
        )
        if self._refreshing:
            self.price_status.setText(tr("Fiyatlar alınıyor…"))
        else:
            self.price_status.setText(self._status_text or tr("Fiyatlar henüz alınmadı."))

    def price_map(self) -> dict[str, Decimal] | None:
        """Current prices by ticker for the Summary tab.

        ``None`` means no price lookup has finished yet (so nothing is "missing"
        yet); an empty dict means a lookup ran but returned no price.
        """
        if self._quote_info is None:
            return None
        return {symbol: quote.price for symbol, quote in self._quotes.items()}

    def price_notes(self) -> dict[str, str]:
        """Where/when each price came from, for the Excel export."""
        return {symbol: describe_quote(quote) for symbol, quote in self._quotes.items()}

    def _update_notice(self) -> None:
        base = tr("Fiyatlar gecikmeli ve resmi olmayan kaynaklardan alınır; yatırım tavsiyesi değildir. KAP taraması ve yapay zekâ analizleri sonraki aşamada eklenecek.")
        if not self._quote_info:
            self.notice.setText(tr("Güncel fiyatlar için \"Fiyatları Güncelle\" düğmesini kullanın. ") + base)
        else:
            self.notice.setText(base)

    @staticmethod
    def _signed(value: Decimal) -> str:
        sign = "+" if value > 0 else ""
        return f"{sign}{format_tl(value)}"

    def _pl_color(self, value: Decimal | None) -> QBrush | None:
        if value is None or value == 0:
            return None
        return QBrush(QColor(self.PROFIT_COLOR if value > 0 else self.LOSS_COLOR))

    def refresh_table(self) -> None:
        holdings = self.database.list_holdings()
        valuation = value_holdings(holdings, self.price_map())
        self.table.setRowCount(len(holdings))

        for row_index, (holding, row) in enumerate(zip(holdings, valuation["rows"])):
            quote = self._quotes.get(holding["symbol"])
            price = row["price"]
            if price is None:
                price_text, value_text, pl_text, pct_text = "–", "–", "–", "–"
            else:
                price_text = f"{format_tl(price)} ₺" + (" (eski)" if quote and quote.stale else "")
                delta = self._changes.get(holding["symbol"])
                if delta:
                    price_text += " ▲" if delta > 0 else " ▼"
                value_text = f"{format_tl(row['market_value'])} ₺"
                pl_text = f"{self._signed(row['profit_loss'])} ₺"
                pct = row["profit_loss_pct"]
                pct_text = f"{self._signed(pct)} %" if pct is not None else "–"
            updated = str(holding.get("updated_at", ""))[:10]
            values = [
                holding["symbol"],
                holding.get("company", ""),
                format_quantity(row["quantity"]),
                f"{format_tl(row['average_cost'])} ₺",
                f"{format_tl(row['cost'])} ₺",
                price_text,
                value_text,
                pl_text,
                pct_text,
                holding.get("sector", ""),
                holding.get("notes", ""),
                updated,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in self.NUMERIC_COLUMNS:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, holding["symbol"])
                if column == 5 and quote is not None:
                    tip = tr("Kaynak: {0}\nFiyat zamanı: {1}").format(quote.source, format_quote_time(quote) or tr("bilinmiyor"))
                    delta = self._changes.get(holding["symbol"])
                    if delta is not None and price is not None:
                        tip += "\n" + tr("Önceki fiyat: {0}").format(format_tl(price - delta))
                    item.setToolTip(tip)
                if column in (7, 8):
                    brush = self._pl_color(row["profit_loss"])
                    if brush is not None:
                        item.setForeground(brush)
                self.table.setItem(row_index, column, item)

        summary = self.database.summary()
        self._set_metric(self.count_value, str(summary["holding_count"]))
        self._set_metric(self.cost_value, f"{format_tl(summary['total_cost'])} ₺")

        market_value = valuation["market_value"]
        if market_value is None:
            self._set_metric(self.market_value, tr("Fiyat yok"))
        elif valuation["complete"]:
            self._set_metric(self.market_value, f"{format_tl(market_value)} ₺")
        else:
            self._set_metric(
                self.market_value,
                tr("{0} ₺ (kısmi: {1}/{2})").format(format_tl(market_value), valuation['priced_count'], valuation['holding_count']),
            )
        profit_loss = valuation["profit_loss"]
        if profit_loss is None:
            self._set_metric(self.pl_value, tr("Veri yok"))
            self.pl_value.setStyleSheet("font-size: 17px; font-weight: 700;")
        else:
            pct = valuation["profit_loss_pct"]
            suffix = f" ({self._signed(pct)} %)" if pct is not None else ""
            if not valuation["complete"]:
                suffix += tr(" (kısmi)")
            self._set_metric(self.pl_value, f"{self._signed(profit_loss)} ₺{suffix}")
            color = "" if profit_loss == 0 else f" color: {self.PROFIT_COLOR if profit_loss > 0 else self.LOSS_COLOR};"
            self.pl_value.setStyleSheet(f"font-size: 17px; font-weight: 700;{color}")

    def save_holding(self) -> None:
        try:
            symbol = normalize_symbol(self.symbol_input.text())
            quantity = parse_localized_decimal(self.quantity_input.text(), field_name=tr("Adet"))
            average_cost = parse_localized_decimal(self.cost_input.text(), field_name=tr("Ortalama maliyet"))
            self.database.upsert_holding(
                symbol=symbol,
                company=self.company_input.text(),
                quantity=quantity,
                average_cost=average_cost,
                sector=self.sector_input.text(),
                notes=self.notes_input.text(),
            )
            self.refresh_table()
            self.portfolio_changed.emit()
            self.clear_form()
            QMessageBox.information(self, tr("BIST Portföy"), tr("{0} kaydı kaydedildi.").format(symbol))
        except Exception as exc:
            QMessageBox.warning(self, tr("Kayıt yapılamadı"), str(exc))

    def clear_form(self) -> None:
        for field in (
            self.symbol_input,
            self.company_input,
            self.quantity_input,
            self.cost_input,
            self.sector_input,
            self.notes_input,
        ):
            field.clear()
        self.symbol_input.setFocus()

    def _selected_symbols(self) -> list[str]:
        symbols: list[str] = []
        for index in self.table.selectionModel().selectedRows():
            item = self.table.item(index.row(), 0)
            if item is not None:
                symbol = item.data(Qt.UserRole)
                if symbol:
                    symbols.append(str(symbol))
        return list(dict.fromkeys(symbols))

    def edit_holding(self, item=None, *_args) -> None:
        """Edit a BIST row in a dedicated dialog, matching other portfolio tabs."""
        symbol = item.data(Qt.UserRole) if item is not None else None
        if not symbol:
            symbols = self._selected_symbols()
            if not symbols:
                return
            symbol = symbols[0]
        holding = self.database.get_holding(symbol)
        if not holding:
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("{0} kaydını düzenle").format(holding['symbol']))
        dialog.setMinimumWidth(390)
        root = QVBoxLayout(dialog)
        form = QFormLayout()

        symbol_edit = QLineEdit(str(holding["symbol"]))
        company_edit = QLineEdit(str(holding.get("company", "")))
        quantity_edit = QLineEdit(str(holding["quantity"]).replace(".", ","))
        cost_edit = QLineEdit(str(holding["average_cost"]).replace(".", ","))
        sector_edit = QLineEdit(str(holding.get("sector", "")))
        notes_edit = QLineEdit(str(holding.get("notes", "")))

        symbol_edit.setPlaceholderText(tr("Örn. ASELS"))
        company_edit.setPlaceholderText(tr("Şirket adı"))
        quantity_edit.setPlaceholderText(tr("Örn. 250"))
        cost_edit.setPlaceholderText(tr("Örn. 74,50"))
        sector_edit.setPlaceholderText(tr("Örn. Savunma"))
        notes_edit.setPlaceholderText(tr("İsteğe bağlı not"))

        form.addRow(tr("Hisse kodu *"), symbol_edit)
        form.addRow(tr("Şirket"), company_edit)
        form.addRow("Adet *", quantity_edit)
        form.addRow(tr("Ortalama maliyet (TL) *"), cost_edit)
        form.addRow(tr("Sektör"), sector_edit)
        form.addRow("Not", notes_edit)
        root.addLayout(form)

        hint = QLabel(tr("Hisse kodu dâhil tüm giriş alanlarını bu pencereden değiştirebilirsiniz."))
        hint.setWordWrap(True)
        hint.setStyleSheet("font-size: 10px;")
        root.addWidget(hint)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        localize_dialog_buttons(buttons)
        buttons.button(QDialogButtonBox.Save).setText(tr("Değişiklikleri Kaydet"))
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        root.addWidget(buttons)

        if dialog.exec() != QDialog.Accepted:
            return

        try:
            updated = self.database.update_holding(
                holding["symbol"],
                symbol=symbol_edit.text(),
                company=company_edit.text(),
                quantity=quantity_edit.text(),
                average_cost=cost_edit.text(),
                sector=sector_edit.text(),
                notes=notes_edit.text(),
            )
            self.refresh_table()
            self.portfolio_changed.emit()
            self.clear_form()
            QMessageBox.information(
                self, tr("BIST Portföy"), tr("{0} kaydı güncellendi.").format(updated['symbol'])
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Kayıt güncellenemedi"), str(exc))

    # Retain an explicit helper for code paths that may want to load a row into
    # the main form without opening the editor.
    def load_selected_to_form(self, item=None, *_args) -> None:
        symbol = item.data(Qt.UserRole) if item is not None else None
        if not symbol:
            symbols = self._selected_symbols()
            if not symbols:
                return
            symbol = symbols[0]
        holding = self.database.get_holding(symbol)
        if not holding:
            return
        self.symbol_input.setText(holding["symbol"])
        self.company_input.setText(holding.get("company", ""))
        self.quantity_input.setText(str(holding["quantity"]).replace(".", ","))
        self.cost_input.setText(str(holding["average_cost"]).replace(".", ","))
        self.sector_input.setText(holding.get("sector", ""))
        self.notes_input.setText(holding.get("notes", ""))

    def delete_selected(self) -> None:
        symbols = self._selected_symbols()
        if not symbols:
            QMessageBox.information(self, tr("BIST Portföy"), tr("Önce tablodan bir veya daha fazla hisse seç."))
            return
        answer = ask_question(
            self,
            tr("Seçili kayıtları sil"),
            tr("{0} seçili hisse kaydı silinecek:\n{1}\n\nDevam edilsin mi?").format(len(symbols), ', '.join(symbols)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.database.delete_holdings(symbols)
            self.refresh_table()
            self.portfolio_changed.emit()
            self.clear_form()

    def delete_all(self) -> None:
        holdings = self.database.list_holdings()
        if not holdings:
            QMessageBox.information(self, tr("Tüm kayıtları sil"), tr("BIST portföyünde silinecek kayıt yok."))
            return
        answer = ask_warning_question(
            self,
            tr("Tüm BIST kayıtlarını sil"),
            tr("{0} hisse kaydının tamamı kalıcı olarak silinecek.\n\nBu işlem geri alınamaz. Devam edilsin mi?").format(len(holdings)),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.database.delete_all()
            self.refresh_table()
            self.portfolio_changed.emit()
            self.clear_form()

    def import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            tr("Portföy Excel dosyasını seç"),
            str(Path.home()),
            tr("Excel dosyaları (*.xlsx)"),
        )
        if not path:
            return
        try:
            rows = read_portfolio_excel(path)
            imported, errors = self.database.import_rows(rows)
            self.refresh_table()
            if imported:
                self.portfolio_changed.emit()
            message = tr("{0} kayıt içe aktarıldı.").format(imported)
            if errors:
                message += tr("\n\nAtlanan satırlar:\n") + "\n".join(errors[:12])
                if len(errors) > 12:
                    message += tr("\n... ve {0} hata daha.").format(len(errors) - 12)
                QMessageBox.warning(self, tr("İçe aktarma tamamlandı"), message)
            else:
                QMessageBox.information(self, tr("İçe aktarma tamamlandı"), message)
        except Exception as exc:
            QMessageBox.warning(self, tr("Excel okunamadı"), str(exc))

    def export_excel(self) -> None:
        mode = ask_export_mode(self, tr("BIST portföyü"))
        if mode == TEMPLATE:
            run_template_export(
                self,
                caption=tr("BIST portföyü örnek şablonunu kaydet"),
                default_name="BIST_Portfoy_Ornek_Sablon.xlsx",
                writer=write_bist_template,
            )
            return
        if mode != EXPORT:
            return
        holdings = self.database.list_holdings()
        if not holdings:
            QMessageBox.information(self, tr("BIST Portföy"), tr("Dışa aktarılacak kayıt bulunmuyor."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Portföyü Excel olarak kaydet"),
            str(Path.home() / tr("BIST_Portfoy.xlsx")),
            tr("Excel dosyaları (*.xlsx)"),
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            write_portfolio_excel(
                path, holdings,
                prices=self.price_map() or None, price_notes=self.price_notes(),
                rates_updated_at=getattr(self, "rates_updated_at", None),
                rates_status=getattr(self, "rates_status", None),
            )
            QMessageBox.information(self, tr("Dışa aktarma tamamlandı"), tr("Dosya kaydedildi:\n{0}").format(path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Excel kaydedilemedi"), str(exc))
