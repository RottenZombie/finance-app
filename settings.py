import json
import os

FILE = "config.json"

DEFAULT = {
    "theme": "System",
    "precision": 2,
    "start_tab": 0,
    "close_to_tray": None,
    "auto_update_check": None,
}


def load():
    settings = DEFAULT.copy()
    if not os.path.exists(FILE):
        return settings
    try:
        with open(FILE, "r", encoding="utf-8") as f:
            stored = json.load(f)
        if isinstance(stored, dict):
            settings.update(stored)
        return settings
    except (OSError, ValueError, TypeError):
        return settings


def save(data):
    with open(FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


def detect_system_theme() -> str:
    """Return White when Windows/Qt reports light mode; otherwise Dark."""
    try:
        from PySide6.QtCore import Qt
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance()
        if app is not None:
            scheme = app.styleHints().colorScheme()
            if scheme == Qt.ColorScheme.Light:
                return "White"
            if scheme == Qt.ColorScheme.Dark:
                return "Dark"
    except Exception:
        pass

    if os.name == "nt":
        try:
            import winreg

            key_path = r"Software\Microsoft\Windows\CurrentVersion\Themes\Personalize"
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, key_path) as key:
                value, _ = winreg.QueryValueEx(key, "AppsUseLightTheme")
            return "White" if int(value) == 1 else "Dark"
        except Exception:
            pass

    # Unknown system preference defaults to dark, as requested.
    return "Dark"


def resolve_theme(preference: str) -> str:
    value = str(preference or "System").strip()
    if value.lower() in {"system", "auto", "windows"}:
        return detect_system_theme()
    if value in {"White", "Dark", "Blue"}:
        return value
    return detect_system_theme()
