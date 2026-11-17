"""Start FinanceTerminal automatically when the user signs in to Windows.

Uses the per-user ``Run`` registry key (no administrator rights needed, nothing
outside the current user's profile is touched). The packaged EXE is launched with
``--autostart`` so the app knows it was started by Windows, not by the user.

Windows' Task Manager (Startup apps) keeps its own on/off mark in
``StartupApproved\\Run``; it is honoured when reading and cleared when the user
explicitly enables the option again in the app.

Every function is safe to call on any platform and never raises: the registry
module is injectable, which also makes the behaviour unit-testable.
"""
from __future__ import annotations

import os
import sys
from typing import Any

from core.log_setup import get_logger

log = get_logger("autostart")

RUN_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
APPROVED_PATH = r"Software\Microsoft\Windows\CurrentVersion\Explorer\StartupApproved\Run"
VALUE_NAME = "FinanceTerminal"
AUTOSTART_FLAG = "--autostart"


def _registry(registry: Any = None) -> Any:
    if registry is not None:
        return registry
    if sys.platform != "win32":
        return None
    try:
        import winreg
    except ImportError:
        return None
    return winreg


def is_supported(registry: Any = None, *, frozen: bool | None = None) -> bool:
    """Only the installed (packaged) EXE on Windows can register itself."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    return bool(is_frozen) and _registry(registry) is not None


def build_command(executable: str | None = None) -> str:
    return f'"{os.path.normpath(executable or sys.executable)}" {AUTOSTART_FLAG}'


def _read(reg: Any, path: str, name: str) -> tuple[Any, int] | None:
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, path, 0, reg.KEY_READ) as key:
            return reg.QueryValueEx(key, name)
    except OSError:
        return None


def _delete(reg: Any, path: str, name: str) -> None:
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, path, 0, reg.KEY_SET_VALUE) as key:
            reg.DeleteValue(key, name)
    except FileNotFoundError:
        pass


def is_enabled(registry: Any = None) -> bool:
    """True when Windows will really start the app at sign-in."""
    reg = _registry(registry)
    if reg is None:
        return False
    entry = _read(reg, RUN_PATH, VALUE_NAME)
    if entry is None or not str(entry[0]).strip():
        return False
    approved = _read(reg, APPROVED_PATH, VALUE_NAME)
    if approved is not None:
        data = approved[0]
        # Task Manager stores 0x02/0x06 for "enabled" and 0x03 for "disabled".
        if isinstance(data, (bytes, bytearray)) and data and data[0] & 1:
            return False
    return True


def set_enabled(enabled: bool, registry: Any = None, executable: str | None = None) -> bool:
    """Turn Windows startup on or off. Returns False if the registry refused."""
    reg = _registry(registry)
    if reg is None:
        return False
    try:
        if enabled:
            with reg.CreateKey(reg.HKEY_CURRENT_USER, RUN_PATH) as key:
                reg.SetValueEx(key, VALUE_NAME, 0, reg.REG_SZ, build_command(executable))
            # Re-enabling here also clears an earlier "disabled" mark from Task Manager.
            _delete(reg, APPROVED_PATH, VALUE_NAME)
        else:
            _delete(reg, RUN_PATH, VALUE_NAME)
            _delete(reg, APPROVED_PATH, VALUE_NAME)
        return True
    except OSError:
        log.warning("Windows başlangıç kaydı değiştirilemedi", exc_info=True)
        return False


def repair_command(registry: Any = None, executable: str | None = None) -> bool:
    """If the EXE was moved or renamed, point an existing entry at the current file.

    Only rewrites an entry that already exists; it never creates one and never
    touches the Task Manager on/off mark. Returns True when something was fixed.
    """
    reg = _registry(registry)
    if reg is None:
        return False
    entry = _read(reg, RUN_PATH, VALUE_NAME)
    expected = build_command(executable)
    if entry is None or str(entry[0]) == expected:
        return False
    try:
        with reg.OpenKey(reg.HKEY_CURRENT_USER, RUN_PATH, 0, reg.KEY_SET_VALUE) as key:
            reg.SetValueEx(key, VALUE_NAME, 0, reg.REG_SZ, expected)
        return True
    except OSError:
        log.warning("Windows başlangıç kaydı güncellenemedi", exc_info=True)
        return False
