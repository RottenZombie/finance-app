"""List every text passed to tr()/tr_noop() so translations can be checked.

Usage:  python tools/i18n_keys.py            # print missing English entries
        python tools/i18n_keys.py --all      # print all keys
"""
from __future__ import annotations

import ast
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_DIRS = {"tests", "tools", "docs", ".git", "__pycache__", "build", "dist"}


def collect_keys(root: Path = ROOT) -> dict[str, list[str]]:
    """Return {turkish text: [file:line, ...]} for every literal tr()/tr_noop() call."""
    found: dict[str, list[str]] = {}
    for path in sorted(root.rglob("*.py")):
        relative = path.relative_to(root)
        if SKIP_DIRS & set(relative.parts) or relative.name == "translations_en.py":
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id in {"tr", "tr_noop"}
                and node.args
                and isinstance(node.args[0], ast.Constant)
                and isinstance(node.args[0].value, str)
            ):
                found.setdefault(node.args[0].value, []).append(f"{relative}:{node.lineno}")
    return found


def main(argv: list[str]) -> int:
    sys.path.insert(0, str(ROOT))
    keys = collect_keys()
    try:
        from core.translations_en import EN
    except ImportError:
        EN = {}
    shown = keys if "--all" in argv else {k: v for k, v in keys.items() if k not in EN}
    for index, (key, places) in enumerate(shown.items(), start=1):
        print(f"{index:3d} | {key!r}")
    print(f"\n{len(keys)} keys, {len([k for k in keys if k not in EN])} without an English entry")
    return 0 if all(k in EN for k in keys) else 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
