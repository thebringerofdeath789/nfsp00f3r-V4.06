# =====================================================================
# File: pdol_cdol.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Date: 2025-08-15
# Description:
#   Utilities to parse PDOL (9F38), CDOL1 (8C), CDOL2 (8D) from TLV trees,
#   and to assemble datasets from a provided environment mapping.
# Credits:
#   Tag dictionary ideas inspired by openemv and RFIDIOt tag tables.
# =====================================================================

from typing import List, Tuple, Dict, Any
from tlv import TLVNode

# Minimal tag length lookup for common PDOL/CDOL elements (bytes)
TAG_LEN = {
    "9F66": 4,  # TTQ
    "9F02": 6,  # Amount, Authorised (Numeric)
    "9F03": 6,  # Amount, Other (Numeric)
    "9F1A": 2,  # Terminal Country Code
    "95":   5,  # TVR
    "5F2A": 2,  # Transaction Currency Code
    "9A":   3,  # Transaction Date (YYMMDD)
    "9C":   1,  # Transaction Type
    "9F37": 4,  # Unpredictable Number
    "9F21": 3,  # Transaction Time (HHMMSS)
    "9F4E": 0,  # Merchant Name and Location (var)
    "9F7C": 10, # Merchant Custom Data (example var length)
}

def _parse_dol_bytes(dol_bytes: bytes) -> List[Tuple[str, int]]:
    out: List[Tuple[str, int]] = []
    i = 0
    while i < len(dol_bytes):
        # parse tag (1-3 bytes)
        first = dol_bytes[i]
        tag = [first]
        i += 1
        if (first & 0x1F) == 0x1F:
            # subsequent bytes until continuation bit 0
            while i < len(dol_bytes):
                tag.append(dol_bytes[i])
                cont = dol_bytes[i] & 0x80
                i += 1
                if not cont:
                    break
        tag_hex = ''.join(f"{b:02X}" for b in tag)
        if i >= len(dol_bytes):
            break
        length = dol_bytes[i]
        i += 1
        out.append((tag_hex, length))
    return out

def extract_pdol_cdol(nodes: List[TLVNode]) -> Dict[str, Any]:
    """Search parsed TLV nodes for PDOL (9F38), CDOL1 (8C), CDOL2 (8D)."""
    def find_tag(tag: str) -> bytes:
        for n in nodes:
            # depth-first search
            stack = [n]
            while stack:
                cur = stack.pop()
                if cur.tag == tag:
                    return cur.value
                stack.extend(cur.children)
        return b""

    pdol = find_tag("9F38")
    cdol1 = find_tag("8C")
    cdol2 = find_tag("8D")
    return {
        "pdol_raw": pdol.hex().upper() if pdol else "",
        "pdol_list": _parse_dol_bytes(pdol) if pdol else [],
        "cdol1_raw": cdol1.hex().upper() if cdol1 else "",
        "cdol1_list": _parse_dol_bytes(cdol1) if cdol1 else [],
        "cdol2_raw": cdol2.hex().upper() if cdol2 else "",
        "cdol2_list": _parse_dol_bytes(cdol2) if cdol2 else [],
    }

def build_dataset(dol_list: List[Tuple[str, int]], env: Dict[str, bytes]) -> bytes:
    """Build a dataset for a DOL list from env mapping (tag->bytes). If a tag
    is missing in env, fill with zeroes of the expected length. This function is
    for lab/test usage only and does not attempt any card scheme specific logic."""
    out = bytearray()
    for tag, ln in dol_list:
        val = env.get(tag)
        if val is None:
            # fall back to length from TAG_LEN if available (ignore mismatch)
            if ln == 0 and tag in TAG_LEN:
                ln = TAG_LEN[tag]
            val = bytes([0] * ln)
        if len(val) != ln:
            # truncate or pad to length
            val = (val[:ln] if len(val) > ln else val + bytes([0] * (ln - len(val))))
        out.extend(val)
    return bytes(out)
