# FinanceTerminal 2.3.1-dev

## Automatic updater reliability
- Added live download progress showing downloaded MB, total MB, percentage, and average transfer speed in MB/s.
- Updated the download worker to stream progress events while retaining file-size, MZ-header, and optional SHA-256 verification.
- Fixed the PyInstaller `--onefile` shutdown race by waiting for both the application process and its bootloader parent process before replacing the running EXE.
- The downloaded EXE is staged in the target installation directory and validated before replacement.
- The existing EXE is temporarily backed up. If the new version exits during startup, the updater attempts to restore and relaunch the previous version.
- Added an updater log at `%APPDATA%\FinanceTerminal\logs\updater.log` for installation diagnostics.

## SmartScreen note
- This source update does not bypass Windows SmartScreen. Unsigned standalone releases can still show an Unknown Publisher warning. Eliminating the publisher warning requires a trusted code-signing identity and reputation, or distribution through a suitable trusted channel.
