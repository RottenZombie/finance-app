"""Order of events when an update has been downloaded and verified.

The helper that replaces the EXE waits (about 90 seconds) for this application to
exit. It must therefore be started only *after* the user has seen the "update is
ready" message, immediately before the application closes. Starting it first meant
that a user who did not press OK in time got "the application process did not
close" and a rollback.
"""
from __future__ import annotations

from typing import Callable


def run_update_handoff(
    *,
    announce: Callable[[], None],
    launch: Callable[[], None],
    on_failure: Callable[[Exception], None],
    exit_app: Callable[[], None],
) -> bool:
    """Announce, then launch the helper, then exit. Returns True if the app is exiting.

    ``announce`` may take any amount of time (a dialog with a countdown); nothing
    time-critical has been started yet. If the helper cannot be launched the
    application keeps running and ``on_failure`` explains why.
    """
    announce()
    try:
        launch()
    except Exception as exc:
        on_failure(exc)
        return False
    exit_app()
    return True
