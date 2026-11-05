# FinanceTerminal 2.2.9-dev – Single Instance Fix

## Fix
- Replaced `QLocalServer.listen()`-only single-instance detection with a process-lifetime `QLockFile` lock.
- Kept `QLocalServer` / `QLocalSocket` only for sending the activation message to the primary instance.
- A second launch now exits without creating a second application window and signals the primary instance to restore itself from the system tray.
- The secondary process cannot remove or release the primary process lock.
- Added a regression check that a new process can become primary after the original primary closes.

## Validation
- Python compileall: passed.
- Unit tests: 44 discovered; 40 passed; 4 skipped because PySide6 is not installed in the local validation container.
- GitHub Actions workflow YAML: parsed successfully.
- The Windows/PySide6 single-instance regression test must be confirmed by the next GitHub Actions run.
