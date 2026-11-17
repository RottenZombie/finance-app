# FinanceTerminal 2.2.0 – BIST integration notes

## Preserved

- Currency tab and Open ER API worker
- Existing currency-conversion Portfolio tab
- Metals tab
- Existing `config.json` keys (`theme`, `precision`, `start_tab`)
- Existing GitHub Actions Windows PyInstaller workflow

## Added

- Fourth tab: `BIST AI`
- Local SQLite holdings database
- Manual add/update/delete
- `.xlsx` import/export with Turkish/English header aliases
- 2.2.0 version label
- Wider initial application window

## Data privacy

The BIST database is stored under the user's Windows `%APPDATA%` folder, not in the Git checkout. Database and SQLite WAL files are ignored by Git as an extra safeguard.

## Verification

- Six Python unit tests pass.
- Syntax compilation (`compileall`) passes.
- A 25-symbol storage and Excel round-trip smoke test passes.
- A visual Qt run and final Windows EXE build have not been performed in this environment because PySide6/Windows are unavailable here. Run the existing GitHub Actions workflow after committing the source to validate the Windows package.
