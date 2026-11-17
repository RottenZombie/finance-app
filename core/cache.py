"""Tiny JSON cache helpers with atomic writes.

A crash or power loss while writing must never leave a half-written cache file,
and a corrupt/missing cache must never stop the application: callers simply get
an empty dictionary back.
"""
from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from core.log_setup import get_logger

log = get_logger("cache")


def load_json(path: str | Path) -> dict[str, Any]:
    try:
        with Path(path).open("r", encoding="utf-8") as stream:
            value = json.load(stream)
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}


def save_json_atomic(path: str | Path, data: dict[str, Any]) -> bool:
    """Write JSON through a temporary file and replace the target atomically."""
    target = Path(path)
    tmp_name = None
    try:
        target.parent.mkdir(parents=True, exist_ok=True)
        fd, tmp_name = tempfile.mkstemp(
            prefix=target.name + ".", suffix=".tmp", dir=str(target.parent)
        )
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(data, stream, ensure_ascii=False, indent=1)
        os.replace(tmp_name, target)
        tmp_name = None
        return True
    except (OSError, TypeError, ValueError):
        log.warning("Önbellek dosyası yazılamadı: %s", target, exc_info=True)
        return False
    finally:
        if tmp_name:
            try:
                os.unlink(tmp_name)
            except OSError:
                pass
