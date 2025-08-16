# =====================================================================
# File: replay_dialog.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Dialog to emulate a card to a POS using a PN532 device and APDU log.
#
# Classes:
#   - EMVType4TagEmulator(Type4TagEmulation)
#   - ReplayDialog(QDialog)
# =====================================================================

import json
import threading
import time
from PyQt5.QtWidgets import (
    QDialog, QFormLayout, QComboBox, QSpinBox,
    QPushButton, QHBoxLayout, QMessageBox
)
from nfsp00f3r.cardreader_pn532 import PN532Reader
from nfc.clf import ContactlessFrontend
from nfc.tag.tt4 import Type4TagEmulation

class EMVType4TagEmulator(Type4TagEmulation):
    def __init__(self, clf, apdu_map):
        super().__init__(clf)
        self.apdu_map = apdu_map

    def process_command(self, apdu):
        key = tuple(apdu)
        resp = self.apdu_map.get(key, [0x6F, 0x00])
        return resp

class ReplayDialog(QDialog):
    def __init__(self, emv_card, pn532_reader, parent=None):
        super().__init__(parent)
        self.card = emv_card
        self.apdu_log = emv_card.apdu_log
        self.setWindowTitle("Replay Card")
        self.resize(400, 150)
        self._replay_thread = None
        self._stop_event = threading.Event()
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.cmb_device = QComboBox(self)
        self.cmb_device.addItem("usb")
        layout.addRow("PN532 Device:", self.cmb_device)
        self.spin_count = QSpinBox(self)
        self.spin_count.setRange(1, 1000)
        self.spin_count.setValue(1)
        layout.addRow("Repeat Count:", self.spin_count)
        btn_layout = QHBoxLayout()
        self.btn_start = QPushButton("Start Replay", self)
        self.btn_start.clicked.connect(self.run_replay)
        btn_layout.addWidget(self.btn_start)
        self.btn_stop = QPushButton("Stop", self)
        self.btn_stop.clicked.connect(self._stop_event.set)
        self.btn_stop.setEnabled(False)
        btn_layout.addWidget(self.btn_stop)
        self.btn_cancel = QPushButton("Close", self)
        self.btn_cancel.clicked.connect(self.close)
        btn_layout.addWidget(self.btn_cancel)
        layout.addRow(btn_layout)

    def run_replay(self):
        if self._replay_thread and self._replay_thread.is_alive():
            return
        self._stop_event.clear()
        device = self.cmb_device.currentText()
        count = self.spin_count.value()
        apdu_map = {}
        for entry in self.apdu_log:
            cmd = [int(b, 16) for b in entry['cmd'].split()]
            parts = entry['resp'].split()
            resp = [int(b, 16) for b in parts]
            apdu_map[tuple(cmd)] = resp

        def target():
            try:
                with ContactlessFrontend(device) as clf:
                    for i in range(count):
                        if self._stop_event.is_set():
                            break
                        emulator = EMVType4TagEmulator(clf, apdu_map)
                        clf.connect(
                            rdwr={'on-connect': lambda tag: False},
                            emulation={'on-command': emulator.process_command},
                            terminate=lambda: self._stop_event.is_set(),
                            timeout=30.0
                        )
                        time.sleep(0.5)
            except Exception as e:
                QMessageBox.critical(self, "Replay Error", str(e))
            finally:
                self.btn_start.setEnabled(True)
                self.btn_stop.setEnabled(False)
        self.btn_start.setEnabled(False)
        self.btn_stop.setEnabled(True)
        self._replay_thread = threading.Thread(target=target, daemon=True)
        self._replay_thread.start()

    def closeEvent(self, event):
        self._stop_event.set()
        if self._replay_thread:
            self._replay_thread.join(timeout=1.0)
        super().closeEvent(event)
