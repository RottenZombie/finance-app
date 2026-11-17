from __future__ import annotations

import unittest

from core import autostart
from core.autostart import RUN_PATH, APPROVED_PATH, VALUE_NAME


class FakeKey:
    def __init__(self, store, path):
        self.store, self.path = store, path

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


class FakeRegistry:
    """Minimal in-memory stand-in for the winreg module."""
    HKEY_CURRENT_USER = "HKCU"
    KEY_READ = 1
    KEY_SET_VALUE = 2
    REG_SZ = 1

    def __init__(self, fail_writes=False):
        self.data: dict[str, dict[str, tuple]] = {}
        self.fail_writes = fail_writes

    def OpenKey(self, _root, path, _reserved=0, _access=1):
        if path not in self.data:
            raise FileNotFoundError(path)
        return FakeKey(self.data, path)

    def CreateKey(self, _root, path):
        if self.fail_writes:
            raise PermissionError("denied")
        self.data.setdefault(path, {})
        return FakeKey(self.data, path)

    def QueryValueEx(self, key, name):
        try:
            return key.store[key.path][name]
        except KeyError:
            raise FileNotFoundError(name) from None

    def SetValueEx(self, key, name, _reserved, kind, value):
        if self.fail_writes:
            raise PermissionError("denied")
        key.store[key.path][name] = (value, kind)

    def DeleteValue(self, key, name):
        try:
            del key.store[key.path][name]
        except KeyError:
            raise FileNotFoundError(name) from None


EXE = r"C:\Apps\FinanceTerminal\FinanceTerminal.exe"


class AutostartTests(unittest.TestCase):
    def test_command_quotes_the_path_and_marks_autostart(self):
        command = autostart.build_command(r"C:\Program Files\FT\FinanceTerminal.exe")
        self.assertTrue(command.startswith('"'))
        self.assertTrue(command.endswith('FinanceTerminal.exe" --autostart'))

    def test_enable_writes_run_value_and_disable_removes_it(self):
        reg = FakeRegistry()
        self.assertFalse(autostart.is_enabled(reg))
        self.assertTrue(autostart.set_enabled(True, reg, EXE))
        self.assertTrue(autostart.is_enabled(reg))
        value = reg.data[RUN_PATH][VALUE_NAME][0]
        self.assertIn("--autostart", value)
        self.assertTrue(autostart.set_enabled(False, reg, EXE))
        self.assertFalse(autostart.is_enabled(reg))
        self.assertNotIn(VALUE_NAME, reg.data[RUN_PATH])

    def test_disabling_when_nothing_is_registered_is_fine(self):
        self.assertTrue(autostart.set_enabled(False, FakeRegistry(), EXE))

    def test_task_manager_disabled_mark_is_respected_and_cleared_on_enable(self):
        reg = FakeRegistry()
        autostart.set_enabled(True, reg, EXE)
        reg.data[APPROVED_PATH] = {VALUE_NAME: (bytes([3, 0, 0, 0]) + bytes(8), 3)}
        self.assertFalse(autostart.is_enabled(reg))      # user switched it off in Windows
        reg.data[APPROVED_PATH] = {VALUE_NAME: (bytes([2, 0, 0, 0]) + bytes(8), 3)}
        self.assertTrue(autostart.is_enabled(reg))       # explicit "enabled" mark
        reg.data[APPROVED_PATH] = {VALUE_NAME: (bytes([3, 0, 0, 0]) + bytes(8), 3)}
        autostart.set_enabled(True, reg, EXE)            # user ticks the box again
        self.assertTrue(autostart.is_enabled(reg))

    def test_registry_failure_is_reported_not_raised(self):
        reg = FakeRegistry(fail_writes=True)
        self.assertFalse(autostart.set_enabled(True, reg, EXE))
        self.assertFalse(autostart.is_enabled(reg))

    def test_repair_updates_only_an_existing_entry_that_points_elsewhere(self):
        reg = FakeRegistry()
        self.assertFalse(autostart.repair_command(reg, EXE))          # nothing registered
        self.assertNotIn(RUN_PATH, reg.data)                          # and nothing created
        autostart.set_enabled(True, reg, r"D:\Old\FinanceTerminal.exe")
        self.assertTrue(autostart.repair_command(reg, EXE))
        self.assertIn(r"C:\Apps\FinanceTerminal\FinanceTerminal.exe", reg.data[RUN_PATH][VALUE_NAME][0])
        self.assertFalse(autostart.repair_command(reg, EXE))          # already correct

    def test_repair_keeps_a_task_manager_disabled_mark(self):
        reg = FakeRegistry()
        autostart.set_enabled(True, reg, r"D:\Old\FinanceTerminal.exe")
        reg.data[APPROVED_PATH] = {VALUE_NAME: (bytes([3, 0, 0, 0]) + bytes(8), 3)}
        autostart.repair_command(reg, EXE)
        self.assertFalse(autostart.is_enabled(reg))

    def test_support_requires_a_packaged_exe_and_a_registry(self):
        reg = FakeRegistry()
        self.assertTrue(autostart.is_supported(reg, frozen=True))
        self.assertFalse(autostart.is_supported(reg, frozen=False))

    def test_everything_is_inert_without_winreg(self):
        # On Linux/macOS there is no registry: nothing may raise.
        import sys
        if sys.platform != "win32":
            self.assertFalse(autostart.is_supported(frozen=True))
            self.assertFalse(autostart.is_enabled())
            self.assertFalse(autostart.set_enabled(True))
            self.assertFalse(autostart.repair_command())


if __name__ == "__main__":
    unittest.main()
