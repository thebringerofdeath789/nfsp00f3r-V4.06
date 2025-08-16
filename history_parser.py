# =====================================================================
# File: history_parser.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Converts APDU log entries into structured, human-readable transaction
#   events for the UI. Supports EMV transaction and magstripe flows.
#
# Classes/Functions:
#   - parse_history(apdu_log)
# =====================================================================

def parse_history(apdu_log):
    """
    Parse a list of APDU log entries to human-readable transaction steps.
    """
    result = []
    for direction, apdu_bytes in apdu_log:
        if direction == ">>":
            cmd = apdu_bytes.hex().upper()
            result.append(f"Sent: {cmd}")
        else:
            resp = apdu_bytes.hex().upper()
            result.append(f"Received: {resp}")
    return result
