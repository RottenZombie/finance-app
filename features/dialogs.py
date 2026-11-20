"""Qt dialog helpers that follow the application language.

Qt's standard buttons (Yes/No/Save/Cancel...) are translated by Qt according to the
*operating-system* language, which may differ from the language chosen in
FinanceTerminal. These helpers label them explicitly instead.
"""
from __future__ import annotations

from PySide6.QtWidgets import QDialogButtonBox, QMessageBox

from core.i18n import tr, tr_noop

# (StandardButton member name, Turkish source text)
_BUTTONS = (
    ("Yes", tr_noop("Evet")),
    ("No", tr_noop("Hayır")),
    ("Ok", tr_noop("Tamam")),
    ("Cancel", tr_noop("İptal")),
    ("Save", tr_noop("Kaydet")),
    ("Close", tr_noop("Kapat")),
)


def _localize(box, enum) -> None:
    for member, text in _BUTTONS:
        standard = getattr(enum, member, None)
        button = box.button(standard) if standard is not None else None
        if button is not None:
            button.setText(tr(text))


def localize_message_buttons(box: QMessageBox) -> None:
    _localize(box, QMessageBox.StandardButton)


def localize_dialog_buttons(box: QDialogButtonBox) -> None:
    _localize(box, QDialogButtonBox.StandardButton)


def _ask(parent, title, text, icon, default) -> QMessageBox.StandardButton:
    box = QMessageBox(parent)
    box.setIcon(icon)
    box.setWindowTitle(title)
    box.setText(text)
    box.setStandardButtons(QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
    box.setDefaultButton(default)
    localize_message_buttons(box)
    box.exec()
    clicked = box.clickedButton()
    yes = box.button(QMessageBox.StandardButton.Yes)
    return QMessageBox.StandardButton.Yes if clicked is yes else QMessageBox.StandardButton.No


def ask_question(parent, title, text, buttons=None, default=None) -> QMessageBox.StandardButton:
    """Drop-in for ``QMessageBox.question`` with Yes/No labelled in the app language."""
    return _ask(parent, title, text, QMessageBox.Icon.Question,
                default if default is not None else QMessageBox.StandardButton.No)


def ask_warning_question(parent, title, text, buttons=None, default=None) -> QMessageBox.StandardButton:
    """Same as :func:`ask_question` but with the warning icon (destructive actions)."""
    return _ask(parent, title, text, QMessageBox.Icon.Warning,
                default if default is not None else QMessageBox.StandardButton.No)
