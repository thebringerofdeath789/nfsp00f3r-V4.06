# =====================================================================
# File: bulk_ac.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   UI and logic to run a batch of random GENERATE AC transactions,
#   logging results to the main APDU log.
#
# Classes:
#   - BulkACRunner
# =====================================================================

from PyQt5.QtWidgets import QInputDialog, QLineEdit

class BulkACRunner:
    @staticmethod
    def prompt_bulk_count(parent):
        count, ok = QInputDialog.getInt(parent, "Bulk AC", "Number of cryptograms:", value=100, min=1, max=1000)
        return count, ok

    def run(self, card, count=100):
        """
        Run a batch of GENERATE AC commands with random UNs.
        Returns log list.
        """
        logs = []
        for i in range(count):
            # Generate random unpredictable number for each AC
            import os
            un = os.urandom(4)
            ac = card.generate_ac(un)
            logs.append(f"Bulk AC {i+1}: {ac.hex().upper()}")
        return logs
