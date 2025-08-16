# =====================================================================
# File: emv_crypto_keys.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Utility for storing, searching, importing, exporting, and clearing EMV keys.
#
# Classes:
#   - EMVCryptoKeys
# =====================================================================

import json
import os
import tempfile
import shutil

class EMVCryptoKeys:
    """
    Stores, retrieves, imports, exports, and clears EMV keys.
    Each key entry is mapped by PAN (Primary Account Number) and AID (Application ID).
    """
    def __init__(self, filename="emv_keys.json", logger=None):
        self.filename = filename
        self.keys = {}
        self.logger = logger
        self.load()

    def load(self):
        """
        Loads keys from disk, or resets if file does not exist or is corrupted.
        """
        if not os.path.isfile(self.filename):
            self.keys = {}
            return
        try:
            with open(self.filename, "r", encoding="utf-8") as f:
                self.keys = json.load(f)
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Error loading keys: {e}", "ERROR")
            else:
                print(f"[EMVCryptoKeys] Error loading keys: {e}")
            self.keys = {}

    def save(self):
        """
        Saves the current key dictionary to disk atomically.
        """
        try:
            temp_fd, temp_path = tempfile.mkstemp()
            with os.fdopen(temp_fd, 'w', encoding="utf-8") as f:
                json.dump(self.keys, f, indent=2)
            shutil.move(temp_path, self.filename)
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Error saving keys: {e}", "ERROR")
            else:
                print(f"[EMVCryptoKeys] Error saving keys: {e}")

    def add(self, pan, aid, key_data):
        """
        Adds a key for the given PAN and AID. Overwrites if already present.
        """
        if pan not in self.keys:
            self.keys[pan] = {}
        self.keys[pan][aid] = key_data
        self.save()
        if self.logger:
            self.logger.log(f"[EMVCryptoKeys] Added/Updated key for PAN={pan}, AID={aid}")

    def get(self, pan, aid):
        """
        Returns the key data for the given PAN and AID, or None if not found.
        """
        return self.keys.get(pan, {}).get(aid)

    def remove(self, pan, aid=None):
        """
        Removes a key for a PAN/AID combo, or removes all keys for a PAN if aid is None.
        """
        changed = False
        if pan in self.keys:
            if aid:
                if aid in self.keys[pan]:
                    del self.keys[pan][aid]
                    changed = True
                    if not self.keys[pan]:
                        del self.keys[pan]
                else:
                    if self.logger:
                        self.logger.log(f"[EMVCryptoKeys] No such AID {aid} for PAN {pan} to remove.", "WARN")
            else:
                del self.keys[pan]
                changed = True
            if changed:
                self.save()
                if self.logger:
                    self.logger.log(f"[EMVCryptoKeys] Removed key(s) for PAN={pan}, AID={aid if aid else '*'}")
        else:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] No such PAN {pan} to remove.", "WARN")

    def list_all(self):
        """
        Returns the full dictionary of all PAN/AID keys.
        """
        return self.keys

    def import_keys(self, filename):
        """
        Imports keys from another JSON file, merging with the current key dictionary.
        """
        try:
            with open(filename, "r", encoding="utf-8") as f:
                data = json.load(f)
                for pan, aids in data.items():
                    if pan not in self.keys:
                        self.keys[pan] = {}
                    for aid, key_data in aids.items():
                        self.keys[pan][aid] = key_data
            self.save()
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Imported keys from {filename}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Error importing keys: {e}", "ERROR")
            else:
                print(f"[EMVCryptoKeys] Error importing keys: {e}")

    def export_keys(self, filename):
        """
        Exports the full key dictionary to a JSON file.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(self.keys, f, indent=2)
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Exported keys to {filename}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Error exporting keys: {e}", "ERROR")
            else:
                print(f"[EMVCryptoKeys] Error exporting keys: {e}")

    def clear(self):
        """
        Removes all keys from the dictionary and deletes the key file.
        """
        self.keys = {}
        self.save()
        try:
            if os.path.isfile(self.filename):
                os.remove(self.filename)
                if self.logger:
                    self.logger.log(f"[EMVCryptoKeys] Key file {self.filename} deleted.")
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCryptoKeys] Error deleting key file: {e}", "ERROR")
            else:
                print(f"[EMVCryptoKeys] Error deleting key file: {e}")
