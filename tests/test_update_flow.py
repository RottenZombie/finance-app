from __future__ import annotations

import unittest

from core.update_flow import run_update_handoff


class UpdateHandoffTests(unittest.TestCase):
    def run_flow(self, *, launch_error=None, announce_error=None):
        events: list[str] = []

        def announce():
            events.append("announce")
            if announce_error:
                raise announce_error

        def launch():
            events.append("launch")
            if launch_error:
                raise launch_error

        result = run_update_handoff(
            announce=announce,
            launch=launch,
            on_failure=lambda exc: events.append(f"failure:{exc}"),
            exit_app=lambda: events.append("exit"),
        )
        return result, events

    def test_helper_is_launched_only_after_the_user_has_seen_the_message(self):
        result, events = self.run_flow()
        self.assertTrue(result)
        # Launching earlier made the helper time out when the user was slow to press OK.
        self.assertEqual(events, ["announce", "launch", "exit"])

    def test_if_the_helper_cannot_start_the_application_keeps_running(self):
        result, events = self.run_flow(launch_error=OSError("no powershell"))
        self.assertFalse(result)
        self.assertEqual(events, ["announce", "launch", "failure:no powershell"])
        self.assertNotIn("exit", events)

    def test_nothing_is_launched_if_the_message_itself_fails(self):
        with self.assertRaises(RuntimeError):
            self.run_flow(announce_error=RuntimeError("dialog crashed"))

    def test_helper_wait_is_much_longer_than_the_countdown(self):
        """The helper waits ~90 s for the app to exit; the countdown is a few seconds."""
        from pathlib import Path
        import re

        root = Path(__file__).resolve().parents[1]
        updater = (root / "core" / "updater.py").read_text(encoding="utf-8")
        wait = int(re.search(r"\.AddSeconds\((\d+)\)\s*\n\s*foreach \(\$appProcessId", updater).group(1))
        window = (root / "ui" / "main_window.py").read_text(encoding="utf-8")
        countdown = int(re.search(r"UPDATE_READY_AUTO_CONTINUE_SECONDS = (\d+)", window).group(1))
        self.assertLessEqual(countdown, 10)
        self.assertGreaterEqual(wait, 30)
        self.assertLess(countdown * 3, wait)


if __name__ == "__main__":
    unittest.main()
