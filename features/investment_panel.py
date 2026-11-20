from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QFormLayout,
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QSizePolicy,
)

from features.investment_store import (
    InvestmentStore,
    format_localized,
    format_quantity,
    parse_localized_decimal,
    write_holdings_excel,
)
from features.investment_excel import read_investment_holdings_excel
from features.export_dialog import EXPORT, TEMPLATE, ask_export_mode, run_template_export
from features.export_templates import template_filename, write_investment_template
from core.i18n import tr, tr_noop
from features.dialogs import ask_question, ask_warning_question, localize_dialog_buttons, localize_message_buttons


class InvestmentPanel(QGroupBox):
    """Purchase registration and live valuation for a single asset group."""

    portfolio_changed = Signal()

    HEADERS = [
        tr_noop("Varlık"),
        tr_noop("Miktar"),
        tr_noop("Ort. Alış (₺)"),
        tr_noop("Toplam Maliyet (₺)"),
        tr_noop("Güncel Fiyat (₺)"),
        tr_noop("Güncel Değer (₺)"),
        tr_noop("Kâr / Zarar (₺)"),
        tr_noop("Kâr / Zarar (%)"),
    ]

    def __init__(
        self,
        *,
        asset_group: str,
        assets: dict[str, tuple[str, str]],
        quantity_label: str,
        title: str,
        export_filename: str,
        store: InvestmentStore | None = None,
        parent=None,
    ):
        super().__init__(title, parent)
        self.setObjectName("investmentPanel")
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.asset_group = asset_group
        self.assets = assets
        self.store = store or InvestmentStore()
        self.current_prices: dict[str, Decimal | None] = {code: None for code in assets}
        self.rates_updated_at: str | None = None
        self.rates_status: str | None = None
        self.export_filename = export_filename
        self._build_ui(quantity_label)
        self.refresh_table()

    def _build_ui(self, quantity_label: str) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(12, 18, 12, 10)
        root.setSpacing(9)
        form = QHBoxLayout()
        form.setContentsMargins(0, 0, 0, 0)
        form.setSpacing(8)

        self.asset_input = QComboBox()
        for code, (display_name, _unit) in self.assets.items():
            self.asset_input.addItem(display_name, code)

        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText(tr("Örn. 10"))
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText(tr("Örn. 32,50"))

        form.addWidget(QLabel(tr("Varlık")))
        form.addWidget(self.asset_input, 2)
        form.addWidget(QLabel(quantity_label))
        form.addWidget(self.quantity_input, 1)
        form.addWidget(QLabel(tr("Alış birim fiyatı (₺)")))
        form.addWidget(self.cost_input, 1)

        self.save_button = QPushButton(tr("Alımı Kaydet"))
        self.save_button.clicked.connect(self.save_purchase)
        form.addWidget(self.save_button)
        root.addLayout(form)

        self.info_label = QLabel(
            tr("Aynı varlığa yapılan yeni alımlar miktara eklenir ve ağırlıklı ortalama maliyet güncellenir.")
        )
        self.info_label.setObjectName("investmentInfo")
        self.info_label.setWordWrap(True)
        root.addWidget(self.info_label)

        self.last_update_label = QLabel(tr("Son güncelleme: Henüz veri alınmadı"))
        self.last_update_label.setObjectName("investmentLastUpdate")
        root.addWidget(self.last_update_label)

        action_row = QHBoxLayout()
        self.clear_button = QPushButton(tr("Formu Temizle"))
        self.clear_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton(tr("Seçili Kayıtları Sil"))
        self.delete_button.clicked.connect(self.delete_selected)
        self.delete_all_button = QPushButton(tr("Tüm Kayıtları Sil"))
        self.delete_all_button.clicked.connect(self.delete_all)
        self.import_button = QPushButton(tr("Excel'den İçe Aktar"))
        self.import_button.clicked.connect(self.import_excel)
        self.export_button = QPushButton(tr("Excel'e Aktar"))
        self.export_button.clicked.connect(self.export_excel)
        action_row.addWidget(self.clear_button)
        action_row.addWidget(self.delete_button)
        action_row.addWidget(self.delete_all_button)
        action_row.addStretch(1)
        action_row.addWidget(self.import_button)
        action_row.addWidget(self.export_button)
        root.addLayout(action_row)

        self.table = QTableWidget(0, len(self.HEADERS))
        self.table.setObjectName("investmentTable")
        self.table.setFrameShape(QFrame.Shape.NoFrame)
        self.table.setShowGrid(False)
        self.table.setAlternatingRowColors(True)
        self.table.setWordWrap(False)
        self.table.setHorizontalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setVerticalScrollBarPolicy(Qt.ScrollBarAsNeeded)
        self.table.setHorizontalHeaderLabels([tr(title) for title in self.HEADERS])
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.cellDoubleClicked.connect(self.edit_holding)
        self.table.verticalHeader().setVisible(False)
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.Interactive)
        header.setStretchLastSection(False)
        header.setMinimumSectionSize(78)
        header.setDefaultAlignment(Qt.AlignCenter)
        header.setFixedHeight(40)
        for column, width in enumerate((112, 88, 108, 132, 118, 132, 118, 108)):
            if column < self.table.columnCount():
                self.table.setColumnWidth(column, width)
        self.table.setMinimumHeight(230)
        self.table.verticalHeader().setDefaultSectionSize(36)
        root.addWidget(self.table, 1)

    def set_prices(
        self, prices: dict[str, object], rates_updated_at: str | None = None,
        rates_status: str | None = None,
    ) -> None:
        converted: dict[str, Decimal | None] = {}
        for code in self.assets:
            value = prices.get(code)
            try:
                price = Decimal(str(value)) if value is not None else None
                converted[code] = price if price is not None and price > 0 else None
            except Exception:
                converted[code] = None
        self.current_prices = converted
        if rates_updated_at:
            self.rates_updated_at = rates_updated_at
        if rates_status is not None:
            self.rates_status = rates_status
        self._refresh_update_label()
        self.refresh_table()

    def _refresh_update_label(self) -> None:
        updated = self.rates_updated_at or tr("Henüz veri alınmadı")
        status = self.rates_status or "Bilinmiyor"
        self.last_update_label.setText(
            tr("Son güncelleme: {0}  |  Veri durumu: {1}").format(updated, status)
        )

    def _selected_codes(self) -> list[str]:
        codes: list[str] = []
        for index in self.table.selectionModel().selectedRows():
            item = self.table.item(index.row(), 0)
            if item is not None:
                code = item.data(Qt.UserRole)
                if code:
                    codes.append(str(code))
        return list(dict.fromkeys(codes))

    def save_purchase(self) -> None:
        code = str(self.asset_input.currentData())
        display_name, unit = self.assets[code]
        try:
            quantity = parse_localized_decimal(self.quantity_input.text(), field_name="Miktar")
            unit_cost = parse_localized_decimal(self.cost_input.text(), field_name=tr("Alış birim fiyatı"))
            self.store.add_purchase(
                self.asset_group,
                code,
                quantity,
                unit_cost,
                display_name=display_name,
                unit=unit,
            )
            self.quantity_input.clear()
            self.cost_input.clear()
            self.refresh_table()
            self.portfolio_changed.emit()
            QMessageBox.information(self, tr("Kayıt başarılı"), tr("{0} alımı kaydedildi.\nYeni alımlar mevcut miktara eklenir.").format(display_name))
        except Exception as exc:
            QMessageBox.warning(self, tr("Kayıt yapılamadı"), str(exc))

    def refresh_table(self) -> None:
        holdings = self.store.list_holdings(self.asset_group)
        self.table.setRowCount(len(holdings))
        for row_index, holding in enumerate(holdings):
            code = holding["asset_code"]
            quantity = Decimal(holding["quantity"])
            average_cost = Decimal(holding["average_cost_try"])
            total_cost = quantity * average_cost
            current_price = self.current_prices.get(code)

            if current_price is not None:
                current_value = quantity * current_price
                profit_loss = current_value - total_cost
                profit_pct = (profit_loss / total_cost * Decimal("100")) if total_cost else Decimal("0")
                current_price_text = format_localized(current_price)
                current_value_text = format_localized(current_value)
                profit_loss_text = format_localized(profit_loss)
                profit_pct_text = f"{format_localized(profit_pct)}%"
            else:
                current_price_text = current_value_text = profit_loss_text = profit_pct_text = tr("Veri yok")

            values = [
                holding["display_name"],
                f"{format_quantity(quantity)} {holding['unit']}",
                format_localized(average_cost),
                format_localized(total_cost),
                current_price_text,
                current_value_text,
                profit_loss_text,
                profit_pct_text,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column == 0:
                    item.setData(Qt.UserRole, code)
                if column > 0:
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                self.table.setItem(row_index, column, item)

    def edit_holding(self, row: int, _column: int = 0) -> None:
        """Edit the selected holding snapshot instead of adding another purchase."""
        first_cell = self.table.item(row, 0)
        code = str(first_cell.data(Qt.UserRole) or "") if first_cell is not None else ""
        if not code:
            return
        holding = self.store.get_holding(self.asset_group, code)
        if holding is None:
            QMessageBox.warning(self, tr("Kayıt bulunamadı"), tr("Düzenlenecek kayıt artık mevcut değil."))
            self.refresh_table()
            return

        dialog = QDialog(self)
        dialog.setWindowTitle(tr("{0} kaydını düzenle").format(holding['display_name']))
        dialog.setMinimumWidth(340)
        form = QFormLayout(dialog)
        quantity_edit = QLineEdit(format_quantity(Decimal(holding["quantity"])))
        cost_edit = QLineEdit(format_localized(Decimal(holding["average_cost_try"])))
        quantity_edit.setPlaceholderText(tr("Örn. 10,5"))
        cost_edit.setPlaceholderText(tr("Örn. 3.250,00"))
        form.addRow(f"Miktar ({holding['unit']})", quantity_edit)
        form.addRow(tr("Ortalama alış birim fiyatı (₺)"), cost_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Save | QDialogButtonBox.Cancel)
        localize_dialog_buttons(buttons)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        form.addRow(buttons)
        if dialog.exec() != QDialog.Accepted:
            return

        try:
            quantity = parse_localized_decimal(quantity_edit.text(), field_name="Miktar")
            average_cost = parse_localized_decimal(
                cost_edit.text(), field_name=tr("Ortalama alış fiyatı")
            )
            self.store.set_holding(
                self.asset_group,
                code,
                quantity,
                average_cost,
                display_name=holding["display_name"],
                unit=holding["unit"],
            )
            self.refresh_table()
            self.portfolio_changed.emit()
            QMessageBox.information(
                self, tr("Kayıt güncellendi"),
                tr("{0} miktarı ve ortalama maliyeti güncellendi.").format(holding['display_name']),
            )
        except Exception as exc:
            QMessageBox.warning(self, tr("Kayıt güncellenemedi"), str(exc))

    def clear_form(self) -> None:
        self.quantity_input.clear()
        self.cost_input.clear()
        self.asset_input.setCurrentIndex(0)
        self.quantity_input.setFocus()

    def delete_selected(self) -> None:
        codes = self._selected_codes()
        if not codes:
            QMessageBox.information(self, tr("Kayıt sil"), tr("Önce tablodan bir veya daha fazla kayıt seç."))
            return
        names = [self.assets[code][0] for code in codes if code in self.assets]
        answer = ask_question(
            self,
            tr("Seçili kayıtları sil"),
            tr("{0} seçili kayıt silinecek:\n").format(len(codes)) + ", ".join(names)
            + tr("\n\nDevam edilsin mi?"),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.store.delete_holdings(self.asset_group, codes)
            self.refresh_table()
            self.portfolio_changed.emit()

    def delete_all(self) -> None:
        holdings = self.store.list_holdings(self.asset_group)
        if not holdings:
            QMessageBox.information(self, tr("Tüm kayıtları sil"), tr("Bu bölümde silinecek kayıt yok."))
            return
        answer = ask_warning_question(
            self,
            tr("Tüm kayıtları sil"),
            tr("{0} {1} kaydının tamamı kalıcı olarak silinecek.\n\nBu işlem geri alınamaz. Devam edilsin mi?").format(len(holdings), self.title().lower()),
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.store.delete_all(self.asset_group)
            self.clear_form()
            self.refresh_table()
            self.portfolio_changed.emit()

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
            rows = read_investment_holdings_excel(
                path,
                asset_group=self.asset_group,
                allowed_assets=self.assets,
            )
            if not rows:
                QMessageBox.information(self, tr("İçe aktarma"), tr("İçe aktarılacak kayıt bulunamadı."))
                return

            answer = ask_question(
                self,
                tr("İçe aktarmayı onayla"),
                tr("{0} varlık kaydı içe aktarılacak. Aynı varlık varsa mevcut miktar ve ortalama maliyet dosyadaki değerlerle değiştirilecek.\n\nDevam edilsin mi?").format(len(rows)),
                QMessageBox.Yes | QMessageBox.No,
                QMessageBox.No,
            )
            if answer != QMessageBox.Yes:
                return

            imported = 0
            errors: list[str] = []
            parser_errors = rows[0].get("_import_errors", []) if rows else []
            for row in rows:
                try:
                    self.store.set_holding(
                        self.asset_group,
                        row["asset_code"],
                        row["quantity"],
                        row["average_cost"],
                        display_name=row["display_name"],
                        unit=row["unit"],
                    )
                    imported += 1
                except Exception as exc:
                    errors.append(f"{row.get('asset_code', '?')}: {exc}")

            self.refresh_table()
            if imported:
                self.portfolio_changed.emit()
            messages = [tr("{0} kayıt içe aktarıldı.").format(imported)]
            if parser_errors:
                messages.append(tr("\nAtlanan satırlar:\n") + "\n".join(parser_errors[:10]))
            if errors:
                messages.append(tr("\nKaydedilemeyen kayıtlar:\n") + "\n".join(errors[:10]))
            if parser_errors or errors:
                QMessageBox.warning(self, tr("İçe aktarma tamamlandı"), "".join(messages))
            else:
                QMessageBox.information(self, tr("İçe aktarma tamamlandı"), messages[0])
        except Exception as exc:
            QMessageBox.warning(self, tr("Excel okunamadı"), str(exc))

    def export_excel(self) -> None:
        section = tr("Döviz portföyü") if self.asset_group == "currency" else tr("Metal portföyü")
        mode = ask_export_mode(self, section)
        if mode == TEMPLATE:
            run_template_export(
                self,
                caption=tr("{0} örnek şablonunu kaydet").format(section),
                default_name=template_filename(self.export_filename),
                writer=lambda target: write_investment_template(target, self.asset_group, self.assets),
            )
            return
        if mode != EXPORT:
            return
        holdings = self.store.list_holdings(self.asset_group)
        if not holdings:
            QMessageBox.information(self, tr("Dışa aktarma"), tr("Dışa aktarılacak kayıt bulunmuyor."))
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            tr("Portföyü Excel olarak kaydet"),
            str(Path.home() / self.export_filename),
            tr("Excel dosyaları (*.xlsx)"),
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            write_holdings_excel(
                path,
                holdings,
                self.current_prices,
                title=tr("Döviz Portföyü") if self.asset_group == "currency" else tr("Metal Portföyü"),
                rates_updated_at=self.rates_updated_at,
                rates_status=self.rates_status,
            )
            QMessageBox.information(self, tr("Dışa aktarma tamamlandı"), tr("Dosya kaydedildi:\n{0}").format(path))
        except Exception as exc:
            QMessageBox.warning(self, tr("Dışa aktarma başarısız"), str(exc))
