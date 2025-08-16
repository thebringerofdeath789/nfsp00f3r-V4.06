# =====================================================================
# File: relay.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Bidirectional APDU relay and statistics tracker for live device
#   to companion phone relaying. Handles stats, errors, save/load.
#
# Classes:
#   - RelayManager
# =====================================================================

import time

class RelayManager:
    """
    Handles bidirectional APDU relay between card reader and BLE phone.
    Maintains relay stats and logs.
    """
    def __init__(self, card_manager, ble_manager, logger=None):
        self.card_manager = card_manager
        self.ble_manager = ble_manager
        self.logger = logger
        self.stats = {"sent": 0, "received": 0, "errors": 0, "start": None}
        self.log = []

    def start(self):
        """
        Resets statistics and log for a new relay session.
        """
        self.stats["start"] = time.time()
        self.stats["sent"] = 0
        self.stats["received"] = 0
        self.stats["errors"] = 0
        self.log.clear()

    def relay_apdu(self, apdu_bytes):
        """
        Relay an APDU to BLE companion and wait for response.
        """
        try:
            self.stats["sent"] += 1
            resp = self.ble_manager.relay_apdu(apdu_bytes)
            self.stats["received"] += 1
            self.log.append((apdu_bytes, resp))
            return resp
        except Exception as e:
            self.stats["errors"] += 1
            if self.logger:
                self.logger.log(f"Relay error: {e}", "ERROR")
            return None

    def get_stats(self):
        """
        Returns stats, including elapsed time in seconds since start.
        """
        elapsed = time.time() - (self.stats["start"] or time.time())
        return {
            **self.stats,
            "elapsed_sec": elapsed
        }

    def save_log(self, filename):
        """
        Saves the APDU relay log (as hex) to the specified file.
        """
        try:
            with open(filename, "w", encoding="utf-8") as f:
                for apdu, resp in self.log:
                    f.write(f"{apdu.hex()} {resp.hex()}\n")
            if self.logger:
                self.logger.log(f"[RelayManager] Saved relay log to {filename}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"[RelayManager] Error saving log: {e}", "ERROR")
            return False

    def load_log(self, filename):
        """
        Loads the APDU relay log from the specified file.
        """
        try:
            self.log.clear()
            with open(filename, "r", encoding="utf-8") as f:
                for line in f:
                    parts = line.strip().split(" ")
                    if len(parts) == 2:
                        apdu = bytes.fromhex(parts[0])
                        resp = bytes.fromhex(parts[1])
                        self.log.append((apdu, resp))
            if self.logger:
                self.logger.log(f"[RelayManager] Loaded relay log from {filename}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"[RelayManager] Error loading log: {e}", "ERROR")
            return False


# --- Cardhopper relay integration (requires proxmark_manager and cardhopper_protocol) ---
from proxmark_manager import Proxmark3Manager

class CardhopperRelay:
    def __init__(self, logger, pm_port='/dev/ttyACM0', server_host=None, server_port=9000):
        self.logger = logger
        self.pm = Proxmark3Manager(port=pm_port, logger=logger)
        self.server_host = server_host
        self.server_port = server_port
        if server_host:
            self.pm.start_cardhopper_server(server_host, server_port)
        else:
            self.pm.run_cardhopper_mode()

    def forward_apdu(self, apdu_bytes, timeout=1.0):
        # send APDU as raw frame and wait for response
        self.pm.send_frame_via_cardhopper(apdu_bytes)
        resp = self.pm.read_frame_via_cardhopper(timeout=timeout)
        return resp or b""
