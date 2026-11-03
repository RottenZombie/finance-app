from __future__ import annotations

from decimal import Decimal
from pathlib import Path

from PySide6.QtCore import Qt
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
)

from .database import BistDatabase
from .excel_io import read_portfolio_excel, write_portfolio_excel
from .utils import format_quantity, format_tl, normalize_symbol, parse_localized_decimal


class BistPortfolioTab(QWidget):
    """Local-only BIST holdings tab. Price feeds and AI analysis are later stages."""

    def __init__(self, parent=None, database: BistDatabase | None = None):
        super().__init__(parent)
        self.database = database or BistDatabase()
        self._build_ui()
        self.refresh_table()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 12, 14, 14)
        root.setSpacing(10)

        header = QHBoxLayout()
        title_box = QVBoxLayout()
        title = QLabel("BIST AI · Portföy")
        title.setObjectName("bistTitle")
        title.setStyleSheet("font-size: 20px; font-weight: 700;")
        subtitle = QLabel("Hisselerini kaydet, maliyetini takip et ve analiz modüllerine hazırla.")
        subtitle.setObjectName("bistSubtitle")
        subtitle.setWordWrap(True)
        title_box.addWidget(title)
        title_box.addWidget(subtitle)
        header.addLayout(title_box, 1)

        self.storage_label = QLabel("Veriler bu bilgisayarda saklanır")
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
        self.count_card, self.count_value = self._metric_card("Hisse sayısı", "0")
        self.cost_card, self.cost_value = self._metric_card("Toplam maliyet", "0,00 ₺")
        metrics.addWidget(self.count_card, 0, 0)
        metrics.addWidget(self.cost_card, 0, 1)
        root.addLayout(metrics)

        form_frame = QFrame()
        form_frame.setObjectName("bistFormFrame")
        form_layout = QVBoxLayout(form_frame)
        form_layout.setContentsMargins(10, 9, 10, 9)
        form_layout.setSpacing(7)
        form_title = QLabel("Hisse kaydı")
        form_title.setStyleSheet("font-weight: 700;")
        form_layout.addWidget(form_title)

        fields = QGridLayout()
        fields.setHorizontalSpacing(8)
        fields.setVerticalSpacing(6)

        self.symbol_input = QLineEdit()
        self.symbol_input.setPlaceholderText("Örn. ASELS")
        self.company_input = QLineEdit()
        self.company_input.setPlaceholderText("Şirket adı (isteğe bağlı)")
        self.quantity_input = QLineEdit()
        self.quantity_input.setPlaceholderText("Örn. 250")
        self.cost_input = QLineEdit()
        self.cost_input.setPlaceholderText("Örn. 74,50")
        self.sector_input = QLineEdit()
        self.sector_input.setPlaceholderText("Örn. Savunma")
        self.notes_input = QLineEdit()
        self.notes_input.setPlaceholderText("İsteğe bağlı not")

        fields.addWidget(QLabel("Hisse kodu *"), 0, 0)
        fields.addWidget(QLabel("Şirket"), 0, 1)
        fields.addWidget(self.symbol_input, 1, 0)
        fields.addWidget(self.company_input, 1, 1)
        fields.addWidget(QLabel("Adet *"), 2, 0)
        fields.addWidget(QLabel("Ortalama maliyet (TL) *"), 2, 1)
        fields.addWidget(self.quantity_input, 3, 0)
        fields.addWidget(self.cost_input, 3, 1)
        fields.addWidget(QLabel("Sektör"), 4, 0)
        fields.addWidget(QLabel("Not"), 4, 1)
        fields.addWidget(self.sector_input, 5, 0)
        fields.addWidget(self.notes_input, 5, 1)
        form_layout.addLayout(fields)

        buttons = QHBoxLayout()
        self.save_button = QPushButton("Ekle / Güncelle")
        self.save_button.clicked.connect(self.save_holding)
        self.clear_button = QPushButton("Formu temizle")
        self.clear_button.clicked.connect(self.clear_form)
        self.delete_button = QPushButton("Seçili hisseyi sil")
        self.delete_button.clicked.connect(self.delete_selected)
        buttons.addWidget(self.save_button)
        buttons.addWidget(self.clear_button)
        buttons.addWidget(self.delete_button)
        buttons.addStretch(1)
        form_layout.addLayout(buttons)
        root.addWidget(form_frame)

        toolbar = QHBoxLayout()
        toolbar.addWidget(QLabel("Portföy kayıtları"))
        toolbar.addStretch(1)
        self.import_button = QPushButton("Excel içe aktar")
        self.import_button.clicked.connect(self.import_excel)
        self.export_button = QPushButton("Excel dışa aktar")
        self.export_button.clicked.connect(self.export_excel)
        toolbar.addWidget(self.import_button)
        toolbar.addWidget(self.export_button)
        root.addLayout(toolbar)

        self.table = QTableWidget(0, 7)
        self.table.setHorizontalHeaderLabels(
            ["Hisse", "Şirket", "Adet", "Ort. maliyet", "Toplam maliyet", "Sektör", "Son güncelleme"]
        )
        self.table.setAlternatingRowColors(True)
        self.table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QAbstractItemView.SingleSelection)
        self.table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.table.setSortingEnabled(False)
        self.table.verticalHeader().setVisible(False)
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        for column in (2, 3, 4, 5, 6):
            self.table.horizontalHeader().setSectionResizeMode(column, QHeaderView.ResizeToContents)
        self.table.itemDoubleClicked.connect(self.load_selected_to_form)
        root.addWidget(self.table, 1)

        self.notice = QLabel(
            "Bilgi: Bu sürüm portföy ve maliyet kayıtlarını yönetir. Güncel fiyat, getiri, "
            "KAP taraması ve yapay zekâ analizleri sonraki geliştirme aşamasında eklenecek."
        )
        self.notice.setObjectName("bistNotice")
        self.notice.setWordWrap(True)
        root.addWidget(self.notice)

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

    def refresh_table(self) -> None:
        holdings = self.database.list_holdings()
        self.table.setRowCount(len(holdings))

        for row_index, holding in enumerate(holdings):
            quantity = Decimal(holding["quantity"])
            average_cost = Decimal(holding["average_cost"])
            total_cost = quantity * average_cost
            updated = str(holding.get("updated_at", ""))[:10]
            values = [
                holding["symbol"],
                holding.get("company", ""),
                format_quantity(quantity),
                f"{format_tl(average_cost)} ₺",
                f"{format_tl(total_cost)} ₺",
                holding.get("sector", ""),
                updated,
            ]
            for column, value in enumerate(values):
                item = QTableWidgetItem(value)
                if column in (2, 3, 4):
                    item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                if column == 0:
                    item.setData(Qt.UserRole, holding["symbol"])
                self.table.setItem(row_index, column, item)

        summary = self.database.summary()
        self._set_metric(self.count_value, str(summary["holding_count"]))
        self._set_metric(self.cost_value, f"{format_tl(summary['total_cost'])} ₺")

    def save_holding(self) -> None:
        try:
            symbol = normalize_symbol(self.symbol_input.text())
            quantity = parse_localized_decimal(self.quantity_input.text(), field_name="Adet")
            average_cost = parse_localized_decimal(self.cost_input.text(), field_name="Ortalama maliyet")
            self.database.upsert_holding(
                symbol=symbol,
                company=self.company_input.text(),
                quantity=quantity,
                average_cost=average_cost,
                sector=self.sector_input.text(),
                notes=self.notes_input.text(),
            )
            self.refresh_table()
            self.clear_form()
            QMessageBox.information(self, "BIST Portföy", f"{symbol} kaydı kaydedildi.")
        except Exception as exc:
            QMessageBox.warning(self, "Kayıt yapılamadı", str(exc))

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

    def _selected_symbol(self) -> str | None:
        row = self.table.currentRow()
        if row < 0:
            return None
        item = self.table.item(row, 0)
        return item.data(Qt.UserRole) if item else None

    def load_selected_to_form(self, *_args) -> None:
        symbol = self._selected_symbol()
        if not symbol:
            return
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
        symbol = self._selected_symbol()
        if not symbol:
            QMessageBox.information(self, "BIST Portföy", "Önce tablodan bir hisse seç.")
            return
        answer = QMessageBox.question(
            self,
            "Hisseyi sil",
            f"{symbol} portföy kaydı silinsin mi?",
            QMessageBox.Yes | QMessageBox.No,
            QMessageBox.No,
        )
        if answer == QMessageBox.Yes:
            self.database.delete_holding(symbol)
            self.refresh_table()
            self.clear_form()

    def import_excel(self) -> None:
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Portföy Excel dosyasını seç",
            str(Path.home()),
            "Excel dosyaları (*.xlsx)",
        )
        if not path:
            return
        try:
            rows = read_portfolio_excel(path)
            imported, errors = self.database.import_rows(rows)
            self.refresh_table()
            message = f"{imported} kayıt içe aktarıldı."
            if errors:
                message += "\n\nAtlanan satırlar:\n" + "\n".join(errors[:12])
                if len(errors) > 12:
                    message += f"\n... ve {len(errors) - 12} hata daha."
                QMessageBox.warning(self, "İçe aktarma tamamlandı", message)
            else:
                QMessageBox.information(self, "İçe aktarma tamamlandı", message)
        except Exception as exc:
            QMessageBox.warning(self, "Excel okunamadı", str(exc))

    def export_excel(self) -> None:
        holdings = self.database.list_holdings()
        if not holdings:
            QMessageBox.information(self, "BIST Portföy", "Dışa aktarılacak kayıt bulunmuyor.")
            return
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Portföyü Excel olarak kaydet",
            str(Path.home() / "BIST_Portfoy.xlsx"),
            "Excel dosyaları (*.xlsx)",
        )
        if not path:
            return
        if not path.lower().endswith(".xlsx"):
            path += ".xlsx"
        try:
            write_portfolio_excel(path, holdings)
            QMessageBox.information(self, "Dışa aktarma tamamlandı", f"Dosya kaydedildi:\n{path}")
        except Exception as exc:
            QMessageBox.warning(self, "Excel kaydedilemedi", str(exc))
