import unittest
from unittest.mock import patch

from settings import resolve_theme


class ThemePreferenceTests(unittest.TestCase):
    def test_system_preference_uses_detected_theme(self):
        with patch("settings.detect_system_theme", return_value="White"):
            self.assertEqual(resolve_theme("System"), "White")
        with patch("settings.detect_system_theme", return_value="Dark"):
            self.assertEqual(resolve_theme("System"), "Dark")

    def test_manual_blue_theme_is_preserved(self):
        with patch("settings.detect_system_theme", return_value="Dark"):
            self.assertEqual(resolve_theme("Blue"), "Blue")


if __name__ == "__main__":
    unittest.main()
