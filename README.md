[![Total Downloads](https://img.shields.io/github/downloads/RottenZombie/finance-app/total?color=blue&label=Downloads)](https://github.com/RottenZombie/finance-app/releases/latest)
[![Open Issues](https://img.shields.io/github/issues/RottenZombie/finance-app)](https://github.com/RottenZombie/finance-app/issues)
[![Windows](https://img.shields.io/badge/Platform-Windows%20-0078D4?logo=windows&logoColor=white&style=flat-square)](https://github.com/RottenZombie/finance-app/tree/bist-ai-2.2.1)
[![Language](https://img.shields.io/badge/Language-Python%203.11+-3776AB?logo=python&logoColor=white&style=flat-square)](https://github.com/RottenZombie/finance-app/tree/bist-ai-2.2.1)

[![Logo](assets/finance_terminal.png)](https://github.com/RottenZombie/finance-app/tree/bist-ai-2.2.1)

# FinanceTerminal 2.3.3

A lightweight Windows desktop application for currency conversion and personal portfolio tracking. Built with Python and PySide6, with local SQLite storage for investment records.

**Current version:** `2.3.3`  
**Platform:** Windows x64  
**Download:** [Latest GitHub Release](https://github.com/RottenZombie/finance-app/releases/latest)

---

## Features

### Summary
- Shows the combined portfolio overview for Currency, Metals, and BIST holdings.
- Displays current TRY, EUR, and USD equivalents where the required market quotes are available.
- Shows unrealized profit/loss for currency and metal holdings when current prices are available.
- BIST holdings are shown at recorded acquisition cost until a live BIST price feed is added. BIST is therefore excluded from market-based unrealized profit/loss.

### Currency
- USD/TRY, EUR/TRY, HUF/TRY, and additional supported foreign-currency rates.
- Choose which currency cards are visible; CHF (Swiss franc), CZK (Czech koruna), and other supported currencies can be enabled.
- Normal and inverse conversion display.
- Manual rate refresh.
- Saved holdings for supported currencies with quantity and weighted-average acquisition cost.
- Current TRY valuation and unrealized profit/loss when a current quote is available.

### Portfolio
- Track saved currency purchases separately from the currency converter.
- Repeated purchases of the same currency are merged using weighted-average acquisition cost.
- Double-click a saved row to edit its total quantity and average acquisition cost.
- Large TRY amounts use Turkish thousands separators and decimal formatting.
- View quantity, average cost, total cost, current price, current value, and unrealized profit/loss.
- Import and export portfolio records using Excel.

### Metals
- Track gold and silver purchases by gram.
- Repeated purchases of the same metal are merged using weighted-average acquisition cost.
- Double-click a saved row to edit its total quantity and average acquisition cost.
- Large gram quantities and TRY amounts use readable Turkish number formatting.
- View quantity, average cost, total cost, current gram price, current value, and unrealized profit/loss.
- Import and export metal holdings using Excel.

### BIST AI
- Local BIST share portfolio records using SQLite.
- Add, update, select, and remove share holdings.
- Store ticker, company, quantity, average acquisition cost, sector, and notes.
- Multi-row deletion and clear-all option with confirmation.
- Excel import/export.
- Resizable table columns.

> **Current limitation:** BIST AI is currently a local portfolio-management foundation. Live BIST prices, market-value and unrealized-return calculations, KAP scanning, and AI recommendations are not included in version 2.3.3. No broker login or automatic order placement is provided.

---

## Portfolio calculations

Repeated purchases of the same asset are merged using weighted-average acquisition cost. For example, buying 10 units at 30 TRY and another 10 units at 40 TRY produces 20 units at a 35 TRY average cost.

Current valuation is a snapshot based on the latest available quote when the application refreshes. It is not a historical price archive. If a required price quote is unavailable, the application does not treat the missing value as zero.

Metal valuation uses the application's spot-price feed converted to TRY per gram. Local dealer spreads, workmanship, taxes, and bank buy/sell spreads are not included.

---

## Excel import and export

- Individual Currency, Metals, and BIST sections support their own Excel import/export actions.
- The **Import All Portfolio from Excel** action reads Currency, Metals, and BIST holdings from one combined workbook.
- The **Export All Portfolio to Excel** action creates one workbook with these sheets:
  1. `Summary`
  2. `Döviz`
  3. `Maden`
  4. `Hisse Senedi`
  5. `Veri Bilgisi`
- Re-importing a matching record updates the saved snapshot instead of adding the same quantity again.
- The `Veri Bilgisi` sheet identifies the export timestamp, last available refresh information, data status, and human-readable source names/links.

---

## Application behavior and appearance

- Dark, light, and manually selectable blue themes. The initial light/dark choice follows the Windows appearance preference when available.
- Application icon included in the Windows build.
- Tables allow users to resize columns.
- Close-to-system-tray behavior can be selected and remembered from Settings. The tray menu can restore the main window or exit the application.
- When minimized to the tray, the application retains the latest displayed values. It does not perform background price refreshes; refresh remains manual.
- Up to three independent profiles can be used. Profile 1 and Profile 2 are available initially; Profile 3 is created from the Profile Add option. Each profile has separate Currency, Metals, and BIST records, and each profile name can be changed.
- Single-instance protection prevents multiple copies from opening. Starting the executable again restores/activates the existing application.
- Automatic update checks can be enabled or disabled from Settings. The application can check GitHub Releases at startup and also supports a manual update check.
- When a newer release is found, the user is asked before it is downloaded and installed. The download window shows the downloaded/total MB, percentage, and average speed in MB/s.
- The Windows updater waits for both processes used by a PyInstaller one-file application, stages and verifies the new EXE beside the current one, keeps the previous EXE temporarily, and attempts an automatic rollback if the new version does not stay open.
- The updater uses an explicit Windows PowerShell executable path and a hidden-process launch configuration to improve update-helper startup reliability.
- Launcher activity, startup failures, and update-helper errors are written to `%APPDATA%\FinanceTerminal\logs\updater.log`.
- The updater checks for early PowerShell process termination and records the process ID to simplify troubleshooting.
- Portfolio databases and settings remain in the user's application-data directory.
- The system-tray notification identifies the application as FinanceTerminal.

---

## Data storage and privacy

Portfolio data is stored locally in SQLite under the current user's application-data directory. Up to three profiles can be used; Profile 1 and Profile 2 are available initially, and Profile 3 is created from the Profile Add option. Each profile uses a separate database folder; the databases are not uploaded by the application.

Typical Windows locations:

- Settings: `%APPDATA%\FinanceTerminal\config.json`
- Profile 1 BIST: `%APPDATA%\FinanceTerminal\profiles\profile1\data\bist_portfolio.db`
- Profile 1 Currency / Metals: `%APPDATA%\FinanceTerminal\profiles\profile1\data\investment_holdings.db`
- Profile 2 databases use the same paths under `profiles\profile2\data`.

If an older installation has its `config.json` next to the executable, the application migrates that configuration into the application-data directory on startup. On first launch of version 2.3.0, the existing 2.2.x `data` folder is copied into Profile 1; the original folder is left untouched as a recovery copy. Portfolio databases are not stored beside the executable.

The application retrieves market quotes from the configured public data providers. The combined Excel export records source names and links for transparency.

---

## Installation

Download `FinanceTerminal.exe` from the [latest GitHub Release](https://github.com/RottenZombie/finance-app/releases/latest) and run it on Windows x64.

> **Windows SmartScreen note:** Current standalone builds are not digitally signed. Windows may therefore display an “Unknown publisher” / “Windows protected your PC” warning when the EXE is downloaded. Only proceed when the file was obtained from this project's official GitHub Releases page and you trust the source. A verified publisher name and improved SmartScreen reputation require a trusted code-signing identity; changing the updater alone cannot remove this warning.

The Windows x64 build is distributed as a standalone executable. User settings and portfolio data are stored separately in the current user’s application-data directory. When an update is installed, the updater replaces the executable without intentionally removing this data directory.

---

## Run from source

Requirements:

- Python 3.10+
- Dependencies listed in `requirements.txt`

PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python app.py
```

Run tests:

```powershell
python -m unittest discover -s tests -v
```

---

## Build

The GitHub Actions workflow builds a Windows x64 executable with PyInstaller and runs the test suite before packaging. The Windows application icon is included in the build. Excel import/export uses `openpyxl`.

---

## Version history

### 2.3.3
- Improved Windows automatic updater startup reliability.
- Changed the PowerShell helper launch configuration and uses an explicit Windows PowerShell executable path.
- Added Python-side updater launcher logging before the helper starts.
- Added logging of the helper process ID and early startup failures.
- Improved troubleshooting for cases where the update helper cannot start.
- Preserved staged EXE validation, temporary backup, rollback attempt, and automatic application restart.

### 2.3.2
- Updated application and Windows build version information to match the 2.3.2 release.

### 2.3.1
- Fixed the automatic updater for PyInstaller one-file Windows builds by waiting for both bootloader and application processes to close before replacing the EXE.
- Added live update download progress with downloaded/total MB, percentage, and average MB/s speed.
- Added staged EXE validation, temporary backup, rollback attempt when the new version does not remain open, and an updater log under `%APPDATA%\FinanceTerminal\logs\updater.log`.

### 2.3.0
- Added up to three independent local profiles; Profile 1 and Profile 2 are available initially, and Profile 3 is created on demand. Profile names can be changed.
- Migrates the existing 2.2.x data folder into Profile 1 by copying it, while keeping the original data folder as a recovery copy.
- Added selectable currency cards and expanded the supported currency catalog, including CHF and CZK.
- Added double-click editing of existing Currency and Metals holdings.
- Improved Turkish thousands/decimal formatting in the Portfolio and Metals calculators.
- Corrected Metals EUR conversion to use the current EUR/TRY quote rather than a fixed approximation.
- Clarified Summary valuation basis: Currency/Metals use current market quotes; BIST is included at recorded acquisition cost and excluded from unrealized K/Z until live quotes exist.

### 2.2.9
- Moved application settings into `%APPDATA%\FinanceTerminal\config.json` and added migration from the legacy executable-folder configuration file.
- Added Windows single-instance protection. Launching the executable again activates the already-running application instead of opening another copy.
- Added configurable automatic update checks at startup and a manual update-check action in Settings.
- Added user confirmation before downloading and installing a newer GitHub Release.
- Added an update helper that replaces the executable while keeping portfolio databases and settings in the application-data directory.
- Simplified the system-tray notification identity to FinanceTerminal.

### 2.2.7
- Added application tray behavior with a remembered close preference.
- Added adjustable column widths across portfolio tables.
- Added the BIST notes field to the holdings table.
- Added last-refresh information to Portfolio and Metals.
- Improved table selection and multi-row deletion workflows.
- Included the FinanceTerminal Windows application icon.

### 2.2.6
- Added multi-select and clear-all deletion to investment holdings.
- Added profit/loss visibility to Summary for assets with available current quotes.

### 2.2.5
- Added the FinanceTerminal application icon in SVG, PNG, and Windows ICO formats.
- Added combined Excel import for Currency, Metals, and BIST holdings.

### 2.2.2
- Added saved currency and metal purchase records with weighted-average acquisition cost.
- Added individual Excel import/export and combined portfolio workbook export.

### 2.2.1
- Fixed BIST summary-card ownership and widget lifetime handling.

### 2.2.0
- Added the BIST AI portfolio tab with local SQLite storage and Excel import/export.

---

## License

See the `LICENSE` file in this repository for the applicable license and terms.