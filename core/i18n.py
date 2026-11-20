"""Tiny translation layer: Turkish source text -> English.

The program's source strings are Turkish, so Turkish needs no lookup at all. In
English mode :func:`tr` looks the Turkish text up in ``translations_en.EN``; a
missing entry falls back to the Turkish text (a unit test guarantees there are
none). Texts with values use positional placeholders::

    tr("{0} hisse güncel").format(count)

The language is chosen once at startup (see ``app.py``) before any window is
built, so ``tr`` must be called while a window/export is being created, never
at import time.
"""
from __future__ import annotations

SUPPORTED_LANGUAGES = ("tr", "en")
DEFAULT_LANGUAGE = "tr"

_language = DEFAULT_LANGUAGE


def normalize_language(value: object) -> str:
    code = str(value or "").strip().lower()[:2]
    return code if code in SUPPORTED_LANGUAGES else DEFAULT_LANGUAGE


def set_language(value: object) -> str:
    global _language
    _language = normalize_language(value)
    return _language


def get_language() -> str:
    return _language


def is_english() -> bool:
    return _language == "en"


def tr(text: str) -> str:
    """Return ``text`` in the active language (Turkish is the source language)."""
    if _language != "en":
        return text
    from core.translations_en import EN  # imported lazily: it is large

    return EN.get(text, text)


def tr_noop(text: str) -> str:
    """Mark a Turkish text for translation without translating it yet.

    Used for constants defined at import time (table headers, column titles);
    translate them where they are used: ``tr(constant)``. A unit test collects
    these markers so every one has an English entry.
    """
    return text


def translate(text: str, language: str) -> str:
    """Translate ``text`` into an explicit language (independent of the active one).

    Used for the "language changed" prompt, which should already speak the language
    the user just picked.
    """
    if normalize_language(language) != "en":
        return text
    from core.translations_en import EN

    return EN.get(text, text)
