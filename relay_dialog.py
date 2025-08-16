# =====================================================================
# File: relay_dialog.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Dialog to live-forward card profiles via BLE to companion app/phone.
#
# Classes:
#   - RelayDialog(QDialog)
# =====================================================================

import threading
import time
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox,
    QPushButton, QHBoxLayout, QMessageBox
)
from nfsp00f3r.cardreader_pcsc import PCSCCardReader
from nfsp00f3r.cardreader_pn532 import PN532Reader
from nfsp00f3r.proxmark3_manager import Proxmark3Manager
from nfsp00f3r.chameleon_manager import ChameleonMiniManager
from nfsp00f3r.bluetooth_api import BleakBluetoothManager
from nfsp00f3r.emvcard import EMVCard

class RelayDialog(QDialog):
    def __init__(self, ble_manager: BleakBluetoothManager, parent=None):
        super().__init__(parent)
        self.ble = ble_manager
        self.pcsc = PCSCCardReader()
        self.pn532 = PN532Reader()
        self.proxmark = Proxmark3Manager()
        self.chameleon = ChameleonMiniManager()
        self._relay_thread = None
        self._stop_event = threading.Event()
        self.setWindowTitle("Relay Card")
        self.resize(360, 130)
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.cmb_reader = QComboBox(self)
        self.cmb_reader.addItems(["PCSC Reader", "PN532 Reader", "Proxmark3", "Chameleon Mini"])
        layout.addRow("Select Reader:", self.cmb_reader)

        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Relay", self)
        self.btn_start.clicked.connect(self.run_relay)
        btn_layout.addWidget(self.btn_start)

        self.btn_stop = QPushButton("Stop Relay", self)
        self.btn_stop.clicked.connect(self.stop_relay)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)

        layout.addRow(btn_layout)
    def run_relay(self):
        reader = None
        selected = self.cmb_reader.currentText()
        if selected == "PCSC Reader":
            reader = self.pcsc
        elif selected == "PN532 Reader":
            reader = self.pn532
        elif selected == "Proxmark3":
            reader = self.proxmark
        elif selected == "Chameleon Mini":
            reader = self.chameleon

        if not reader:
            QMessageBox.critical(self, "Error", "No reader selected or available.")
            return

        self._stop_event.clear()
        self._relay_thread = threading.Thread(target=self._relay_loop, args=(reader,))
        self._relay_thread.start()
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)

    def stop_relay(self):
        self._stop_event.set()
        self.btn_start.setEnabled(True)
        self.btn_stop.setEnabled(False)

    def _relay_loop(self, reader):
        while not self._stop_event.is_set():
            try:
                card = reader.read_emv_card()
                if card:
                    profile = card.export_profile()
                    self.ble.send_card(profile)
                    time.sleep(0.75)  # send every 750ms
            except Exception as e:
                print(f"[Relay] Error: {e}")
                time.sleep(1)
