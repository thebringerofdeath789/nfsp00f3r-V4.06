# =====================================================================
# Cardhopper integration added 2025-08-15
# Portions of this file incorporate code and logic from:
# - "Cardhopper" by Tiernan Messmer (Neo-Vortex) – https://github.com/nvx/cardhopper (GPL v3+)
# - "proxmark3" by RfidResearchGroup – https://github.com/RfidResearchGroup/proxmark3 (GPL v3)

import logging
from cardhopper_protocol import CardhopperProtocol
from cardhopper_server import CardhopperRelayServer

# =====================================================================
# File: proxmark3_manager.py
# Project: nfsp00f3r V4.05 – EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Proxmark3 EMV interaction manager:
#   - Handles EMV card reading and emulation via Proxmark3 hardware.
#   - APDU exchange, cryptogram handling, EMV standards compliance.
#
# Dependencies:
#   - pyserial (serial interface to Proxmark3)
# =====================================================================

import serial
import threading
import time
from emvcard import EMVCard
from emv_crypto import EMVCrypto

class Proxmark3Manager:
    def __init__(self, port='/dev/ttyACM0', baudrate=115200, logger=None):
        self.port = port
        self.baudrate = baudrate
        self.serial_conn = None
        self.logger = logger
        self.connect()

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            if self.logger:
                self.logger.log(f"[Proxmark3] Connected on {self.port}")
            self.initialize_proxmark()
        except Exception as e:
            if self.logger:
                self.logger.log(f"[Proxmark3] Connection error: {e}", "ERROR")
            raise

    def initialize_proxmark(self):
        """
        Sends Proxmark3 initialization commands to enable EMV mode.
        """
        self.send_cmd("hf 14a reader")
        self.send_cmd("hf 14a sim")

    def send_cmd(self, command, wait_response=True):
        """
        Sends a command to the Proxmark3 and optionally waits for a response.
        """
        cmd = f"{command}\n".encode()
        self.serial_conn.write(cmd)
        if self.logger:
            self.logger.log(f"[Proxmark3] Sent: {command}")
        if wait_response:
            return self.read_response()
        return None

    def read_response(self):
        """
        Reads lines from the Proxmark3 until a prompt or timeout.
        """
        response = ""
        start_time = time.time()
        while True:
            line = self.serial_conn.readline().decode().strip()
            if line:
                response += line + "\n"
                if self.logger:
                    self.logger.log(f"[Proxmark3] Received: {line}")
                if "proxmark3>" in line.lower():
                    break
            if time.time() - start_time > 5:
                if self.logger:
                    self.logger.log("[Proxmark3] Response timeout", "WARN")
                break
        return response

    def read_emv_card(self):
        """
        Reads EMV data from an inserted card via Proxmark3 hardware.
        Returns EMVCard object.
        """
        self.send_cmd("hf emv exec")
        response = self.read_response()
        emv_data = self.parse_emv_response(response)
        emv_card = EMVCard(logger=self.logger)
        emv_card.tlv_parser.parse(emv_data)
        emv_card.parse_tlv_records(emv_card.tlv_root)
        return emv_card

    def parse_emv_response(self, response):
        """
        Parses raw Proxmark3 EMV response to bytes.
        """
        hex_data = ""
        for line in response.splitlines():
            if ":" in line:
                parts = line.split(":")[1].strip().replace(" ", "")
                hex_data += parts
        return bytes.fromhex(hex_data)

    def emulate_emv_card(self, emv_card: EMVCard, emv_crypto: EMVCrypto):
        """
        Emulates an EMV card using Proxmark3 and provided EMVCard data.
        """
        def emulation_loop():
            self.send_cmd("hf 14a sim")
            while True:
                apdu_cmd = self.wait_for_apdu()
                if apdu_cmd:
                    response = self.process_apdu(apdu_cmd, emv_card, emv_crypto)
                    self.send_apdu_response(response)

        threading.Thread(target=emulation_loop, daemon=True).start()

    def wait_for_apdu(self):
        """
        Waits and parses APDU command from terminal.
        """
        response = self.read_response()
        if "apdu" in response.lower():
            hex_data = "".join(response.split(":")[1:]).strip().replace(" ", "")
            return bytes.fromhex(hex_data)
        return None

    def process_apdu(self, apdu_cmd, emv_card, emv_crypto):
        """
        Processes APDU command using EMVCard data and cryptographic module.
        Returns APDU response bytes.
        """
        if self.logger:
            self.logger.log(f"[Proxmark3] Processing APDU: {apdu_cmd.hex()}")
        # Process SELECT, GPO, READ RECORD, GENERATE AC explicitly
        cla, ins, p1, p2, lc = apdu_cmd[:5]
        data = apdu_cmd[5:]

        if ins == 0xA4:  # SELECT command
            return emv_card.select_application(data)
        elif ins == 0xA8:  # GET PROCESSING OPTIONS
            return emv_card.get_processing_options()
        elif ins == 0xB2:  # READ RECORD
            record = emv_card.get_record(p1, p2)
            return record if record else b"\x6A\x83"  # Record not found
        elif ins == 0xAE:  # GENERATE AC
            ac_response = emv_crypto.generate_ac("ARQC", data)
            return ac_response if ac_response else b"\x69\x85"  # Conditions not satisfied
        else:
            return b"\x6D\x00"  # Instruction code not supported

    def send_apdu_response(self, response):
        """
        Sends an APDU response back to the terminal via Proxmark3.
        """
        hex_resp = response.hex().upper()
        self.send_cmd(f"hf 14a apdu {hex_resp}")

    def disconnect(self):
        """
        Disconnects Proxmark3 serial connection gracefully.
        """
        if self.serial_conn:
            self.serial_conn.close()
            if self.logger:
                self.logger.log("[Proxmark3] Disconnected")


    # -------------------------
    # Cardhopper integration
    # -------------------------
    def run_cardhopper_mode(self):
        if self.logger:
            self.logger.log("[Proxmark3] Starting Cardhopper mode...")
        self.send_cmd("hf cardhopper", wait_response=False)
        time.sleep(0.5)
        self._cardhopper = CardhopperProtocol(self.serial_conn)
        self._cardhopper_enabled = True
        if self.logger:
            self.logger.log("[Proxmark3] Cardhopper mode active")

    def start_cardhopper_server(self, host='0.0.0.0', port=9000):
        if not getattr(self, "_cardhopper_enabled", False):
            self.run_cardhopper_mode()
        try:
            self._cardhopper_srv = CardhopperRelayServer(self.serial_conn, host, port)
            self._cardhopper_srv.start()
            if self.logger:
                self.logger.log(f"[Proxmark3] Cardhopper server on {host}:{port}")
            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"[Proxmark3] Cardhopper server error: {e}", "ERROR")
            return False

    def stop_cardhopper_server(self):
        srv = getattr(self, "_cardhopper_srv", None)
        if srv:
            srv.stop()
            self._cardhopper_srv = None
            if self.logger:
                self.logger.log("[Proxmark3] Cardhopper server stopped")

    def send_frame_via_cardhopper(self, frame_bytes):
        if not getattr(self, "_cardhopper_enabled", False):
            raise RuntimeError("Cardhopper mode not active")
        self._cardhopper.send_frame(frame_bytes)

    def read_frame_via_cardhopper(self, timeout=1.0):
        if not getattr(self, "_cardhopper_enabled", False):
            raise RuntimeError("Cardhopper mode not active")
        return self._cardhopper.receive_frame(timeout=timeout)
