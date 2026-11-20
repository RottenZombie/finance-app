from __future__ import annotations

import os
import unittest
from unittest.mock import patch

from core import restart
from core.autostart import AUTOSTART_FLAG


class RestartCommandTests(unittest.TestCase):
    def test_packaged_exe_restarts_itself_without_the_autostart_flag(self):
        program, args = restart.restart_command(
            frozen=True, executable=r"C:\Apps\FinanceTerminal.exe",
            argv=[r"C:\Apps\FinanceTerminal.exe", AUTOSTART_FLAG, "--other"],
        )
        self.assertEqual(program, r"C:\Apps\FinanceTerminal.exe")
        self.assertEqual(args, ["--other"])

    def test_source_run_restarts_through_the_interpreter_and_script(self):
        program, args = restart.restart_command(
            frozen=False, executable="/usr/bin/python3", argv=["app.py"]
        )
        self.assertEqual(program, "/usr/bin/python3")
        self.assertEqual(len(args), 1)
        self.assertTrue(args[0].endswith("app.py") and os.path.isabs(args[0]))


class SpawnTests(unittest.TestCase):
    def test_spawn_resets_the_pyinstaller_environment_and_detaches(self):
        with patch("core.restart.subprocess.Popen") as popen:
            self.assertTrue(restart.spawn_detached("prog", ["a"]))
        command = popen.call_args.args[0]
        self.assertEqual(command, ["prog", "a"])
        self.assertEqual(popen.call_args.kwargs["env"]["PYINSTALLER_RESET_ENVIRONMENT"], "1")
        self.assertTrue(popen.call_args.kwargs["close_fds"])

    def test_spawn_failure_is_reported_not_raised(self):
        with patch("core.restart.subprocess.Popen", side_effect=OSError("nope")):
            self.assertFalse(restart.spawn_detached("missing", []))


if __name__ == "__main__":
    unittest.main()
