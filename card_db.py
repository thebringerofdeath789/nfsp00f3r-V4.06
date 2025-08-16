# =====================================================================
# File: card_db.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-15
#
# Description:
#   JSON-backed storage for card reads, APDU Rx/Tx logs, and EMV fields.
#   Provides index by PAN, issuer, and timestamp. Supports mark-emulated flag.
# =====================================================================

import json, os, time
from pathlib import Path
from typing import Dict, Any, List

class CardDatabase:
    def __init__(self, root: str = "data"):
        self.root = Path(root)
        self.cards_dir = self.root / "cards"
        self.cards_dir.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self._write_index({"cards": []})

    def _read_index(self) -> Dict[str, Any]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8"))
        except Exception:
            return {"cards": []}

    def _write_index(self, idx: Dict[str, Any]):
        self.index_path.write_text(json.dumps(idx, indent=2), encoding="utf-8")

    def _timestamp(self) -> str:
        return time.strftime("%Y-%m-%dT%H:%M:%S", time.localtime())

    def add_card(self, card: Dict[str, Any]) -> str:
        # ensure id
        card_id = card.get("id") or f"card_{int(time.time()*1000)}"
        card["id"] = card_id
        card["ts"] = card.get("ts") or self._timestamp()
        # write card file
        Path(self.cards_dir / f"{card_id}.json").write_text(json.dumps(card, indent=2), encoding="utf-8")
        # update index
        idx = self._read_index()
        idx["cards"].append({
            "id": card_id,
            "ts": card["ts"],
            "pan": card.get("pan"),
            "issuer": card.get("issuer"),
            "emulated": bool(card.get("emulated", False))
        })
        self._write_index(idx)
        return card_id

    def list_cards(self, sort_by: str = "ts", reverse: bool = True) -> List[Dict[str, Any]]:
        idx = self._read_index()["cards"]
        return sorted(idx, key=lambda x: x.get(sort_by) or "", reverse=reverse)

    def get_card(self, card_id: str) -> Dict[str, Any]:
        p = self.cards_dir / f"{card_id}.json"
        if not p.exists():
            return {}
        return json.loads(p.read_text(encoding="utf-8"))

    def update_card(self, card_id: str, updates: Dict[str, Any]):
        card = self.get_card(card_id)
        if not card:
            return
        card.update(updates)
        Path(self.cards_dir / f"{card_id}.json").write_text(json.dumps(card, indent=2), encoding="utf-8")

    def mark_emulated(self, card_id: str, value: bool = True):
        self.update_card(card_id, {"emulated": value})
