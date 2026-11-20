from __future__ import annotations

import unittest

from settings import resolve_theme
from ui.themes import EXTRA_THEMES, build_card_stylesheet, build_stylesheet


def _luminance(color: str) -> float:
    channels = [int(color[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    linear = [c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast(foreground: str, background: str) -> float:
    a, b = sorted((_luminance(foreground), _luminance(background)), reverse=True)
    return (a + 0.05) / (b + 0.05)


# (foreground key or literal, background key) pairs that must stay readable (WCAG AA = 4.5).
READABLE_PAIRS = [
    ("text", "bg"), ("text", "pane"), ("text", "input"), ("text", "button"),
    ("text", "button_hover"), ("text", "header"), ("text", "frame"), ("text", "panel"),
    ("text", "alt_row"), ("tab_text", "tab"), ("#ffffff", "tab_selected"),
    ("#ffffff", "selection"), ("#ffffff", "table_select"), ("muted", "bg"),
    ("muted", "panel"), ("card_subtitle", "card_bg"), ("card_value", "card_bg"),
    ("#ffffff", "card_bg"), ("accent", "bg"),
]


class ThemeTests(unittest.TestCase):
    def test_new_themes_are_selectable(self):
        for name in EXTRA_THEMES:
            self.assertEqual(resolve_theme(name), name)

    def test_palettes_are_complete_and_stylesheets_well_formed(self):
        keys = set(next(iter(EXTRA_THEMES.values())))
        for name, palette in EXTRA_THEMES.items():
            self.assertEqual(set(palette), keys, name)
            for stylesheet in (build_stylesheet(palette), build_card_stylesheet(palette)):
                self.assertEqual(stylesheet.count("{"), stylesheet.count("}"))
                self.assertNotIn("{p[", stylesheet)
                self.assertNotIn("None", stylesheet)

    def test_text_stays_readable_on_every_surface(self):
        for name, palette in EXTRA_THEMES.items():
            for foreground, background in READABLE_PAIRS:
                fg = palette.get(foreground, foreground)
                ratio = contrast(fg, palette[background])
                self.assertGreaterEqual(ratio, 4.5, f"{name}: {foreground} on {background} = {ratio:.2f}")


if __name__ == "__main__":
    unittest.main()
