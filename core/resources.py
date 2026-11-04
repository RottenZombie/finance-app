from __future__ import annotations

import sys
from pathlib import Path


def resource_path(relative_path: str) -> Path:
    """Resolve bundled resources both in source runs and PyInstaller one-file builds."""
    base = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[1]))
    return base / relative_path
