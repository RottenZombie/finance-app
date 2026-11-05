# FinanceTerminal 2.2.9-dev – Single-instance activation queue fix

- Kept `QLockFile` as the authoritative per-user single-instance lock.
- Replaced the fragile QLocalServer/QLocalSocket wake-up path with a per-user AppData request queue.
- The primary process polls activation requests on its Qt event loop and emits one activation for a batch of requests.
- Multiple rapid launches are coalesced into a single window activation.
- Added a test for multiple secondary launches.
- No portfolio databases, settings, or updater behavior were changed.

Validation in the current build environment:
- `python -m compileall -q .`: passed.
- `python -m unittest discover -s tests -v`: 44 discovered; 40 passed; 4 skipped because PySide6 is not installed in this environment.
- The Qt single-instance test is included in CI and must pass on the Windows runner before EXE packaging.
