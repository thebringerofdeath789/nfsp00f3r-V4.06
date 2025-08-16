# =====================================================================
# File: cardreader_pn532.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   PN532 (NFC) reader interface using nfcpy. Scans, polls, and emulates
#   Type4 tags; can forward APDU flows and handle debounced polling.
#
# Classes:
#   - PN532Reader
# =====================================================================

import threading
import time
import nfc

from emvcard import EMVCard

class PN532Reader:
    def __init__(self, logger=None):
        self.logger = logger
        self.clf = None
        self._thread = None
        self._stop = threading.Event()
        self._debounce = 2.0
        self._interval = 0.1
        self._callback = None
        self._interfaces = ["usb"]

    def enumerate_interfaces(self):
        # For nfcpy, typically only "usb"
        self._interfaces = ["usb"]

    def list_interfaces(self):
        return self._interfaces

    def get_interface(self, idx=0):
        """
        Returns the interface string at index idx, or logs a warning if not found.
        """
        if self._interfaces and 0 <= idx < len(self._interfaces):
            return self._interfaces[idx]
        if self.logger:
            self.logger.log(f"[PN532] get_interface: No interface at index {idx}", "WARN")
        return "usb"

    def read_card(self, interface="usb"):
        try:
            with nfc.ContactlessFrontend(interface) as clf:
                tag = clf.connect(rdwr={"on-connect": lambda tag: False})
                if tag.ndef:
                    conn = tag
                    emv_card = EMVCard(conn)
                    if self.logger:
                        self.logger.log(f"[PN532] Read card on {interface}")
                    return emv_card
        except Exception as e:
            if self.logger:
                self.logger.log(f"[PN532] Error reading card: {e}", "ERROR")
            return None

    def start_polling(self, callback, debounce=2.0, interval=0.1):
        self._callback = callback
        self._debounce = debounce
        self._interval = interval
        self._stop.clear()
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._poll_loop, daemon=True)
        self._thread.start()

    def stop_polling(self):
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _poll_loop(self):
        while not self._stop.is_set():
            try:
                card = self.read_card()
                if card:
                    self._callback(card)
                    time.sleep(self._debounce)
                else:
                    time.sleep(self._interval)
            except Exception as e:
                if self.logger:
                    self.logger.log(f"[PN532] Poll loop error: {e}", "ERROR")
                time.sleep(self._interval)
