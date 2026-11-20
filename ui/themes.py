"""Palette-driven themes added in 2.5.0 (the original White/Dark/Blue keep their stylesheets).

Each palette is rendered through the same selectors as the built-in dark theme,
so every widget (tabs, tables, investment panels, summary frames, cards) is covered.
"""
from __future__ import annotations

# Midnight: true-black (AMOLED friendly) with a cyan accent.
# Emerald: deep green "finance" look with a mint accent.
EXTRA_THEMES: dict[str, dict[str, str]] = {
    "Midnight": {
        "bg": "#000000", "text": "#e9f1ff", "pane": "#06080c", "border": "#1c2531",
        "tab": "#0b0f15", "tab_text": "#c9d6ea", "tab_selected": "#06080c",
        "accent": "#22d3ee", "button": "#0f141c", "button_border": "#22d3ee",
        "button_hover": "#16202c", "input": "#05070a", "input_border": "#263446",
        "selection": "#0e7490", "header": "#0f1620", "frame": "#080b10",
        "panel": "#070a0f", "panel_border": "#1f2c3b", "muted": "#9fb1c8",
        "alt_row": "#0a0e14", "row_line": "#141c27", "table_select": "#0e5c70",
        "card_bg": "#080b10", "card_border": "#1f3a4a", "card_subtitle": "#8fa6bf",
        "card_value": "#f5fbff",
    },
    "Emerald": {
        "bg": "#0a1612", "text": "#e6f4ee", "pane": "#0e1f19", "border": "#1f4a3b",
        "tab": "#12281f", "tab_text": "#cfe8dc", "tab_selected": "#173528",
        "accent": "#34d399", "button": "#14352a", "button_border": "#34d399",
        "button_hover": "#1b4a3a", "input": "#0f241c", "input_border": "#2a5e4a",
        "selection": "#1f7a5a", "header": "#16382c", "frame": "#10261e",
        "panel": "#0f231b", "panel_border": "#27594a", "muted": "#a7c9ba",
        "alt_row": "#12291f", "row_line": "#1a3a2d", "table_select": "#1f6b52",
        "card_bg": "#10261e", "card_border": "#2f7a5f", "card_subtitle": "#9cc4b3",
        "card_value": "#f2fff9",
    },
}


def build_stylesheet(p: dict[str, str]) -> str:
    return f"""
        QWidget {{ background: {p['bg']}; color: {p['text']}; }}
        QLabel {{ color: {p['text']}; background: transparent; }}
        QTabWidget::pane {{ background: {p['pane']}; border: 1px solid {p['border']}; }}
        QTabBar::tab {{ background: {p['tab']}; color: {p['tab_text']}; padding: 8px 12px; border: 1px solid {p['border']}; }}
        QTabBar::tab:selected {{ background: {p['tab_selected']}; color: #ffffff; border-bottom: 2px solid {p['accent']}; }}
        QPushButton {{ background: {p['button']}; color: {p['text']}; border: 1px solid {p['button_border']}; border-radius: 5px; padding: 5px 10px; }}
        QPushButton:hover {{ background: {p['button_hover']}; }}
        QPushButton:disabled {{ color: {p['muted']}; border-color: {p['border']}; }}
        QLineEdit, QComboBox, QTableWidget, QTextEdit {{ background: {p['input']}; color: {p['text']}; border: 1px solid {p['input_border']}; selection-background-color: {p['selection']}; selection-color: #ffffff; }}
        QComboBox QAbstractItemView {{ background: {p['input']}; color: {p['text']}; selection-background-color: {p['selection']}; }}
        QHeaderView::section {{ background: {p['header']}; color: {p['text']}; border: 1px solid {p['input_border']}; padding: 5px; }}
        QTableWidget::item {{ color: {p['text']}; }}
        QFrame#summaryFrame, QFrame#bistMetricCard, QFrame#bistFormFrame {{ background: {p['frame']}; color: {p['text']}; border: 1px solid {p['border']}; border-radius: 7px; }}
        QGroupBox {{ color: {p['text']}; border: 1px solid {p['border']}; border-radius: 6px; margin-top: 8px; padding-top: 8px; }}
        QGroupBox::title {{ color: {p['text']}; subcontrol-origin: margin; left: 8px; padding: 0 4px; }}
        QGroupBox#investmentPanel {{ background:{p['panel']}; border:1px solid {p['panel_border']}; border-radius:10px; margin-top:14px; padding:14px 10px 10px 10px; }}
        QGroupBox#investmentPanel::title {{ color:{p['text']}; left:12px; padding:0 6px; font-weight:700; }}
        QLabel#investmentInfo {{ color:{p['muted']}; }}
        QLabel#investmentLastUpdate {{ color:{p['muted']}; font-size:10px; }}
        QTableWidget#investmentTable {{ background:{p['input']}; alternate-background-color:{p['alt_row']}; color:{p['text']}; border:0; gridline-color:transparent; selection-background-color:{p['table_select']}; selection-color:#ffffff; }}
        QTableWidget#investmentTable::item {{ padding:6px 5px; border-bottom:1px solid {p['row_line']}; }}
        QTableWidget#investmentTable QHeaderView::section {{ background:{p['header']}; color:{p['text']}; border:0; border-bottom:2px solid {p['accent']}; padding:9px 6px; font-weight:700; }}
    """


def build_card_stylesheet(p: dict[str, str]) -> str:
    return f"""
        QFrame {{
            background:{p['card_bg']};
            border:1px solid {p['card_border']};
            border-radius:10px;
            padding:10px;
        }}
        QLabel#currencyCardTitle {{ color:#ffffff; font-size:13px; font-weight:800; }}
        QLabel#currencyCardSubtitle {{ color:{p['card_subtitle']}; font-size:9px; font-weight:500; }}
        QLabel#currencyCardValue {{ color:{p['card_value']}; font-size:17px; font-weight:750; }}
    """
