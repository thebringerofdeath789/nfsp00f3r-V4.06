# =====================================================================
# File: cardreader_bluetooth.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Legacy BLE relay handler for card detection only. All advanced
#   logic now in BleakBluetoothManager.
#
# Classes:
#   - CardreaderBluetooth
# =====================================================================

class CardreaderBluetooth:
    def __init__(self, logger=None, bleak_manager=None):
        self.logger = logger
        self.bleak_manager = bleak_manager

    def start_server(self, callback):
        """
        Legacy interface. All BLE server/relay logic is now in BleakBluetoothManager.
        """
        if self.logger:
            self.logger.log("[CardreaderBluetooth] start_server is deprecated. Use BleakBluetoothManager.", "WARN")
        raise NotImplementedError("CardreaderBluetooth is deprecated. Use BleakBluetoothManager for BLE relay.")

    def send_card(self, card_json):
        """
        Legacy interface. All BLE server/relay logic is now in BleakBluetoothManager.
        """
        if self.logger:
            self.logger.log("[CardreaderBluetooth] send_card is deprecated. Use BleakBluetoothManager.", "WARN")
        raise NotImplementedError("CardreaderBluetooth is deprecated. Use BleakBluetoothManager for BLE relay.")
