# =====================================================================
# File: bluetooth_api.py
# Safe minimal BLE manager to avoid runtime failures when Bleak not present.
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal

class BleakBluetoothManager(QObject):
    message_received = pyqtSignal(bytes)

    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger
        self.devices = []

    def scan(self):
        if self.logger:
            self.logger.log("[BLE] scan not implemented in minimal build", "WARN")
        return []

    def list_devices(self):
        return list(self.devices)

    def get_device(self, index=0):
        return self.devices[index] if 0 <= index < len(self.devices) else None

    def relay_apdu(self, apdu: bytes) -> bytes:
        if self.logger:
            self.logger.log("[BLE] relay_apdu not implemented in minimal build", "WARN")
        return b""
