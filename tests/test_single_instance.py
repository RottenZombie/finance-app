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
            for _ in range(50):
                self.app.processEvents()
                if activations:
                    break
                time.sleep(0.01)
            self.assertEqual(activations, [True])
        finally:
            second.close()
            first.close()


if __name__ == "__main__":
    unittest.main()
