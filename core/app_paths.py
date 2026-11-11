"""Centralized per-user paths for FinanceTerminal settings and profile data."""
from __future__ import annotations

import os
import shutil
from pathlib import Path

_ACTIVE_PROFILE_ID = "profile1"
_VALID_PROFILE_IDS = {"profile1", "profile2", "profile3"}


def app_data_directory() -> Path:
    """Return the stable per-user FinanceTerminal data root."""
    if os.name == "nt":
        root = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    else:
        root = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local" / "share"))
    return root / "FinanceTerminal"


def set_active_profile(profile_id: str) -> None:
    """Select the profile used by newly created data stores."""
    global _ACTIVE_PROFILE_ID
    normalized = str(profile_id or "profile1").strip().lower()
    if normalized not in _VALID_PROFILE_IDS:
        raise ValueError("Geçersiz FinanceTerminal profili.")
    _ACTIVE_PROFILE_ID = normalized


def active_profile_id() -> str:
    return _ACTIVE_PROFILE_ID


def profile_directory(profile_id: str | None = None) -> Path:
    normalized = str(profile_id or _ACTIVE_PROFILE_ID).strip().lower()
    if normalized not in _VALID_PROFILE_IDS:
        raise ValueError("Geçersiz FinanceTerminal profili.")
    return app_data_directory() / "profiles" / normalized


def data_directory() -> Path:
    """Return the active profile's independent data directory."""
    return profile_directory() / "data"


def migrate_legacy_data_to_profile1() -> bool:
    """Copy legacy 2.2.x data into Profile 1 without deleting the old copy.

    Keeping the source folder intact makes this a non-destructive, one-time
    migration and provides an additional recovery copy if the first run fails.
    """
    legacy = app_data_directory() / "data"
    target = profile_directory("profile1") / "data"
    if not legacy.is_dir() or target.exists():
        return False
    staging = target.with_name(target.name + ".migration")
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        if staging.exists():
            shutil.rmtree(staging, ignore_errors=True)
        shutil.copytree(legacy, staging)
        staging.replace(target)
        return True
    except OSError:
        shutil.rmtree(staging, ignore_errors=True)
        return False


def settings_file_path() -> Path:
    """Settings remain global so profile names and the active profile persist."""
    return app_data_directory() / "config.json"
