# FinanceTerminal 2.2.7

A lightweight Windows desktop application for currency conversion and personal portfolio tracking. Built with Python and PySide6, with local SQLite storage for investment records.

**Latest stable version:** `2.2.7`  
**Platform:** Windows x64  
**Download:** [GitHub Releases](https://github.com/RottenZombie/finance-app/releases/latest)

---

## Features

### Summary
- Shows the combined portfolio overview for Currency, Metals, and BIST holdings.
- Displays current TRY, EUR, and USD equivalents where the required market quotes are available.
- Shows unrealized profit/loss for currency and metal holdings when current prices are available.
- BIST holdings are shown at recorded acquisition cost until a live BIST price feed is added. BIST is therefore excluded from market-based unrealized profit/loss.

### Currency
- USD/TRY, EUR/TRY, and HUF/TRY rates.
- Normal and inverse conversion display.
- Manual rate refresh.
- Saved USD, EUR, and HUF purchases with quantity and weighted-average acquisition cost.
- Current TRY valuation and unrealized profit/loss when a current quote is available.

### Portfolio
- Track saved currency purchases separately from the currency converter.
- Repeated purchases of the same currency are merged using weighted-average acquisition cost.
- View quantity, average cost, total cost, current price, current value, and unrealized profit/loss.
- Import and export portfolio records using Excel.

### Metals
- Track gold and silver purchases by gram.
- Repeated purchases of the same metal are merged using weighted-average acquisition cost.
- View quantity, average cost, total cost, current gram price, current value, and unrealized profit/loss.
- Import and export metal holdings using Excel.

### BIST AI
- Local BIST share portfolio records using SQLite.
- Add, update, select, and remove share holdings.
- Store ticker, company, quantity, average acquisition cost, sector, and notes.
- Multi-row deletion and clear-all option with confirmation.
- Excel import/export.
- Resizable table columns.

> **Current limitation:** BIST AI is currently a local portfolio-management foundation. Live BIST prices, market-value and unrealized-return calculations, KAP scanning, and AI recommendations are not included in version 2.2.7. No broker login or automatic order placement is provided.

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
- Close-to-system-tray behavior can be selected and remembered. The tray menu can restore the main window or exit the application.
- When minimized to the tray, the application retains the latest displayed values. It does not perform background price refreshes; refresh remains manual.

---

## Data storage and privacy

Portfolio data is stored locally in SQLite under the current user's application-data directory. The databases are not uploaded by the application.

Typical Windows locations:

- BIST: `%APPDATA%\\FinanceTerminal\\data\\bist_portfolio.db`
- Currency / Metals: `%APPDATA%\\FinanceTerminal\\data\\investment_holdings.db`

The application retrieves market quotes from the configured public data providers. The combined Excel export records source names and links for transparency.

---

## Installation

Download `FinanceTerminal.exe` from the [latest GitHub Release](https://github.com/RottenZombie/finance-app/releases/latest) and run it on Windows x64.

Version 2.2.7 is distributed as a standalone executable. User portfolio data is stored separately in the current user’s application-data directory.

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
