# FinanceTerminal 2.2.9-dev

- Moved user settings to `%APPDATA%\FinanceTerminal\config.json`; legacy beside-EXE/current-folder config is migrated once and removed after successful copy.
- Kept Portfolio, Metals and BIST SQLite databases in `%APPDATA%\FinanceTerminal\data`. Updating the EXE does not replace user data.
- Changed the Windows notification identity to `FinanceTerminal` to remove the publisher prefix from tray notifications.
- Added Settings controls for close-to-tray behavior and automatic update checks.
- New stable releases are checked automatically only when enabled; finding a newer release always asks the user before download/install.
- Added per-Windows-user single-instance protection: launching the EXE again activates the existing window, including when minimized to the tray.
- Added app-data and single-instance tests.
