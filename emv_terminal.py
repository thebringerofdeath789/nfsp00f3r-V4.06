# =====================================================================
# File: emv_terminal.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Terminal profile configuration for emulated/virtual POS. Allows
#   terminal AID allowlisting, masking, and custom profile data.
#
# Classes:
#   - EmvTerminal
# =====================================================================

class EmvTerminal:
    def __init__(self):
        self.profile = {
            "terminal_country_code": "0840",
            "merchant_id": "000000000000000",
            "terminal_capabilities": "E0F0C8",
            "terminal_type": "22",
            "aids": []
        }

    def set_terminal_profile(self, profile):
        self.profile.update(profile)

    def get_terminal_profile(self):
        return self.profile

    def filter_aid(self, aid):
        aids = self.profile.get("aids", [])
        return aid in aids if aids else True

    def list_aids(self):
        return self.profile.get("aids", [])

    def pdol_profile(self):
        """Return a dict suitable for pdol_builder.build_env from terminal profile."""
        return {
            "terminal_country_code": self.profile.get("terminal_country_code", "0840"),
            "transaction_currency_code": self.profile.get("transaction_currency_code", self.profile.get("terminal_country_code", "0840")),
            "ttq": self.profile.get("ttq", "36000000"),
            "terminal_type": self.profile.get("terminal_type", "22"),
            "merchant_name": self.profile.get("merchant_name", ""),
        }
