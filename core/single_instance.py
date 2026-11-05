"""Single-instance guard using QLockFile and AppData activation signals.

QLockFile is the authoritative process lock.  A small per-user request queue
is used to wake the primary GUI instance.  The queue is deliberately file
based: it behaves consistently for two launches in the same process during
unit tests and for separate Windows processes, without relying on named-pipe
server semantics.
"""
from __future__ import annotations

import getpass
import hashlib
import os
import re
import tempfile
import uuid
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QLockFile, QTimer

from core.app_paths import app_data_directory


class SingleInstance(QObject):
    """Keep one FinanceTerminal process per Windows user/session."""

    activated = Signal()

    @staticmethod
    def server_name() -> str:
        username = getpass.getuser() or "user"
        safe_user = re.sub(r"[^A-Za-z0-9_-]", "_", username)[:32] or "user"
        suffix = hashlib.sha1(username.encode("utf-8", errors="ignore")).hexdigest()[:10]
        return f"FinanceTerminal_{safe_user}_{suffix}"

    @staticmethod
    def _storage_root(server_name: str) -> Path:
        if server_name == SingleInstance.server_name():
            root = app_data_directory() / "instance"
        else:
            # Custom names keep tests isolated and do not touch the user's app data.
            root = Path(tempfile.gettempdir()) / "FinanceTerminal_instance_tests"
        root.mkdir(parents=True, exist_ok=True)
        return root

    @staticmethod
    def _name_digest(server_name: str) -> str:
        return hashlib.sha256(server_name.encode("utf-8")).hexdigest()[:24]

    @classmethod
    def _lock_path(cls, server_name: str) -> Path:
        return cls._storage_root(server_name) / f"{cls._name_digest(server_name)}.lock"

    @classmethod
    def _request_directory(cls, server_name: str) -> Path:
        path = cls._storage_root(server_name) / f"{cls._name_digest(server_name)}.requests"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def __init__(self, parent=None, *, server_name: str | None = None):
        super().__init__(parent)
        self._server_name = server_name or self.server_name()
        self._lock_file = QLockFile(str(self._lock_path(self._server_name)))
        # A zero stale timeout means never remove a lock based only on age.
        # QLockFile still checks whether the owning PID is alive.
        self._lock_file.setStaleLockTime(0)
        self.activation_sent = False
        self.error_string = ""
        self.is_primary = self._start_or_signal_existing()

        self._activation_timer = QTimer(self)
        self._activation_timer.setInterval(75)
        self._activation_timer.timeout.connect(self._process_activation_requests)
        if self.is_primary:
            self._activation_timer.start()

    def _send_activation(self) -> bool:
        """Create a unique wake-up request for the primary process."""
        try:
            request_dir = self._request_directory(self._server_name)
            request_file = request_dir / f"{os.getpid()}-{uuid.uuid4().hex}.request"
            # Exclusive creation makes each launch a distinct, atomic signal.
            with request_file.open("xb") as handle:
                handle.write(b"show-window")
                handle.flush()
                os.fsync(handle.fileno())
            return True
        except OSError as exc:
            self.error_string = f"Ana uygulamaya uyandırma sinyali gönderilemedi: {exc}"
            return False

    def _start_or_signal_existing(self) -> bool:
        if not self._lock_file.tryLock(0):
            if self._lock_file.error() == QLockFile.LockError.LockFailedError:
                self.activation_sent = self._send_activation()
                return False
            self.error_string = f"Tek uygulama kilidi alınamadı: {self._lock_file.error()}"
            return False
        return True

    def _process_activation_requests(self) -> None:
        """Consume queued second-launch requests on the GUI event loop."""
        request_dir = self._request_directory(self._server_name)
        requests = list(request_dir.glob("*.request"))
        if not requests:
            return

        consumed = False
        for request_file in requests:
            try:
                request_file.unlink()
                consumed = True
            except FileNotFoundError:
                continue
            except OSError:
                # Leave an unreadable request for the next poll.
                continue

        if consumed:
            # Several fast launches should raise the window once, not repeatedly.
            self.activated.emit()

    def close(self) -> None:
        """Stop polling and release the process lock if this is the primary."""
        if self._activation_timer.isActive():
            self._activation_timer.stop()
        if self.is_primary:
            if self._lock_file.isLocked():
                self._lock_file.unlock()
            self.is_primary = False

