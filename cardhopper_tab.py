# =====================================================================
# File: cardhopper_tab.py
# Project: nfsp00f3r V4.06 - EMV/NFC Sniffer, Card Manager & Companion
# Description: Cardhopper panel widget and logic.
# =====================================================================

from PyQt5.QtWidgets import QWidget, QGridLayout, QLabel, QPushButton, QComboBox
from PyQt5.QtCore import QThread, pyqtSignal
from relay import CardhopperRelay

class BatchWorker(QThread):
    status = pyqtSignal(str)
    count = pyqtSignal(int)

    def __init__(self, logger, pm_port):
        super().__init__()
        self.logger = logger
        self.pm_port = pm_port
        self._running = False
        self._count = 0

    def stop(self):
        self._running = False

    def run(self):
        self._running = True
        self._count = 0
        self.status.emit("batch started")
        # simple loop to demonstrate batch timing
        while self._running and self._count < 1000:
            self._count += 1
            self.count.emit(self._count)
            self.msleep(10)
        self.status.emit("batch stopped")

class CardhopperTab(QWidget):
    def __init__(self, parent=None, logger=None, settings=None):
        super().__init__(parent)
        self.logger = logger
        self.settings = settings or {}
        self.pm_port = self.settings.get("proxmark_port", "/dev/ttyACM0")
        self.relay = None
        self._build_ui()

    def _build_ui(self):
        self.layout = QGridLayout(self)
        self.lbl = QLabel("Cardhopper status: idle")
        self.cmb = QComboBox()
        self.cmb.addItems(["Auto", "PCSC", "PN532", "ACR", "Proxmark3", "Chameleon"])
        self.btnConn = QPushButton("Connect")
        self.btnDisc = QPushButton("Disconnect")
        self.btnStart = QPushButton("Start Relay")
        self.btnSrvStart = QPushButton("Start Server")
        self.btnSrvStop = QPushButton("Stop Server")
        self.lblCount = QLabel("cards read: 0")

        self.layout.addWidget(self.lbl, 0, 0, 1, 2)
        self.layout.addWidget(QLabel("Device:"), 1, 0)
        self.layout.addWidget(self.cmb, 1, 1)
        self.layout.addWidget(self.btnConn, 2, 0)
        self.layout.addWidget(self.btnDisc, 2, 1)
        self.layout.addWidget(self.btnStart, 3, 0)
        self.layout.addWidget(self.btnSrvStart, 3, 1)
        self.layout.addWidget(self.btnSrvStop, 4, 1)
        self.layout.addWidget(self.lblCount, 5, 0, 1, 2)

        self.btnConn.clicked.connect(self._on_connect)
        self.btnDisc.clicked.connect(self._on_disconnect)
        self.btnStart.clicked.connect(self._on_start)
        self.btnSrvStart.clicked.connect(self._on_server)
        self.btnSrvStop.clicked.connect(self._on_stop_server)

    def _on_connect(self):
        self.relay = CardhopperRelay(logger=self.logger, pm_port=self.pm_port)
        self.lbl.setText("Cardhopper connected")

    def _on_disconnect(self):
        self.relay = None
        self.lbl.setText("Cardhopper disconnected")

    def _on_start(self):
        if not self.relay:
            self._on_connect()
        # here you would drive APDUs through self.relay.forward_apdu
        self.lbl.setText("Cardhopper relay active")

    def _on_server(self):
        if not self.relay:
            self.relay = CardhopperRelay(logger=self.logger, pm_port=self.pm_port, server_host="0.0.0.0", server_port=9000)
        else:
            self.relay.pm.start_cardhopper_server("0.0.0.0", 9000)
        self.lbl.setText("Cardhopper server running on 0.0.0.0:9000")

    def _on_stop_server(self):
        if self.relay:
            self.relay.pm.stop_cardhopper_server()
        self.lbl.setText("Cardhopper connected" if self.relay else "Cardhopper idle")
