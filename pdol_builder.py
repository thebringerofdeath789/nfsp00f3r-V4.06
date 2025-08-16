# =====================================================================
# File: pdol_builder.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Date: 2025-08-15
#
# Description:
#   Helpers to parse DOLs and build PDOL datasets and GPO APDUs from a
#   terminal/transaction environment. Produces a correct 0x83 TLV for GPO.
#
# Public API:
#   - parse_dol(dol_bytes: bytes) -> List[Tuple[str,int]]
#   - build_env(profile: dict, amount_cents: int = 0, tx_type: int = 0x00,
#               currency_code: str = None, country_code: str = None,
#               ttq: bytes = None, now: datetime = None,
#               unpredictable: bytes = None) -> Dict[str, bytes]
#   - build_pdol_value(dol_list, env) -> bytes
#   - build_gpo_field(dol_list, env) -> bytes  # returns 83 TLV only
#   - build_gpo_apdu(dol_list, env) -> bytes   # returns full APDU
# =====================================================================

from typing import List, Tuple, Dict, Optional
from datetime import datetime
import os


def _to_bcd(number: int, digits: int) -> bytes:
    """Pack a positive integer into BCD with given digits (left-padded)."""
    s = f"{number:0{digits}d}"
    out = bytearray()
    for i in range(0, len(s), 2):
        high = int(s[i], 10)
        low = int(s[i + 1], 10) if i + 1 < len(s) else 0
        out.append((high << 4) | low)
    return bytes(out)


def parse_dol(dol_bytes: bytes) -> List[Tuple[str, int]]:
    """Parse a Data Object List (PDOL/CDOL) into [(tag_hex, length), ...]."""
    lst: List[Tuple[str, int]] = []
    i = 0
    n = len(dol_bytes)
    while i < n:
        first = dol_bytes[i]
        tag_bytes = [first]
        i += 1
        if (first & 0x1F) == 0x1F:
            # subsequent tag bytes until bit8=0
            while i < n:
                b = dol_bytes[i]
                tag_bytes.append(b)
                i += 1
                if (b & 0x80) == 0:
                    break
        if i >= n:
            break
        length = dol_bytes[i]
        i += 1
        tag_hex = ''.join(f"{b:02X}" for b in tag_bytes)
        lst.append((tag_hex, length))
    return lst


def build_env(
    profile: Dict[str, str],
    amount_cents: int = 0,
    tx_type: int = 0x00,
    currency_code: Optional[str] = None,
    country_code: Optional[str] = None,
    ttq: Optional[bytes] = None,
    now: Optional[datetime] = None,
    unpredictable: Optional[bytes] = None,
) -> Dict[str, bytes]:
    """Construct a sensible default environment mapping tag->bytes.

    - amount_cents: integer of minor units (e.g., cents) for 9F02.
    - tx_type: EMV transaction type (9C), default 0x00 goods/services.
    - currency_code: numeric ISO 4217 in 4-hex-digit string, e.g., '0840'.
    - country_code: numeric ISO 3166-1 numeric in 4-hex-digit string, e.g., '0840'.
    - ttq: 4-byte TTQ if provided (9F66). If None, uses profile default or 36 00 00 00.
    - now: datetime to use for 9A and 9F21.
    - unpredictable: 4 bytes for 9F37; if None, uses os.urandom(4).
    """
    dt = now or datetime.utcnow()
    # Amount (9F02) & Amount Other (9F03)
    amt = max(0, int(amount_cents))
    amt_bcd = _to_bcd(amt, 12)  # 12 digits -> 6 bytes
    # Currency (5F2A) and Country (9F1A)
    cur = currency_code or profile.get("transaction_currency_code") or profile.get("terminal_country_code") or "0840"
    ctry = country_code or profile.get("terminal_country_code") or cur
    cur_bytes = bytes.fromhex(cur)
    ctry_bytes = bytes.fromhex(ctry)
    # TTQ (9F66)
    ttq_bytes = ttq or bytes.fromhex(profile.get("ttq", "36000000"))
    # Terminal Type (9F35)
    ttype = bytes.fromhex(profile.get("terminal_type", "22"))
    # TVR (95) default zeros
    tvr = b"\x00\x00\x00\x00\x00"
    # Date (9A) YYMMDD and Time (9F21) HHMMSS in BCD
    date_bcd = _to_bcd(int(dt.strftime("%y%m%d")), 6)
    time_bcd = _to_bcd(int(dt.strftime("%H%M%S")), 6)[:3]
    # Transaction Type (9C)
    tx_type_b = bytes([tx_type & 0xFF])
    # UN (9F37)
    un = unpredictable or os.urandom(4)

    env: Dict[str, bytes] = {
        "9F66": ttq_bytes,
        "9F02": amt_bcd,
        "9F03": b"\x00\x00\x00\x00\x00\x00",
        "9F1A": ctry_bytes,
        "95": tvr,
        "5F2A": cur_bytes,
        "9A": date_bcd,
        "9C": tx_type_b,
        "9F37": un,
        "9F21": time_bcd,
        "9F35": ttype,
        # Add more common PDOL/CDOL tags
        "9F33": bytes.fromhex(profile.get("terminal_capabilities", "E0F0C8")),  # Terminal Capabilities
        "9F40": bytes.fromhex(profile.get("additional_terminal_capabilities", "6000F0A001")),  # Additional Terminal Capabilities
        "9F45": b"\x00\x00",  # Data Authentication Code
        "9F34": b"\x3F\x00\x00",  # CVM Results
        "9F4C": b"\x00" * 8,  # ICC Dynamic Data
        "9F7C": b"\x00" * 14,  # Customer Exclusive Data
    }

    # Optional merchant name/location (9F4E) if present in profile
    mname = profile.get("merchant_name")
    if mname:
        try:
            env["9F4E"] = mname.encode("ascii", errors="ignore")
        except Exception:
            pass

    return env


def build_pdol_value(dol_list: List[Tuple[str, int]], env: Dict[str, bytes]) -> bytes:
    """Concatenate PDOL values according to dol_list using env; pad/truncate as needed."""
    out = bytearray()
    for tag, ln in dol_list:
        v = env.get(tag, b"\x00" * ln)
        if len(v) != ln:
            if len(v) > ln:
                v = v[:ln]
            else:
                v = v + (b"\x00" * (ln - len(v)))
        out.extend(v)
    return bytes(out)


def build_gpo_field(dol_list: List[Tuple[str, int]], env: Dict[str, bytes]) -> bytes:
    """Return only the 83 TLV for the PDOL values (to be placed in APDU data field)."""
    val = build_pdol_value(dol_list, env)
    return b"\x83" + bytes([len(val)]) + val


def build_gpo_apdu(dol_list: List[Tuple[str, int]], env: Dict[str, bytes]) -> bytes:
    """Return full GET PROCESSING OPTIONS APDU for given PDOL list and env."""
    field = build_gpo_field(dol_list, env)
    return b"\x80\xA8\x00\x00" + bytes([len(field)]) + field
