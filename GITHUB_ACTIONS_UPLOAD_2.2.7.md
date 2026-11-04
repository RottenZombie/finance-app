# FinanceTerminal 2.2.7-dev - GitHub Actions EXE build

This source package is prepared for the existing `bist-ai-2.2.1` branch.

- No new branch is required.
- `main` is not targeted by the build workflow.
- Pushes to `bist-ai-2.2.1` trigger `.github/workflows/build.yml`.
- GitHub Actions installs `requirements.txt`, verifies imports, runs tests, and builds `FinanceTerminal.exe` with `assets/finance_terminal.ico` and the `assets` directory included.
- The Actions artifact is named `FinanceTerminal-2.2.7-Windows-x64` and contains `FinanceTerminal.exe` plus `build-info.txt`.
- This is an Actions test artifact only. Do not create a GitHub Release until the user has tested the EXE.

When copying this package into the existing local Git clone, copy the contents of `finance-app-main` into the repository root. Do not copy local `.venv`, local databases, or temporary files. The repository `.gitignore` excludes local database files.
