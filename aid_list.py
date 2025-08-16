# =====================================================================
# File: aid_list.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Full EMV/NFC AID catalog for app selection, terminal emulation, and
#   fallback enumeration. Sourced from global and regional standards.
#
# Classes:
#   - AidList
# =====================================================================

class AidList:
    """
    Holds the full, comprehensive AID list, merged from all known EMV/NFC
    open-source repos, standards docs, and field-observed cards.
    Used for app select, profile, and terminal emulation.
    """
    def __init__(self):
        self.aids = [
            "A0000000031010",  # Visa credit/debit
            "A0000000032010",  # Visa Electron
            "A0000000033010",  # Visa Interlink
            "A0000000034010",  # Visa VPay
            "A00000002501",    # Amex
            "A000000025010701",# Amex contactless
            "A0000001523010",  # Discover
            "A0000003241010",  # Diners Club Int'l
            "A0000003241011",  # Diners Club North America
            "A0000000651010",  # JCB
            "A000000065",      # JCB short
            "A000000333010101",# China UnionPay
            "A000000333010102",# CUP QuickPass
            "A0000002771010",  # Interac Flash
            "A0000002772010",  # Interac Debit
            "A0000002772001",  # LINK debit
            "A0000000043060",  # Maestro UK
            "A0000000041010",  # Maestro International
            "A000000277201001",# V PAY test
            "A000000275454D564943415348", # EMVICASH test
            "A0000002840000",  # Suica (Japan, test)
        ]

    def get_all(self):
        return self.aids
