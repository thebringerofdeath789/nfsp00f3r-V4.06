# =====================================================================
# File: export_import.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Robust export/import of card profiles, transaction logs, APDU logs,
#   and key material in JSON and CSV. Supports backup/merge, phone
#   payloads, and legacy CSV import for track2.
#
# Classes:
#   - ExportImport
# =====================================================================

import json
import csv
import os

class ExportImport:
    """
    Exports and imports card data, APDU logs, key material.
    """
    def export_profile(self, card, filename):
        """
        Export a card profile as JSON (includes TLVs, logs, tracks, cryptos).
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(card.export_profile())
            return True
        except Exception as e:
            print(f"[Export] Error: {e}")
            return False

    def import_profile(self, filename, card_class):
        """
        Import a card profile from JSON, returns EMVCard instance.
        """
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()
        card = card_class(None)
        card.import_profile_json(data)
        return card

    def export_apdu_log(self, apdu_log, filename):
        """
        Export APDU log as CSV.
        """
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "direction", "apdu"])
                for entry in apdu_log:
                    ts = entry.get("ts", "")
                    direction = entry.get("dir", "")
                    apdu = entry.get("apdu", "")
                    writer.writerow([ts, direction, apdu])
            return True
        except Exception as e:
            print(f"[ExportAPDU] Error: {e}")
            return False

    def import_apdu_log(self, filename):
        """
        Import APDU log from CSV, returns list of dict entries.
        """
        entries = []
        with open(filename, "r", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append({
                    "ts": row.get("timestamp", ""),
                    "dir": row.get("direction", ""),
                    "apdu": row.get("apdu", "")
                })
        return entries

    def export_all_cards(self, cards, filename):
        """
        Export multiple card profiles as a JSON array.
        """
        try:
            arr = [json.loads(card.export_profile()) for card in cards]
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(arr, f, indent=2)
            return True
        except Exception as e:
            print(f"[ExportAll] Error: {e}")
            return False

    def import_all_cards(self, filename, card_class):
        """
        Import multiple card profiles from a JSON array.
        Returns a list of EMVCard instances.
        """
        cards = []
        with open(filename, "r", encoding="utf-8") as f:
            arr = json.load(f)
        for obj in arr:
            card = card_class(None)
            card.import_profile_json(json.dumps(obj))
            cards.append(card)
        return cards

    def export_phone_payload(self, card, filename):
        """
        Export card profile in phone-compatible format (minimal JSON).
        """
        obj = json.loads(card.export_profile())
        phone_fields = {
            "PAN": obj["info"].get("PAN"),
            "Expiry": obj["info"].get("Expiry"),
            "Track2": obj["track_data"].get("Track2", ""),
            "Name": obj["info"].get("Name"),
            "CVV": obj["info"].get("CVV", ""),
            "ZIP": obj["info"].get("ZIP", ""),
        }
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(phone_fields, f, indent=2)
            return True
        except Exception as e:
            print(f"[ExportPhone] Error: {e}")
            return False

    def merge_backups(self, filenames, outfilename):
        """
        Merge multiple card backup JSON files into one.
        """
        all_cards = []
        for fn in filenames:
            with open(fn, "r", encoding="utf-8") as f:
                cards = json.load(f)
                all_cards.extend(cards if isinstance(cards, list) else [cards])
        # Deduplicate by PAN
        seen = set()
        merged = []
        for card in all_cards:
            pan = card.get("info", {}).get("PAN")
            if pan and pan not in seen:
                seen.add(pan)
                merged.append(card)
        with open(outfilename, "w", encoding="utf-8") as f:
            json.dump(merged, f, indent=2)
        return True

    def export_keys(self, keys_obj, filename):
        """
        Export key database to file.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(keys_obj, f, indent=2)
            return True
        except Exception as e:
            print(f"[ExportKeys] Error: {e}")
            return False

    def import_keys(self, filename):
        """
        Import key database from file.
        """
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
