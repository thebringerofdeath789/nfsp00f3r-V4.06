# =====================================================================
# File: cardmanager.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   CardManager orchestrates all card events, storage, and lifecycle:
#   - Handles insert, remove, switching, duplicate prevention,
#     and proxying APDU flows from all device sources.
#
# Classes:
#   - CardManager
# =====================================================================

from PyQt5.QtCore import QObject, pyqtSignal
from emvcard import EMVCard

class CardManager(QObject):
    card_inserted = pyqtSignal(object)
    card_removed = pyqtSignal(str)  # PAN
    card_switched = pyqtSignal(object)
    apdu_sent = pyqtSignal(bytes)
    apdu_received = pyqtSignal(bytes)
    
    def __init__(self, logger, devices):
        super().__init__()
        self.logger = logger
        self.devices = devices
        self.cards = {}      # key: PAN, value: EMVCard
        self.current_pan = None

    def add_card(self, emv_card: EMVCard):
        pan = emv_card.get_cardholder_info().get("PAN", None)
        if not pan or pan in self.cards:
            return
        self.cards[pan] = emv_card
        self.current_pan = pan
        self.card_inserted.emit(emv_card)
        self.logger.log(f"Card added: {pan}")

    def remove_card(self, pan):
        if pan in self.cards:
            del self.cards[pan]
            self.card_removed.emit(pan)
            self.logger.log(f"Card removed: {pan}")
            if pan == self.current_pan:
                self.current_pan = next(iter(self.cards), None)
                if self.current_pan:
                    self.card_switched.emit(self.cards[self.current_pan])

    def switch_card(self, pan):
        if pan in self.cards:
            self.current_pan = pan
            self.card_switched.emit(self.cards[pan])
            self.logger.log(f"Switched to card: {pan}")

    def get_current_card(self):
        """
        Returns the currently active EMVCard instance, or None if none loaded.
        Logs a warning if no card is loaded.
        """
        if self.current_pan and self.current_pan in self.cards:
            return self.cards[self.current_pan]
        self.logger.log("[CardManager] No active card selected", "WARN")
        return None

    def list_cards(self):
        """
        Returns a list of all loaded EMVCard objects.
        """
        return list(self.cards.values())

    def proxy_apdu(self, apdu: bytes):
        """
        Proxies the given APDU to the current card.
        Emits apdu_sent and apdu_received signals.
        Returns the response APDU bytes, or None if no card is loaded.
        Logs an error if no card is present.
        """
        card = self.get_current_card()
        if not card:
            self.logger.log("[CardManager] proxy_apdu called with no card loaded", "ERROR")
            return None
        self.apdu_sent.emit(apdu)
        resp = card.send_apdu(apdu)
        self.apdu_received.emit(resp)
        return resp
