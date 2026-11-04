# FinanceTerminal 2.2.7-dev

- BIST tab now displays the saved Notes field in the holdings table.
- All investment tables allow manual column resizing; starting widths are sensible defaults.
- Portfolio and Metals panels display the last quote refresh timestamp and online/offline status.
- Optional system-tray behavior on close, with a remember-choice checkbox.
- Tray icon supports restore and explicit Exit actions.
- Hiding to the tray does not trigger automatic price refresh; only the existing manual Update action refreshes prices.
- Fixed the BIST UI test to use the PySide6 QAbstractItemView enum correctly.
