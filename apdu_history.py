# =====================================================================
# File: apdu_history.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Persistent APDU history per PAN, used for per-card session logs,
#   recall, and transaction analysis. Capped at 1000 entries per card.
#
# Classes:
#   - APDUHistory
# =====================================================================

import os
import json

try:
    from logger import Logger
    logger = Logger("apdu_history")
except ImportError:
    # Fallback to print if logger not available
    class DummyLogger:
        def error(self, msg): print("[APDUHistory][ERROR]", msg)
        def info(self, msg): pass
        def debug(self, msg): pass
    logger = DummyLogger()

class APDUHistory:
    """
    Handles persistent storage and recall of APDU log history, per card PAN.
    """
    def __init__(self, filename="apdu_history.json", max_entries=1000):
        self.filename = filename
        self.max_entries = max_entries
        self._db = {}
        self.load()

    def add(self, pan, entry):
        if pan not in self._db:
            self._db[pan] = []
        self._db[pan].append(entry)
        if len(self._db[pan]) > self.max_entries:
            self._db[pan] = self._db[pan][-self.max_entries:]
        self.save()

    def get(self, pan):
        return self._db.get(pan, [])

    def all(self):
        return self._db.copy()

    def save(self):
        try:
            with open(self.filename, "w", encoding="utf-8") as f:
                json.dump(self._db, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save APDU history: {e}")

    def load(self):
        if not os.path.isfile(self.filename):
            self._db = {}
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self._db = json.load(f)
        except Exception as e:
            logger.error(f"Failed to load APDU history: {e}")
            self._db = {}
