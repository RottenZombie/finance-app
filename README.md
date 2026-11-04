[![Toplam İndirme](https://img.shields.io/github/downloads/RottenZombie/finance-app/total?color=blue&label=Downloads)](https://github.com/RottenZombie/finance-app/releases/latest)
[![Last Commit](https://img.shields.io/github/last-commit/RottenZombie/finance-app)](https://github.com/RottenZombie/finance-app/commits/main)
[![Open Issues](https://img.shields.io/github/issues/RottenZombie/finance-app)](https://github.com/RottenZombie/finance-app/issues)

# FinanceTerminal 2.2.5-dev

## What is new in 2.2.5-dev

- Added the FinanceTerminal app icon in SVG, PNG, and multi-size Windows ICO formats.
- Set the application and window icon for source runs and PyInstaller builds.
- Added a one-step combined Excel import for Currency, Metals, and BIST holdings.
- Re-importing the same workbook replaces matching snapshots instead of doubling quantities.


FinanceTerminal is a PySide6 desktop application with Currency, Portfolio (currency conversion and holdings), Metals, and BIST AI tabs.

## What's new in 2.2.2

- Added saved purchase records to the existing Portfolio currency calculator for USD, EUR, and HUF. The currency calculator itself remains available.
- Added saved gram-based purchase records for gold and silver in Metals.
- Repeat purchases of the same asset are merged using weighted-average acquisition cost.
- The tables show quantity, average purchase price, total cost, current unit price, current value, and unrealized profit/loss.
- Current valuation uses the existing live exchange-rate and metal-price feeds. If a price feed is unavailable, the current value and profit/loss are shown as unavailable rather than as zero.
- Added Excel export of current holdings and valuation. Export is a snapshot at export time, not a historical price archive.
- Portfolio and Metals records are stored locally in SQLite under the user's FinanceTerminal application-data directory.

## What's new in 2.2.1

- Fixed the BIST summary-card ownership issue that could delete a QLabel when its local QFrame parent was garbage-collected. The BIST tab now keeps explicit references to both card frames and value labels.

## What's new in 2.2.0

- Added a separate **BIST AI** tab. The existing Portfolio currency calculator remains available.
- Added local SQLite storage for BIST holdings.
- Added manual entry, edit-through-selection, and deletion of holdings.
- Added Excel `.xlsx` import/export using Turkish and English column headings.
- Added portfolio count and total acquisition-cost summary.
- Stored BIST holdings under the current user's application-data directory, separate from the app folder and `config.json`.
- Updated the default window size and settings dialog to accommodate the additional tab.

## Current scope and limitations

- Portfolio supports saved USD, EUR, and HUF holdings with weighted-average purchase cost and current TRY valuation.
- Metals supports saved gold and silver gram holdings with weighted-average purchase cost and current TRY valuation.
- Metal valuation is based on the application's USD-per-troy-ounce spot-price feed converted to TRY per gram. Local dealer spreads, workmanship, taxes, and bank buy/sell spreads are not included.
- If a currency or metal price feed is unavailable, the current value and profit/loss are shown as unavailable.
- BIST AI remains a local portfolio data-entry foundation. It does not yet fetch live BIST prices, calculate market value/unrealized return, scan KAP, or generate AI recommendations. No broker login or automatic order placement is included.

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

- Windows BIST: `%APPDATA%\FinanceTerminal\data\bist_portfolio.db`
- Linux BIST: `$XDG_DATA_HOME/FinanceTerminal/data/bist_portfolio.db`, or `~/.local/share/FinanceTerminal/data/bist_portfolio.db`
- Windows Portfolio / Metals: `%APPDATA%\FinanceTerminal\data\investment_holdings.db`
- Linux Portfolio / Metals: `$XDG_DATA_HOME/FinanceTerminal/data/investment_holdings.db`, or `~/.local/share/FinanceTerminal/data/investment_holdings.db`

The SQLite databases remain on the user's computer and are not uploaded by the application.

## Tests

Run database, Excel I/O, and Qt UI smoke tests:

```powershell
python -m unittest discover -s tests -v
```

The UI smoke tests use Qt's offscreen platform. They are skipped automatically when PySide6 is not installed.

## Build

The GitHub Actions workflow builds a Windows x64 executable using PyInstaller. The workflow also runs tests before the build. `openpyxl` is included for Excel import/export.


## Portföy Excel işlemleri (2.2.2 and later)

- Döviz ve Maden sekmelerindeki kayıtlar ayrı Excel dosyalarına aktarılabilir ve aynı formatta dosyalardan içe alınabilir.
- İçe aktarma mevcut varlık koduyla eşleşirse kaydı dosyadaki miktar ve ortalama maliyetle günceller; miktarı tekrar ekleyerek iki katına çıkarmaz.
- Pencerenin üst kısmındaki **Tüm Portföyü Excel'e Aktar** düğmesi tek bir çalışma kitabı oluşturur. İlk sayfa `Summary`, devamında `Döviz`, `Maden` ve `Hisse Senedi` detay sayfaları yer alır.
- Summary içinde Döviz ve Maden güncel fiyatla değerlenir. Bu sürümde BIST canlı fiyat akışı bulunmadığından Hisse Senedi toplamı kayıtlı alış maliyetidir; genel toplamın hesaplama esası Summary notlarında belirtilir. Eksik fiyat/kur varsa genel toplam boş bırakılır.
- Birleşik çalışma kitabı Döviz, Maden ve BIST sekmelerinin mevcut içe aktarma özellikleriyle uyumludur.

## Otomatik güncelleme (Windows EXE)

FinanceTerminal, `RottenZombie/finance-app` GitHub deposunun en son kararlı Release kaydını kontrol eder. İlk açılışta otomatik kontrol tercihi sorulur; tercih hatırlanabilir. Ayarlar bölümünden otomatik kontrol açılıp kapatılabilir veya güncelleme elle denetlenebilir.

Yeni sürümün `FinanceTerminal.exe` varlığı HTTPS üzerinden indirilir. İndirilen dosya boyutu, Windows EXE imzası ve GitHub API SHA-256 özeti sunuyorsa bu özet doğrulanır. Çalışan EXE doğrudan değiştirilmez: uygulama kapandıktan sonra geçici PowerShell yardımcısı EXE'yi değiştirir ve yeniden başlatır. Uygulamanın bulunduğu klasör yazılabilir olmalıdır. Kaynak kodla (`python app.py`) çalıştırıldığında güncelleme kontrolü yapılabilir, ancak kaynak kod kendi kendini EXE olarak güncellemez.
