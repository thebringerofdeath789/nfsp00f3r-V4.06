# =====================================================================
# File: hce_manager.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   HCEManager handles BLE provisioning for the Android companion app.
#   Uses ECDH and AES-GCM for secure transfer of card payloads.
#
# Classes:
#   - HCEManager
# =====================================================================

import os
import json
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.ciphers.aead import AESGCM

class HCEManager:
    def __init__(self):
        self._ecdh_private = ec.generate_private_key(ec.SECP256R1())
        self._peer_pubkey = None
        self._session_key = None

    def get_public_key_bytes(self):
        pubkey = self._ecdh_private.public_key()
        return pubkey.public_bytes(
            serialization.Encoding.X962,
            serialization.PublicFormat.UncompressedPoint
        )

    def receive_peer_pubkey(self, peer_bytes):
        self._peer_pubkey = ec.EllipticCurvePublicKey.from_encoded_point(
            ec.SECP256R1(), peer_bytes
        )
        self._session_key = self._ecdh_private.exchange(ec.ECDH(), self._peer_pubkey)
        # Derive session key for AESGCM
        self._session_key = HKDF(
            algorithm=hashes.SHA256(),
            length=32,
            salt=None,
            info=b"nfsp00f3r-hce-session"
        ).derive(self._session_key)

    def encrypt_payload(self, payload: dict):
        if self._session_key is None:
            raise ValueError("Session not established")
        aesgcm = AESGCM(self._session_key)
        nonce = os.urandom(12)
        ct = aesgcm.encrypt(nonce, json.dumps(payload).encode("utf-8"), None)
        return nonce + ct

    def decrypt_payload(self, ciphertext: bytes):
        if self._session_key is None:
            raise ValueError("Session not established")
        nonce = ciphertext[:12]
        ct = ciphertext[12:]
        aesgcm = AESGCM(self._session_key)
        data = aesgcm.decrypt(nonce, ct, None)
        return json.loads(data.decode("utf-8"))
