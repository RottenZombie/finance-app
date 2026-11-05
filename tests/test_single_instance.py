from __future__ import annotations

import importlib.util
import unittest
import uuid
import time

if importlib.util.find_spec("PySide6") is None:
    raise unittest.SkipTest("PySide6 is not installed")

from PySide6.QtCore import QCoreApplication
from core.single_instance import SingleInstance


class SingleInstanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QCoreApplication.instance() or QCoreApplication([])

    def test_second_launch_signals_primary_instead_of_starting_another_instance(self):
        name = "FinanceTerminal_Test_" + uuid.uuid4().hex
        first = SingleInstance(server_name=name)
        self.assertTrue(first.is_primary)
        activations = []
        first.activated.connect(lambda: activations.append(True))
        second = SingleInstance(server_name=name)
        try:
            self.assertFalse(second.is_primary)
            self.assertTrue(second.activation_sent)
            # The primary consumes the cross-launch request on its Qt event loop.
            deadline = time.monotonic() + 2.0
            while not activations and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertEqual(activations, [True])
        finally:
            second.close()
            first.close()

        # Once the primary releases its lock, a fresh launch can become primary.
        third = SingleInstance(server_name=name)
        try:
            self.assertTrue(third.is_primary)
        finally:
            third.close()

    def test_multiple_second_launches_are_coalesced_into_one_activation(self):
        name = "FinanceTerminal_Test_" + uuid.uuid4().hex
        first = SingleInstance(server_name=name)
        self.assertTrue(first.is_primary)
        activations = []
        first.activated.connect(lambda: activations.append(True))
        second_a = SingleInstance(server_name=name)
        second_b = SingleInstance(server_name=name)
        try:
            self.assertFalse(second_a.is_primary)
            self.assertFalse(second_b.is_primary)
            deadline = time.monotonic() + 2.0
            while not activations and time.monotonic() < deadline:
                self.app.processEvents()
                time.sleep(0.01)
            self.assertEqual(activations, [True])
        finally:
            second_a.close()
            second_b.close()
            first.close()


if __name__ == "__main__":
    unittest.main()
