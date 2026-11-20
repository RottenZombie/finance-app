"""Relaunch the application (used after a language change)."""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from core.autostart import AUTOSTART_FLAG
from core.log_setup import get_logger

log = get_logger("restart")


def restart_command(
    *, frozen: bool | None = None, executable: str | None = None,
    argv: list[str] | None = None,
) -> tuple[str, list[str]]:
    """Program and arguments that start a fresh copy of this application."""
    is_frozen = getattr(sys, "frozen", False) if frozen is None else frozen
    program = executable or sys.executable
    arguments = list(sys.argv if argv is None else argv)
    # A manual restart is not an automatic Windows start.
    extra = [item for item in arguments[1:] if item != AUTOSTART_FLAG]
    if is_frozen:
        return program, extra
    script = str(Path(arguments[0]).resolve()) if arguments else "app.py"
    return program, [script, *extra]


def spawn_detached(program: str, arguments: list[str]) -> bool:
    """Start the process independently of this one. Never raises."""
    environment = os.environ.copy()
    # A one-file PyInstaller build restarted from itself must unpack a fresh copy
    # instead of reusing the temporary folder of the process that is about to exit.
    environment["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
    flags = 0
    if sys.platform == "win32":
        flags = subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP
    try:
        subprocess.Popen(
            [program, *arguments], env=environment, creationflags=flags,
            close_fds=True, stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        return True
    except (OSError, ValueError):
        log.warning("Uygulama yeniden başlatılamadı", exc_info=True)
        return False
