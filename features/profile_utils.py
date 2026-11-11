"""Presentation helpers for the profile selector."""

MAX_PROFILE_SELECTOR_CHARS = 20


def profile_selector_label(profile_name: str) -> str:
    """Show up to 20 characters in the compact selector, then an ellipsis.

    The original profile name is never modified; exports continue to use the
    complete name stored in settings.
    """
    name = str(profile_name or "").strip()
    if len(name) <= MAX_PROFILE_SELECTOR_CHARS:
        return name
    return name[:MAX_PROFILE_SELECTOR_CHARS].rstrip() + "..."
