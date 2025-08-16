# =====================================================================
# File: pdol.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   PDOL/CDOL builder and parser for EMV transactions. Supports mapping
#   between tag/length fields and robust fallback/zeroing.
#
# Classes/Functions:
#   - parse_pdol(pdol_bytes)
#   - build_pdol(pdol_fields, values_dict=None)
# =====================================================================

from nfsp00f3r.tag_dict import get_tag_info

def parse_pdol(pdol_bytes):
    """
    Parses PDOL bytes to a list of (tag, length) tuples.
    """
    pdol = []
    i = 0
    while i < len(pdol_bytes):
        tag = pdol_bytes[i]
        i += 1
        # Check if tag is multibyte
        if (tag & 0x1F) == 0x1F:
            tag = (tag << 8) | pdol_bytes[i]
            i += 1
        length = pdol_bytes[i]
        i += 1
        pdol.append((f"{tag:02X}", length))
    return pdol

def build_pdol(pdol_fields, values_dict=None):
    """
    Build the PDOL data from a list of (tag, length) tuples and an
    optional dict of values (hex or bytes).
    Zero-fills any missing.
    Returns: list of int (PDOL data)
    """
    if values_dict is None:
        values_dict = {}
    data = []
    for tag, length in pdol_fields:
        value = values_dict.get(tag)
        if value:
            if isinstance(value, str):
                value = bytes.fromhex(value)
            elif isinstance(value, int):
                value = value.to_bytes(length, "big")
            if len(value) < length:
                value += b"\x00" * (length - len(value))
            data.extend(value[:length])
        else:
            data.extend([0x00] * length)
    return data
