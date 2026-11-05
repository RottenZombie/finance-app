"""Centralized per-user paths for FinanceTerminal settings and portfolio data."""
from __future__ import annotations

import os
from pathlib import Path


def app_data_directory() -> Path:
    """Return the stable per-user FinanceTerminal data root.

    On Windows this is %APPDATA%\\FinanceTerminal. Keeping settings and SQLite
    files here means replacing the EXE during an update never replaces user data.
    """
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "FinanceTerminal"


def data_directory() -> Path:
    return app_data_directory() / "data"


def settings_file_path() -> Path:
    return app_data_directory() / "config.json"
