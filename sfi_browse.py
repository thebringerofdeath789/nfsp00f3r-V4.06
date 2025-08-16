# =====================================================================
# File: sfi_browse.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   SFI browser and brute-forcer: tries all combinations of SFI/record
#   to discover all accessible data objects on card, for forensics
#   and advanced troubleshooting.
#
# Classes:
#   - SFIBrowser
# =====================================================================

class SFIBrowser:
    """
    Tries all SFI/record combos, reads, and decodes all records present.
    """
    def __init__(self, card, logger=None):
        self.card = card
        self.logger = logger
        self.results = []

    def browse(self, sfi_range=range(1, 32), record_range=range(1, 17)):
        """
        Attempts to read every SFI/record in range.
        Stores results in self.results (list of dicts).
        """
        self.results.clear()
        for sfi in sfi_range:
            for record in record_range:
                p2 = (sfi << 3) | 4
                cmd = [0x00, 0xB2, record, p2, 0]
                try:
                    resp, sw = self.card.send_apdu(cmd)
                    if sw == 0x9000 and resp:
                        entry = {
                            "SFI": sfi,
                            "Record": record,
                            "Data": resp.hex().upper()
                        }
                        self.results.append(entry)
                        if self.logger:
                            self.logger.log(f"SFI {sfi}, Rec {record}: {resp.hex().upper()}")
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Error SFI {sfi}, Rec {record}: {e}", "ERROR")
        return self.results

    def get_results(self):
        return self.results
