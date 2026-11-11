import unittest

from features.profile_utils import profile_selector_label


class ProfileSelectorLabelTests(unittest.TestCase):
    def test_names_up_to_twenty_characters_are_shown_fully(self):
        self.assertEqual(profile_selector_label("Benim Portföyüm"), "Benim Portföyüm")
        self.assertEqual(profile_selector_label("12345678901234567890"), "12345678901234567890")

    def test_long_names_are_elided_without_changing_the_original(self):
        long_name = "Bu Profil Adı Yirmi Karakterden Uzun"
        label = profile_selector_label(long_name)
        self.assertEqual(label, long_name[:20].rstrip() + "...")
        self.assertEqual(len(long_name), 36)


if __name__ == "__main__":
    unittest.main()
