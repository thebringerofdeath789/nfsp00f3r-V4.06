###############################################################
# File: emv_crypto.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   In-house EMV cryptography routines for ARQC, TC, AAC, and MAC.
#   Handles standard key derivation, session key management, and
#   cryptogram calculation for all supported schemes.
#
# Classes:
#   - EmvCrypto
###############################################################

import hashlib
from Crypto.Cipher import DES3


class EmvCrypto:
    """
    EMV cryptography helper: session key derivation and AC/MAC generation.
    Note: This is a simplified, self-contained implementation suitable for
    offline testing. Master keys must be 16 or 24 bytes for 3DES.
    """

    def __init__(self, master_key: bytes, kdf_mode: str = "EMV2000"):
        if len(master_key) not in (16, 24):
            raise ValueError("master_key must be 16 or 24 bytes for 3DES")
        self.master_key = master_key
        self.kdf_mode = kdf_mode

    def derive_icc_key(self, pan: str, atc: int) -> bytes:
        """
        Derive a 16-byte session key from PAN and ATC.
        This is a simplified derivation using hashing as a stand-in where
        full EMV key derivation inputs are unavailable.
        """
        pan12 = (pan or "").replace(" ", "").replace("-", "")[-12:]
        data = (pan12 + f"{atc:04X}").encode("ascii")
        if self.kdf_mode.upper() == "EMV2000":
            sk = hashlib.sha1(self.master_key + data).digest()[:16]
        else:
            sk = hashlib.sha256(self.master_key + data).digest()[:16]
        # Expand to 24-byte 3DES key by K1||K2||K1
        return sk + sk[:8]

    @staticmethod
    def _pad8(b: bytes) -> bytes:
        pad = 8 - (len(b) % 8)
        return b + bytes([pad] * pad)

    def generate_cryptogram(self, session_key: bytes, data: bytes, cryptogram_type: str = "ARQC") -> bytes:
        type_map = {"ARQC": b"\x80", "TC": b"\x40", "AAC": b"\x00"}
        t = type_map.get(cryptogram_type.upper())
        if t is None:
            raise ValueError("Invalid cryptogram type")
        payload = self._pad8((data or b"") + t)
        cipher = DES3.new(session_key, DES3.MODE_CBC, iv=b"\x00" * 8)
        return cipher.encrypt(payload)[-8:]

    def generate_arqc(self, pan: str, atc: int, data: bytes) -> bytes:
        sk = self.derive_icc_key(pan, atc)
        return self.generate_cryptogram(sk, data, "ARQC")

    def generate_tc(self, pan: str, atc: int, data: bytes) -> bytes:
        sk = self.derive_icc_key(pan, atc)
        return self.generate_cryptogram(sk, data, "TC")

    def generate_aac(self, pan: str, atc: int, data: bytes) -> bytes:
        sk = self.derive_icc_key(pan, atc)
        return self.generate_cryptogram(sk, data, "AAC")

    def gen_arqc(self, session_key: bytes, data: bytes) -> bytes:
        cipher = DES3.new(session_key, DES3.MODE_CBC, iv=b"\x00" * 8)
        return cipher.encrypt(self._pad8(data))[-8:]

    def gen_mac(self, session_key: bytes, data: bytes) -> bytes:
        cipher = DES3.new(session_key, DES3.MODE_CBC, iv=b"\x00" * 8)
        return cipher.encrypt(self._pad8(data))[-8:]

