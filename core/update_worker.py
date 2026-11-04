from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from core.updater import check_latest_release, download_release_asset


class UpdateCheckWorker(QThread):
    completed = Signal(object)

    def __init__(self, current_version: str, parent=None):
        super().__init__(parent)
        self.current_version = current_version

    def run(self):
        try:
            release = check_latest_release(self.current_version)
            self.completed.emit({"release": release, "error": None})
        except Exception as exc:
            self.completed.emit({"release": None, "error": str(exc)})


class UpdateDownloadWorker(QThread):
    completed = Signal(object)

    def __init__(self, release, parent=None):
        super().__init__(parent)
        self.release = release

    def run(self):
        try:
            downloaded = download_release_asset(self.release)
            self.completed.emit({"path": str(downloaded), "error": None})
        except Exception as exc:
            self.completed.emit({"path": None, "error": str(exc)})
