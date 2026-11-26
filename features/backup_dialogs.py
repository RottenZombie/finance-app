"""Dialogs for creating and restoring a backup (see docs/DATA_FORMAT.md)."""
from __future__ import annotations

import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Mapping

from PySide6.QtWidgets import QFileDialog, QInputDialog, QLineEdit, QMessageBox

from core import backup
from core.backup import BackupError, PasswordRequiredError, WrongPasswordError
from core.i18n import tr
from core.log_setup import get_logger
from core.timefmt import format_local
from features import backup_data
from features.dialogs import ask_warning_question

log = get_logger("backup.ui")

PASSWORD_ATTEMPTS = 3
SHOWN_SKIPPED = 8


def _file_filter() -> str:
    return tr("FinanceTerminal yedeği (*.ftbackup)")


def _ask_password(parent, title: str, label: str) -> str | None:
    text, accepted = QInputDialog.getText(parent, title, label, QLineEdit.EchoMode.Password)
    return text if accepted else None


def _ask_new_password(parent) -> str | None:
    """Ask twice; returns None when the user cancels."""
    title = tr("Yedek şifresi")
    while True:
        first = _ask_password(
            parent, title, tr("Yedek şifresi (en az {0} karakter):").format(backup.MIN_PASSWORD_LENGTH)
        )
        if first is None:
            return None
        problem = backup.password_problem(first)
        if problem:
            QMessageBox.warning(parent, title, problem)
            continue
        second = _ask_password(parent, title, tr("Şifreyi tekrar girin:"))
        if second is None:
            return None
        if first != second:
            QMessageBox.warning(parent, title, tr("Şifreler aynı değil."))
            continue
        return first


def _ask_encryption(parent) -> str | None:
    """"encrypted", "plain" or None (cancelled)."""
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("Yedek Al"))
    box.setText(tr("Yedek dosyası şifrelensin mi?"))
    box.setInformativeText(
        tr("Şifreli yedekte şifreyi unutursanız verileriniz kurtarılamaz; şifre hiçbir yerde saklanmaz.")
        + "\n\n"
        + tr("Şifresiz yedek, finansal verilerinizi dosyayı açan herkesin okuyabileceği biçimde içerir; güvenli bir yerde saklayın.")
    )
    encrypted_button = box.addButton(tr("Şifreli Yedek"), QMessageBox.ButtonRole.AcceptRole)
    plain_button = box.addButton(tr("Şifresiz Yedek"), QMessageBox.ButtonRole.ActionRole)
    cancel_button = box.addButton(tr("İptal"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(plain_button)
    box.setEscapeButton(cancel_button)
    box.exec()
    clicked = box.clickedButton()
    if clicked is encrypted_button:
        return "encrypted"
    if clicked is plain_button:
        return "plain"
    return None


def _write_atomic(path: Path, data: bytes) -> None:
    """Never leave a half-written backup behind: write beside it, then replace."""
    fd, tmp_name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=str(path.parent))
    try:
        with os.fdopen(fd, "wb") as stream:
            stream.write(data)
        os.replace(tmp_name, path)
    except BaseException:
        try:
            os.unlink(tmp_name)
        except OSError:
            pass
        raise


def run_backup(parent, settings: Mapping[str, Any], app_version: str) -> bool:
    """Create a backup file. Returns True when a file was written."""
    choice = _ask_encryption(parent)
    if choice is None:
        return False
    password = None
    if choice == "encrypted":
        password = _ask_new_password(parent)
        if password is None:
            return False

    default_name = f"FinanceTerminal_{tr('Yedek')}_{time.strftime('%Y-%m-%d')}{backup.FILE_EXTENSION}"
    path, _ = QFileDialog.getSaveFileName(
        parent, tr("Yedeği kaydet"), str(Path.home() / default_name), _file_filter()
    )
    if not path:
        return False
    if not path.lower().endswith(backup.FILE_EXTENSION):
        path += backup.FILE_EXTENSION

    try:
        data, counts = backup_data.build_backup_bytes(settings, password=password, app_version=app_version)
        _write_atomic(Path(path), data)
    except (BackupError, OSError) as exc:
        log.warning("Yedek alınamadı", exc_info=True)
        QMessageBox.warning(parent, tr("Yedek alınamadı"), str(exc))
        return False

    message = tr("Yedek kaydedildi:\n{0}\n\nProfil: {1}, döviz: {2}, maden: {3}, hisse: {4} kayıt.").format(
        path, counts["profiles"], counts["currency"], counts["metals"], counts["stocks"]
    )
    message += "\n\n" + (
        tr("Dosya şifrelidir. Şifreyi unutursanız verileriniz kurtarılamaz.")
        if password
        else tr("Dosya şifresizdir ve finansal verilerinizi içerir; güvenli bir yerde saklayın.")
    )
    QMessageBox.information(parent, tr("Yedek alındı"), message)
    return True


def _created_text(info: backup.BackupInfo) -> str:
    try:
        moment = datetime.strptime(info.created_at, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc)
        return format_local(moment)
    except (ValueError, AttributeError):
        return info.created_at or "-"


def _load_with_password(parent, data: bytes, info: backup.BackupInfo):
    """Decrypt/validate, asking for the password when needed. None when cancelled."""
    if not info.encrypted:
        return backup_data.load_clean(data)
    for attempt in range(PASSWORD_ATTEMPTS):
        password = _ask_password(parent, tr("Yedek şifresi"), tr("Bu yedek şifreli; şifreyi girin."))
        if password is None:
            return None
        try:
            return backup_data.load_clean(data, password)
        except (WrongPasswordError, PasswordRequiredError) as exc:
            QMessageBox.warning(parent, tr("Yedek şifresi"), str(exc))
    return None


def _ask_mode(parent, info: backup.BackupInfo, clean) -> str | None:
    counts = backup_data.summarize(clean)
    box = QMessageBox(parent)
    box.setIcon(QMessageBox.Icon.Question)
    box.setWindowTitle(tr("Yedekten Geri Yükle"))
    text = tr("Yedekte {0} profil, {1} döviz, {2} maden ve {3} hisse kaydı var.\nOluşturulma: {4} (FinanceTerminal {5})").format(
        counts["profiles"], counts["currency"], counts["metals"], counts["stocks"],
        _created_text(info), info.app_version or "?",
    )
    if clean.skipped:
        text += "\n" + tr("{0} satır okunamadığı için atlanacak.").format(len(clean.skipped))
    box.setText(text)
    box.setInformativeText(
        tr("Birleştir: dosyadaki kayıtlar eklenir ya da güncellenir; sizde olup dosyada olmayan kayıtlar korunur.")
        + "\n"
        + tr("Üzerine Yaz: dosyadaki profillerin kayıtları silinip dosyadakilerle değiştirilir; ortak tercihler de dosyadan alınır.")
        + "\n\n"
        + tr("Her iki durumda mevcut verileriniz önce otomatik olarak yedeklenir.")
    )
    merge_button = box.addButton(tr("Birleştir"), QMessageBox.ButtonRole.AcceptRole)
    replace_button = box.addButton(tr("Üzerine Yaz"), QMessageBox.ButtonRole.DestructiveRole)
    cancel_button = box.addButton(tr("İptal"), QMessageBox.ButtonRole.RejectRole)
    box.setDefaultButton(merge_button)
    box.setEscapeButton(cancel_button)
    box.exec()
    clicked = box.clickedButton()
    if clicked is merge_button:
        return backup_data.MERGE
    if clicked is replace_button:
        answer = ask_warning_question(
            parent,
            tr("Üzerine yazılsın mı?"),
            tr("Dosyadaki profillerin mevcut kayıtları silinecek ve yedektekilerle değiştirilecek. Devam edilsin mi?"),
        )
        return backup_data.REPLACE if answer == QMessageBox.StandardButton.Yes else None
    return None


def run_restore(parent, settings: Mapping[str, Any], app_version: str):
    """Restore from a backup file.

    Returns the :class:`backup_data.RestoreReport` (its ``settings`` must be saved by
    the caller) or ``None`` when nothing was restored.
    """
    path, _ = QFileDialog.getOpenFileName(parent, tr("Yedek dosyasını seçin"), str(Path.home()), _file_filter())
    if not path:
        return None
    try:
        with open(path, "rb") as stream:
            data = stream.read(backup.MAX_FILE_BYTES + 1)
        info = backup.inspect_backup(data)
        loaded = _load_with_password(parent, data, info)
    except (BackupError, OSError) as exc:
        QMessageBox.warning(parent, tr("Yedek okunamadı"), str(exc))
        return None
    if loaded is None:
        return None
    _info, clean = loaded
    if not clean.profiles:
        QMessageBox.information(parent, tr("Yedekten Geri Yükle"), tr("Yedekte geri yüklenecek kayıt bulunamadı."))
        return None

    mode = _ask_mode(parent, info, clean)
    if mode is None:
        return None
    try:
        report = backup_data.apply_backup(clean, mode, settings, app_version=app_version)
    except (BackupError, OSError, ValueError) as exc:
        QMessageBox.warning(parent, tr("Geri yükleme başarısız"), str(exc))
        return None

    message = tr("{0} kayıt geri yüklendi.").format(report.total_imported)
    if report.safety_backup:
        message += "\n\n" + tr("Önceki verileriniz şu dosyada saklandı:\n{0}").format(report.safety_backup)
    if report.skipped:
        shown = "\n".join(report.skipped[:SHOWN_SKIPPED])
        extra = len(report.skipped) - SHOWN_SKIPPED
        message += "\n\n" + tr("Atlanan satırlar:\n") + shown
        if extra > 0:
            message += "\n" + tr("... ve {0} satır daha.").format(extra)
    QMessageBox.information(parent, tr("Geri yükleme tamamlandı"), message)
    return report
