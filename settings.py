import json
import os
import sys
from pathlib import Path

from core.app_paths import app_data_directory, settings_file_path

DEFAULT = {
    "theme": "System",
    "precision": 2,
    "start_tab": 0,
    "close_to_tray": None,
    "auto_update_check": None,
    "active_profile": "profile1",
    "profile_names": {"profile1": "Profil 1", "profile2": "Profil 2"},  # Profile 3 is created on demand.
    "currency_codes": ["USD", "EUR", "HUF"],
}


def _legacy_config_candidates() -> list[Path]:
    """Find config files written beside the old EXE/current working directory."""
    candidates: list[Path] = []
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable).resolve().parent / "config.json")
        candidates.append(Path.cwd() / "config.json")
    else:
        candidates.append(Path(__file__).resolve().parent / "config.json")
        candidates.append(Path.cwd() / "config.json")

    target = settings_file_path().resolve()
    unique: list[Path] = []
    seen: set[str] = set()
    for candidate in candidates:
        try:
            resolved = candidate.resolve()
        except OSError:
            continue
        key = str(resolved).casefold()
        if key != str(target).casefold() and key not in seen:
            unique.append(resolved)
            seen.add(key)
    return unique


def _read_json(path: Path) -> dict | None:
    try:
        with path.open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else None
    except (OSError, ValueError, TypeError):
        return None


def _migrate_legacy_config(target: Path) -> None:
    """Move old beside-EXE config into %APPDATA% once, without losing settings."""
    if target.exists():
        # A prior run may have copied the config but could not remove the old file.
        if getattr(sys, "frozen", False):
            for legacy in _legacy_config_candidates():
                try:
                    legacy.unlink(missing_ok=True)
                except OSError:
                    pass
        return

    for legacy in _legacy_config_candidates():
        stored = _read_json(legacy)
        if stored is None:
            continue
        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            with target.open("w", encoding="utf-8") as stream:
                json.dump(stored, stream, indent=4, ensure_ascii=False)
            # Remove the visible legacy file only after the new copy is safely written.
            if getattr(sys, "frozen", False):
                try:
                    legacy.unlink(missing_ok=True)
                except OSError:
                    pass
            return
        except OSError:
            return


def load():
    target = settings_file_path()
    _migrate_legacy_config(target)
    settings = DEFAULT.copy()
    stored = _read_json(target)
    if stored is not None:
        settings.update(stored)
    return settings


def save(data):
    target = settings_file_path()
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as stream:
        json.dump(data, stream, indent=4, ensure_ascii=False)


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

    return "Dark"


def resolve_theme(preference: str) -> str:
    value = str(preference or "System").strip()
    if value.lower() in {"system", "auto", "windows"}:
        return detect_system_theme()
    if value in {"White", "Dark", "Blue"}:
        return value
    return detect_system_theme()
