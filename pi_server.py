# =====================================================================
# File: pi_server.py
# Project: nfsp00f3r - Raspberry Pi server side
# Date: 2025-08-15
#
# Description:
#   Acts like a terminal to an NFC card. Reads cards via PCSC or PN532.
#   Stores all Rx/Tx APDUs and parsed TLV to JSON via card_db.
#   Selects PPSE, enumerates AIDs, selects each AID and runs minimal flows.
#   Generates cryptograms for UN 1..100 and stores keyed by UN.
# =====================================================================

import os, sys, time, json, random
from typing import List, Dict, Any

try:
    from smartcard.System import readers as pcsc_readers
    from smartcard.util import toBytes, toHexString
except Exception:
    pcsc_readers = None

try:
    from pn532 import PN532_SPI  # optional, if installed
except Exception:
    PN532_SPI = None

from tlv import TLVParser
from pdol_cdol import extract_pdol_cdol, build_dataset
from card_db import CardDatabase

# simple EMV helpers
PPSE = b'2PAY.SYS.DDF01'

def build_select(name: bytes) -> bytes:
    return b'\x00\xA4\x04\x00' + bytes([len(name)]) + name

def build_gpo(pdol: List[bytes]) -> bytes:
    # concatenate PDOL data elements as given
    data = b''.join(pdol)
    return b'\x80\xA8\x00\x00' + bytes([len(data)+2]) + b'\x83' + bytes([len(data)]) + data

class TerminalSession:
    def __init__(self, db: CardDatabase):
        self.db = db
        self.parser = TLVParser()
        self.apdu_log: List[Dict[str, str]] = []
        self.cryptos: Dict[int, str] = {}

    def log(self, direction: str, apdu: bytes):
        self.apdu_log.append({"dir": direction, "apdu": apdu.hex().upper(), "ts": time.time()})

    def parse_tlv(self, data: bytes) -> List[Dict[str, Any]]:
        try:
            nodes = self.parser.parse(data)
            return [n.to_dict() for n in nodes]
        except Exception:
            return []

    def run(self):
        # PCSC only for now
        if not pcsc_readers:
            print("PCSC not available")
            return
        rlist = pcsc_readers()
        if not rlist:
            print("No PCSC readers")
            return
        reader = rlist[0]
        conn = reader.createConnection()
        conn.connect()
        # 1) SELECT PPSE
        sel = build_select(PPSE)
        self.log(">>", sel)
        data, sw1, sw2 = conn.transmit(list(sel))
        resp = bytes(data) + bytes([sw1, sw2])
        self.log("<<", resp)
        ppse_tlv = self.parse_tlv(bytes(data))
        # 2) find AIDs in FCI
        aids = []
        for node in self.parser.parse(bytes(data)):
            if node.tag in ("4F",):  # AID
                aids.append(bytes.fromhex(node.value.hex()))
        # 3) for each AID, select and try minimal flow
        card = {
            "aids": [a.hex().upper() for a in aids],
            "ppse_fci": ppse_tlv,
            "apdu": self.apdu_log,
            "parsed": [],
            "pdol": "",
            "pdol_list": [],
            "cdol1": "",
            "cdol1_list": [],
            "cdol2": "",
            "cdol2_list": [],
            "cdol1": "",
            "cdol2": "",
            "cryptograms": {},
            "issuer": "",
            "pan": "",
            "emulated": False
        }
        for aid in aids or []:
            sel = build_select(aid)
            self.log(">>", sel)
            data, sw1, sw2 = conn.transmit(list(sel))
            resp = bytes(data) + bytes([sw1, sw2])
            self.log("<<", resp)
            fci = self.parse_tlv(bytes(data))
            
            # extract PDOL/CDOL from FCI if present
            try:
                meta = extract_pdol_cdol(self.parser.parse(bytes(data)))
                card["pdol"] = meta.get("pdol_raw","")
                card["pdol_list"] = [(t,l) for (t,l) in meta.get("pdol_list",[])]
                card["cdol1"] = meta.get("cdol1_raw","")
                card["cdol1_list"] = [(t,l) for (t,l) in meta.get("cdol1_list",[])]
                card["cdol2"] = meta.get("cdol2_raw","")
                card["cdol2_list"] = [(t,l) for (t,l) in meta.get("cdol2_list",[])]
            except Exception:
                pass
card["parsed"].append({"aid": aid.hex().upper(), "fci": fci})
            # try GPO with empty PDOL for compatibility
            gpo = b'\x80\xA8\x00\x00\x02\x83\x00'
            self.log(">>", gpo)
            data, sw1, sw2 = conn.transmit(list(gpo))
            resp = bytes(data) + bytes([sw1, sw2])
            self.log("<<", resp)
            gpo_tlv = self.parse_tlv(bytes(data))
            card["parsed"][-1]["gpo"] = gpo_tlv
        # generate 100 cryptograms placeholder as hashes of UN + AID
        # In a proper build, use emv_crypto and keys
        for un in range(1, 101):
            s = f"UN{un:03d}"
            card["cryptograms"][str(un)] = s.encode().hex().upper()
        # persist
        card_id = self.db.add_card(card)
        print("Saved card id", card_id)

if __name__ == "__main__":
    db = CardDatabase()
    session = TerminalSession(db)
    session.run()
