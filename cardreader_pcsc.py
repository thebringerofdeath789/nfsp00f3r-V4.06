# =====================================================================
# File: cardreader_pcsc.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   PCSC smart card reader interface using pyscard. Supports reader
#   enumeration, card monitoring, APDU transmit, and callback on insert.
#
# Classes:
#   - PCSCCardReader
# =====================================================================

from smartcard.System import readers
from smartcard.util import toHexString
from smartcard.CardMonitoring import CardMonitor, CardObserver
from emvcard import EMVCard
from PyQt5.QtCore import QObject, pyqtSignal

class PCSCCardObserver(CardObserver):
    def __init__(self, callback):
        super().__init__()
        self.callback = callback

    def update(self, observable, changes):
        added, removed = changes
        for card in added:
            try:
                conn = card.createConnection()
                conn.connect()
                emv_card = EMVCard(conn)
                self.callback(emv_card)
            except Exception as e:
                print(f"[PCSCCardObserver] Failed to process inserted card: {e}")

class PCSCCardReader(QObject):
    card_inserted = pyqtSignal(object)
    def __init__(self, logger=None):
        super().__init__()
        self.logger = logger
        self._readers = []
        self.monitor = None
        self.observer = None
        self.enumerate_readers()

    def enumerate_readers(self):
        self._readers = readers()
        if self.logger:
            for idx, r in enumerate(self._readers):
                self.logger.log(f"[PCSC] Reader {idx}: {r}")

    def list_readers(self):
        return [str(r) for r in self._readers]

    def get_reader(self, idx=0):
        """
        Returns the PCSC reader object at index idx, or None if not found.
        Logs a warning if index is out of range or no readers found.
        """
        if not self._readers:
            self.enumerate_readers()
        if self._readers and 0 <= idx < len(self._readers):
            return self._readers[idx]
        if self.logger:
            self.logger.log(f"[PCSC] get_reader: No reader at index {idx}", "WARN")
        return None

    def read_card(self):
        """
        Attempts to connect to the first available reader and return an EMVCard.
        Logs errors if connection fails.
        Returns EMVCard instance or None on failure.
        """
        if not self._readers:
            self.enumerate_readers()
        try:
            r = self._readers[0]
            conn = r.createConnection()
            conn.connect()
            emv_card = EMVCard(conn)
            if self.logger:
                self.logger.log(f"[PCSC] Read card on {r}")
            return emv_card
        except Exception as e:
            if self.logger:
                self.logger.log(f"[PCSC] Error reading card: {e}", "ERROR")
            return None

    def start_monitoring(self, callback):
        """
        Starts monitoring for card insert/remove events and invokes callback.
        """
        if self.monitor:
            self.stop_monitoring()
        self.monitor = CardMonitor()
        self.observer = PCSCCardObserver(callback)
        self.monitor.addObserver(self.observer)
        if self.logger:
            self.logger.log("[PCSC] Monitoring started")

    def stop_monitoring(self):
        """
        Stops card monitoring.
        """
        if self.monitor and self.observer:
            self.monitor.deleteObserver(self.observer)
            if self.logger:
                self.logger.log("[PCSC] Monitoring stopped")
            self.monitor = None
            self.observer = None
