"""Single-instance guard using Qt's local-server IPC."""
from __future__ import annotations

import getpass
import hashlib
import re

from PySide6.QtCore import QObject, Signal
from PySide6.QtNetwork import QLocalServer, QLocalSocket


class SingleInstance(QObject):
    """Keep one FinanceTerminal process per Windows user/session.

    A later launch sends an activation message to the running process instead
    of creating another window. The primary instance emits ``activated``.
    """

    activated = Signal()
    MESSAGE = b"show-window"

    @staticmethod
    def server_name() -> str:
        username = getpass.getuser() or "user"
        safe_user = re.sub(r"[^A-Za-z0-9_-]", "_", username)[:32] or "user"
        suffix = hashlib.sha1(username.encode("utf-8", errors="ignore")).hexdigest()[:10]
        return f"FinanceTerminal_{safe_user}_{suffix}"

    def __init__(self, parent=None, *, server_name: str | None = None):
        super().__init__(parent)
        self._server = QLocalServer(self)
        self._server.newConnection.connect(self._accept_connections)
        self._server_name = server_name or self.server_name()
        self.is_primary = self._start_or_signal_existing()

    def _send_activation(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(self._server_name)
        if not socket.waitForConnected(1500):
            socket.abort()
            return False
        socket.write(self.MESSAGE)
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()
        return True

    def _start_or_signal_existing(self) -> bool:
        if self._server.listen(self._server_name):
            return True

        # If the endpoint belongs to a live process, wake it up and exit.
        if self._send_activation():
            return False

        # A crashed process can leave a stale local-server endpoint behind.
        QLocalServer.removeServer(self._server_name)
        if self._server.listen(self._server_name):
            return True

        # One final connect attempt handles a race with another simultaneous launch.
        if self._send_activation():
            return False
        self.error_string = self._server.errorString()
        return False

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
        """Release the local endpoint (mainly useful for orderly shutdown/tests)."""
        # A secondary instance does not own the endpoint and must never remove it.
        if self.is_primary:
            if self._server.isListening():
                self._server.close()
            QLocalServer.removeServer(self._server_name)
