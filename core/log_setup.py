"""Application logging (rotating file in %APPDATA%\\FinanceTerminal\\logs).

Silent failures were the main diagnostic gap in earlier versions: many network
and parsing errors were swallowed with ``except Exception``. Modules now log
those errors through ``get_logger`` so a problem can be investigated afterwards.
"""
from __future__ import annotations

import logging
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

from core.app_paths import app_data_directory

_BASE = "financeterminal"
# A NullHandler keeps Python from printing "No handlers could be found" noise
# (and keeps tests quiet) when setup_logging() has not been called.
logging.getLogger(_BASE).addHandler(logging.NullHandler())

_configured = False


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(f"{_BASE}.{name}")


def log_directory() -> Path:
    return app_data_directory() / "logs"


def setup_logging(directory: str | Path | None = None) -> logging.Logger:
    """Configure the file log once. Never raises: logging must not break startup."""
    global _configured
    logger = logging.getLogger(_BASE)
    if _configured:
        return logger
    _configured = True
    logger.setLevel(logging.INFO)
    logger.propagate = False
    try:
        folder = Path(directory) if directory else log_directory()
        folder.mkdir(parents=True, exist_ok=True)
        handler: logging.Handler = RotatingFileHandler(
            folder / "app.log", maxBytes=512 * 1024, backupCount=2, encoding="utf-8"
        )
        handler.setFormatter(
            logging.Formatter("%(asctime)s %(levelname)s %(name)s: %(message)s")
        )
        logger.addHandler(handler)
    except OSError:
        pass
    _install_excepthook(logger)
    return logger


def _install_excepthook(logger: logging.Logger) -> None:
    previous = sys.excepthook

    def hook(exc_type, exc, tb):
        if not issubclass(exc_type, KeyboardInterrupt):
            logger.critical("Yakalanmamış hata", exc_info=(exc_type, exc, tb))
        try:
            previous(exc_type, exc, tb)
        except Exception:
            # A windowed PyInstaller build has no stderr to print to.
            pass

    sys.excepthook = hook
