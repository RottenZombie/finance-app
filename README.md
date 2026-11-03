# FinanceTerminal 2.2.1

FinanceTerminal is a PySide6 desktop application with Currency, Portfolio (currency conversion), Metals, and the new BIST AI portfolio tab.

## What's new in 2.2.1

- Fixed the BIST summary-card ownership issue that could delete a QLabel when its local QFrame parent was garbage-collected. The BIST tab now keeps explicit references to both card frames and value labels.

## What's new in 2.2.0

- Added a separate **BIST AI** tab. The existing Portfolio currency calculator remains unchanged.
- Added local SQLite storage for BIST holdings.
- Added manual entry, edit-through-selection, and deletion of holdings.
- Added Excel `.xlsx` import/export using Turkish and English column headings.
- Added portfolio count and total acquisition-cost summary.
- Stored BIST holdings under the current user's application-data directory, separate from the app folder and `config.json`.
- Updated the default window size and settings dialog to accommodate the additional tab.

## Current scope and limitations

This release is the **portfolio data-entry foundation**. It does not yet fetch BIST prices, calculate market value/unrealized return, scan KAP, or generate AI recommendations. Those features will be added only after a reliable, permitted data source has been selected and tested. No broker login or automatic order placement is included.

## Requirements

- Python 3.10+
- Dependencies from `requirements.txt`

Install and run:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python app.py
```

## BIST Excel format

Required columns:

- `Hisse Kodu` (or `Sembol`, `Ticker`, `Symbol`)
- `Adet` (or `Lot`, `Miktar`, `Quantity`, `Shares`)
- `Ortalama Maliyet (TL)` (or `Ortalama Maliyet`, `Maliyet`, `Average Cost`, `Cost`)

Optional columns include `Şirket Adı`, `Sektör`, and `Notlar`. Existing symbols are updated during import. Exported files use the same compatible format.

Turkish numbers such as `1.234,56` and `74,50` are accepted.

## Local data location

- Windows: `%APPDATA%\FinanceTerminal\data\bist_portfolio.db`
- Linux: `$XDG_DATA_HOME/FinanceTerminal/data/bist_portfolio.db`, or `~/.local/share/FinanceTerminal/data/bist_portfolio.db`

The database contains only the portfolio fields entered into the BIST tab. It is not uploaded to a cloud service.

## Tests

Run repository, Excel I/O, and (when PySide6 is installed) BIST UI smoke tests:

```powershell
python -m unittest discover -s tests -v
```

The BIST UI smoke test uses Qt's offscreen platform and instantiates the actual tab. It is skipped automatically in environments where PySide6 is not installed.

## Build

The existing GitHub Actions workflow continues to build a Windows executable with PyInstaller. `openpyxl` is included as a runtime dependency for Excel import/export.
