# FinanceTerminal 2.2.6-dev

## Portfolio management
- Multi-row selection is enabled in Portfolio, Metals and BIST AI tables (Ctrl/Shift selection).
- Added `Seçili Kayıtları Sil` and `Tüm Kayıtları Sil` to all three investment register sections.
- Bulk deletion is confirmed before execution and refreshes the Summary page.
- Action controls are aligned consistently across Portfolio, Metals and BIST AI.

## Summary
- Added unrealized P/L in TRY for Currency and Metals using current quotes versus weighted average cost.
- BIST P/L is shown as unavailable until live BIST quotes are implemented.
- General P/L intentionally excludes BIST and the Summary note says so.

## Windows icon
- Kept the supplied FinanceTerminal icon artwork.
- Added a stable Windows AppUserModelID for more reliable taskbar identity.
- The Windows build workflow embeds `assets/finance_terminal.ico` in the executable.

## Validation
- `python -m compileall -q .` passed.
- `python -m unittest discover -s tests -v`: 29 tests total; 26 passed, 3 Qt UI tests skipped because PySide6 is unavailable in the build environment.
