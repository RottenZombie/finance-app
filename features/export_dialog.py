"""Shared Qt helpers for the Excel export choice ("my data" vs "sample template")."""
from __future__ import annotations

from pathlib import Path
from typing import Callable

from PySide6.QtWidgets import QFileDialog, QMessageBox
from core.i18n import tr

EXPORT = "export"
TEMPLATE = "template"


def ask_export_mode(parent, section_title: str) -> str | None:
    """Return EXPORT, TEMPLATE or None (cancelled)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("Excel'e Aktar"))
    box.setText(tr("{0} için ne yapmak istersiniz?").format(section_title))
    box.setInformativeText(
        tr("Verilerimi Aktar: kayıtlarınız ve dışa aktarma anındaki fiyat / kâr-zarar değerleri.\nÖrnek Şablon İndir: aynı düzende, her sayfada tek örnek satır içeren dosya. Örneği kendi verinizle değiştirip içe aktarabilirsiniz.")
    )
    export_button = box.addButton(tr("Verilerimi Aktar"), QMessageBox.ButtonRole.AcceptRole)
    template_button = box.addButton(tr("Örnek Şablon İndir"), QMessageBox.ButtonRole.ActionRole)
    cancel_button = box.addButton(tr("İptal"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(export_button)
    box.setEscapeButton(cancel_button)
    box.exec()
    clicked = box.clickedButton()
    if clicked is export_button:
        return EXPORT
    if clicked is template_button:
        return TEMPLATE
    return None


def ask_save_xlsx(parent, caption: str, default_name: str) -> str | None:
    path, _ = QFileDialog.getSaveFileName(
        parent, caption, str(Path.home() / default_name), tr("Excel dosyaları (*.xlsx)")
    )
    if not path:
        return None
    return path if path.lower().endswith(".xlsx") else path + ".xlsx"


def run_template_export(
    parent, *, caption: str, default_name: str, writer: Callable[[str], None]
) -> bool:
    """Ask for a path, write the sample template and report. Returns True on success."""
    path = ask_save_xlsx(parent, caption, default_name)
    if not path:
        return False
    try:
        writer(path)
    except Exception as exc:
        QMessageBox.warning(parent, tr("Şablon kaydedilemedi"), str(exc))
        return False
    QMessageBox.information(
        parent,
        tr("Örnek şablon kaydedildi"),
        tr("Dosya kaydedildi:\n{0}\n\nÖrnek satırı kendi verinizle değiştirip \"Excel'den İçe Aktar\" ile yükleyebilirsiniz.").format(path),
    )
    return True
