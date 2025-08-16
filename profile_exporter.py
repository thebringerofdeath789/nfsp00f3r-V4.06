import json
import csv

class ProfileExporter:
    # ...existing code...

# Alias for backward compatibility with tests
ExportImport = ProfileExporter
# =====================================================================
# File: profile_exporter.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Simple legacy wrapper for exporting/importing card profiles and APDU logs
#   as JSON and CSV, used by the UI. For advanced features use export_import.py.
#
# Classes:
#   - ProfileExporter
# =====================================================================

import json
import csv

class ProfileExporter:
    def export(self, card, filename):
        try:
            with open(filename, "w", encoding="utf-8") as f:
                f.write(card.export_profile())
            return True
        except Exception as e:
            print(f"[Export] Error: {e}")
            return False

    def import_profile(self, filename, card_class):
        with open(filename, "r", encoding="utf-8") as f:
            data = f.read()
        card = card_class(None)
        card.import_profile_json(data)
        return card

    def export_apdu_log(self, log, filename):
        try:
            with open(filename, "w", newline='', encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["timestamp", "cmd", "resp"])
                for entry in log:
                    ts = entry.get("ts", "")
                    cmd = entry.get("cmd", "")
                    resp = entry.get("resp", "")
                    writer.writerow([ts, cmd, resp])
            return True
        except Exception as e:
            print(f"[ExportAPDU] Error: {e}")
            return False

    def import_apdu_log(self, filename):
        entries = []
        with open(filename, "r", newline='', encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                entries.append({
                    "ts": row.get("timestamp", ""),
                    "cmd": row.get("cmd", ""),
                    "resp": row.get("resp", "")
                })
        return entries

    def export_all_cards(self, cards, filename):
        try:
            arr = [json.loads(card.export_profile()) for card in cards]
            with open(filename, "w", encoding="utf-8") as f:
                json.dump(arr, f, indent=2)
            return True
        except Exception as e:
            print(f"[ExportAll] Error: {e}")
            return False

    def import_all_cards(self, filename, card_class):
        cards = []
        with open(filename, "r", encoding="utf-8") as f:
            arr = json.load(f)
        for obj in arr:
            card = card_class(None)
            card.import_profile_json(json.dumps(obj))
            cards.append(card)
        return cards
