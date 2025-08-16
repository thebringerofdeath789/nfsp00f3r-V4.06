# =====================================================================
# File: apdu.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-15
#
# Description:
#   APDU logger with Qt signals. Keeps a bounded history and emits
#   events on send and receive to integrate with UI and storage.
#
# Classes:
#   - APDULogger
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal

class APDULogger(QObject):
    log_updated = pyqtSignal(str)
    apdu_sent = pyqtSignal(bytes)
    apdu_received = pyqtSignal(bytes)

    def __init__(self, capacity: int = 2000):
        super().__init__()
        self._max = max(100, capacity)
        self._log = []

    def log_send(self, apdu_bytes: bytes):
        msg = f">> {apdu_bytes.hex().upper()}"
        self._append(msg)
        self.apdu_sent.emit(apdu_bytes)

    def log_recv(self, apdu_bytes: bytes):
        msg = f"<< {apdu_bytes.hex().upper()}"
        self._append(msg)
        self.apdu_received.emit(apdu_bytes)

    def _append(self, msg: str):
        self._log.append(msg)
        if len(self._log) > self._max:
            self._log = self._log[-self._max:]
        self.log_updated.emit(msg)

    def get_log(self):
        return list(self._log)

    def clear(self):
        self._log.clear()
        self.log_updated.emit("[CLEARED]")
