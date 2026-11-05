"""Single-instance guard using QLockFile plus Qt local-server IPC."""
from __future__ import annotations

import getpass
import hashlib
import re
import tempfile
from pathlib import Path

from PySide6.QtCore import QObject, Signal, QLockFile
from PySide6.QtNetwork import QLocalServer, QLocalSocket

from core.app_paths import app_data_directory


class SingleInstance(QObject):
    """Keep one FinanceTerminal process per Windows user/session.

    QLockFile is the authoritative process lock. QLocalServer/QLocalSocket
    only carries the activation message. This distinction matters on Windows:
    named pipes may allow more than one server instance to listen on the same
    pipe name, so QLocalServer.listen() alone is not a single-instance guard.
    """

    activated = Signal()
    MESSAGE = b"show-window"

    @staticmethod
    def server_name() -> str:
        username = getpass.getuser() or "user"
        safe_user = re.sub(r"[^A-Za-z0-9_-]", "_", username)[:32] or "user"
        suffix = hashlib.sha1(username.encode("utf-8", errors="ignore")).hexdigest()[:10]
        return f"FinanceTerminal_{safe_user}_{suffix}"

    @staticmethod
    def _lock_path(server_name: str) -> Path:
        """Return a stable, per-user lock path; custom names isolate tests."""
        digest = hashlib.sha256(server_name.encode("utf-8")).hexdigest()[:24]
        if server_name == SingleInstance.server_name():
            root = app_data_directory() / "instance"
        else:
            root = Path(tempfile.gettempdir()) / "FinanceTerminal_instance_tests"
        root.mkdir(parents=True, exist_ok=True)
        return root / f"{digest}.lock"

    def __init__(self, parent=None, *, server_name: str | None = None):
        super().__init__(parent)
        self._server_name = server_name or self.server_name()
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._accept_connections)
        self._lock_file = QLockFile(str(self._lock_path(self._server_name)))
        # This lock is intentionally held for the lifetime of the GUI process.
        # Disable age-based staleness; QLockFile still detects dead local PIDs.
        self._lock_file.setStaleLockTime(0)
        self.activation_sent = False
        self.error_string = ""
        self.is_primary = self._start_or_signal_existing()

    def _send_activation(self, attempts: int = 5) -> bool:
        for _ in range(attempts):
            socket = QLocalSocket()
            socket.connectToServer(self._server_name)
            if socket.waitForConnected(400):
                socket.write(self.MESSAGE)
                socket.flush()
                socket.waitForBytesWritten(500)
                socket.disconnectFromServer()
                return True
            socket.abort()
        return False

    def _start_or_signal_existing(self) -> bool:
        # The process lock, not the pipe, decides which instance is primary.
        if not self._lock_file.tryLock(0):
            if self._lock_file.error() == QLockFile.LockError.LockFailedError:
                self.activation_sent = self._send_activation()
                # Never start another GUI process while a live lock exists,
                # even if the primary is still initializing its IPC server.
                return False
            self.error_string = f"Tek uygulama kilidi alınamadı: {self._lock_file.error()}"
            return False

        # We own the lock, so any old endpoint is necessarily stale.
        if not self._server.listen(self._server_name):
            QLocalServer.removeServer(self._server_name)
            if not self._server.listen(self._server_name):
                self.error_string = self._server.errorString()
                self._lock_file.unlock()
                return False
        return True

    def _accept_connections(self) -> None:
        while self._server.hasPendingConnections():
            socket = self._server.nextPendingConnection()
            if socket is None:
                continue
            socket.readyRead.connect(lambda s=socket: self._read_message(s))
            socket.disconnected.connect(socket.deleteLater)
            if socket.bytesAvailable():
                self._read_message(socket)

    def _read_message(self, socket: QLocalSocket) -> None:
        message = bytes(socket.readAll())
        if self.MESSAGE in message:
            self.activated.emit()

    def close(self) -> None:
        """Release IPC endpoint and process lock if this instance owns them."""
        if self.is_primary:
            if self._server.isListening():
                self._server.close()
            QLocalServer.removeServer(self._server_name)
            if self._lock_file.isLocked():
                self._lock_file.unlock()
            self.is_primary = False
