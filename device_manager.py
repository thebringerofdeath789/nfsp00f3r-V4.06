# =====================================================================
# File: device_manager.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   DeviceManager enumerates and manages all reader hardware:
#   - PCSC, PN532 (NFC), BLE, Magstripe, and virtual devices.
#
# Classes:
#   - DeviceManager
# =====================================================================

from cardreader_pcsc import PCSCCardReader
from cardreader_pn532 import PN532Reader
from proxmark_manager import Proxmark3Manager
from bluetooth_api import BleakBluetoothManager
from magstripe_writer import MagstripeWriter

class DeviceManager:
    """
    Provides enumeration and access to all reader and emulation devices.
    """
    def __init__(self, logger, settings):
        self.logger = logger
        self.settings = settings
        self.pcsc = PCSCCardReader(logger=logger)
        self.pn532 = PN532Reader(logger=logger)
        self.ble = BleakBluetoothManager(logger=logger, settings=settings)
        self.magstripe = MagstripeWriter(logger=logger)
        self._enumerate_all()

    def _enumerate_all(self):
        self.pcsc.enumerate_readers()
        self.pn532.enumerate_interfaces()
        self.ble.enumerate_devices()
        self.magstripe.enumerate_devices()

    def list_all(self):
        return {
            "pcsc": self.pcsc.list_readers(),
            "pn532": self.pn532.list_interfaces(),
            "ble": self.ble.list_devices(),
            "magstripe": self.magstripe.list_devices()
        }

    def get_reader(self, typ, index=0):
        """
        Returns the selected device interface or reader for the given type and index.
        Logs a warning if the device type is unknown.
        """
        if typ == "pcsc":
            return self.pcsc.get_reader(index)
        elif typ == "pn532":
            return self.pn532.get_interface(index)
        elif typ == "proxmark":
            if self.proxmark is None:
                try:
                    self.proxmark = Proxmark3Manager(logger=self.logger)
                except Exception:
                    self.proxmark = None
            return self.proxmark
        elif typ == "ble":
            return self.ble.get_device(index)
        elif typ == "magstripe":
            return self.magstripe.get_device(index)
        else:
            if self.logger:
                self.logger.log(f"[DeviceManager] Unknown device type requested: {typ}", "WARN")
            return None
