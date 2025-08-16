# =====================================================================
# File: magstripe.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Magstripe track1/track2 parser, LRC generator, and replay/encode
#   utilities for hardware and virtual magstripe devices.
#
# Classes:
#   - MagstripeEmulator
# =====================================================================

import re

def bitflip_service_code(service_code):
    """
    Bitflips the leftmost digit of the service code, returns as a string.
    E.g., '2' (0b0010) -> '1' (0b0001), so '201' becomes '101'
    """
    if not service_code or not service_code[0].isdigit():
        return service_code
    # Bitwise flip the least significant bit (as in EMV fallback trick)
    flipped = str(int(service_code[0]) ^ 1)
    return flipped + service_code[1:]

class MagstripeEmulator:
    """
    Provides parsing, LRC, encoding, and track conversion for ISO7813 track1/track2 magstripe data.
    """

    def parse_track2(self, data):
        """
        Parse ISO 7813 Track 2: ;<PAN>=<EXP><SERVICE><DISCRETIONARY>?<LRC>
        Returns dict or None if parsing fails.
        """
        if data.endswith("?"):
            data = data[:-1]
        m = re.match(r";?(\d{12,19})=(\d{4})(\d{3})([\d ]*)", data)
        if not m:
            return None
        return {
            "PAN": m.group(1),
            "EXP": m.group(2),
            "SERVICE": m.group(3),
            "DISCRETIONARY": m.group(4)
        }

    def parse_track1(self, data):
        """
        Parse ISO 7813 Track 1: %B<PAN>^NAME^<EXP><SERVICE><DISCRETIONARY>?<LRC>
        Returns dict or None if parsing fails.
        """
        if data.endswith("?"):
            data = data[:-1]
        m = re.match(r"%B(\d{1,19})\^([^^]{2,26})\^(\d{4})(\d{3})([\d ]*)", data)
        if not m:
            return None
        return {
            "PAN": m.group(1),
            "NAME": m.group(2).strip(),
            "EXP": m.group(3),
            "SERVICE": m.group(4),
            "DISCRETIONARY": m.group(5)
        }

    def calc_lrc(self, track_data):
        """
        Calculates Longitudinal Redundancy Check for a magstripe track string.
        LRC is xor of all 7-bit characters (not including sentinels).
        """
        lrc = 0
        for c in track_data:
            lrc ^= ord(c) & 0x7F
        return chr(lrc | 0x20)

    def encode_track2(self, pan, exp, service, discretionary, bitflip_service=False):
        """
        Construct valid Track 2 string from fields, with LRC and sentinels.
        bitflip_service: If True, leftmost digit of service code is bit-flipped (EMV magstripe fallback).
        """
        if bitflip_service:
            service = bitflip_service_code(service)
        track = f";{pan}={exp}{service}{discretionary}"
        lrc = self.calc_lrc(track)
        return f"{track}?{lrc}"

    def encode_track1(self, pan, name, exp, service, discretionary, bitflip_service=False):
        """
        Construct valid Track 1 string from fields, with LRC and sentinels.
        bitflip_service: If True, leftmost digit of service code is bit-flipped (EMV magstripe fallback).
        """
        if bitflip_service:
            service = bitflip_service_code(service)
        name = (name or '').ljust(26)
        track = f"%B{pan}^{name}^{exp}{service}{discretionary}"
        lrc = self.calc_lrc(track)
        return f"{track}?{lrc}"

    def build_track1_from_track2(self, track2, card_info=None, bitflip_service=False):
        """
        Constructs a Track 1 string using data parsed from Track 2 and
        card_info (typically from EMVCard.info) for cardholder name.
        """
        parsed = self.parse_track2(track2)
        if not parsed:
            raise ValueError("Invalid Track 2 format")
        pan = parsed['PAN']
        exp = parsed['EXP']
        service = parsed['SERVICE']
        discretionary = parsed['DISCRETIONARY']
        name = ''
        if card_info:
            name = card_info.get('Name', '').strip()
        return self.encode_track1(pan, name, exp, service, discretionary, bitflip_service=bitflip_service)
