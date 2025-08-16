# =====================================================================
# File: chameleon_manager.py
# Project: nfsp00f3r V4.05  EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Chameleon Mini EMV/NFC card emulator & logger using serial interface.
#   Supports APDU command replay, log sniffing, and EMV card profile injection.
#
# Dependencies:
#   - pyserial
# =====================================================================

import serial
import time
import threading
from emvcard import EMVCard
from emv_crypto import EmvCrypto

class ChameleonMiniManager:
    def __init__(self, port="/dev/ttyUSB0", baudrate=115200, logger=None):
        self.port = port
        self.baudrate = baudrate
        self.logger = logger
        self.serial_conn = None
        self.connect()

    def connect(self):
        try:
            self.serial_conn = serial.Serial(self.port, self.baudrate, timeout=1)
            time.sleep(2)  # Let the device reset
            self.send_command("VERSION")
            if self.logger:
                self.logger.log(f"[ChameleonMini] Connected to {self.port}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"[ChameleonMini] Connection error: {e}", "ERROR")
            raise

    def send_command(self, cmd):
        """
        Sends a command to the Chameleon Mini.
        """
        if not cmd.endswith('\n'):
            cmd += '\n'
        self.serial_conn.write(cmd.encode())
        return self.read_response()

    def read_response(self):
        """
        Reads response lines from the Chameleon.
        """
        response = []
        start = time.time()
        while time.time() - start < 2:
            line = self.serial_conn.readline().decode(errors='ignore').strip()
            if line:
                response.append(line)
                if self.logger:
                    self.logger.log(f"[ChameleonMini] {line}")
        return "\n".join(response)

    def load_profile(self, emv_card: EMVCard):
        """
        Writes static card emulation data to the Chameleons memory.
        """
        atr = emv_card.get_atr()
        track1, track2 = emv_card.get_magstripe_tracks()
        if self.logger:
            self.logger.log("[ChameleonMini] Writing EMV track profile...")
        self.send_command("CONFIG=1:MF0EMU")
        self.send_command(f"TRACK1={track1}")
        self.send_command(f"TRACK2={track2}")
        self.send_command("UIDAUTOCALC=1")
        self.send_command("UID=DEADBEEF")
        self.send_command("STORE")

    def start_emulation(self):
        """
        Begins card emulation mode.
        """
        self.send_command("START")
        if self.logger:
            self.logger.log("[ChameleonMini] Emulation started.")

    def stop_emulation(self):
        """
        Ends card emulation mode.
        """
        self.send_command("STOP")
        if self.logger:
            self.logger.log("[ChameleonMini] Emulation stopped.")

    def sniff_apdu(self, callback):
        """
        Continuously sniffs APDU traffic during emulation.
        """
        def _loop():
            self.send_command("LOGSTART")
            while True:
                line = self.serial_conn.readline().decode().strip()
                if line.startswith("APDU:"):
                    apdu = bytes.fromhex(line[5:].strip())
                    if callback:
                        callback(apdu)
        threading.Thread(target=_loop, daemon=True).start()

    def emulate_apdu(self, emv_card: EMVCard, emv_crypto: EmvCrypto):
        """
        Active APDU emulation mode.
        Responds to APDU commands using EMV logic.
        """
        def _loop():
            while True:
                line = self.serial_conn.readline().decode(errors='ignore').strip()
                if line.startswith("APDU:"):
                    apdu = bytes.fromhex(line[5:])
                    if self.logger:
                        self.logger.log(f"[ChameleonMini] APDU Received: {apdu.hex()}")
                    response = self.handle_apdu(apdu, emv_card, emv_crypto)
                    if response:
                        self.send_command(f"APDU={response.hex()}")

        threading.Thread(target=_loop, daemon=True).start()

    def handle_apdu(self, apdu, emv_card, emv_crypto):
        """
        Handles received APDU commands and returns proper response.
        """
        cla, ins, p1, p2 = apdu[:4]
        lc = apdu[4]
        data = apdu[5:5+lc]

        if ins == 0xA4:  # SELECT
            return emv_card.select_application(data)
        elif ins == 0xA8:  # GPO
            return emv_card.get_processing_options()
        elif ins == 0xB2:  # READ RECORD
            return emv_card.get_record(p1, p2)
        elif ins == 0xAE:  # GENERATE AC
            return emv_crypto.generate_ac("ARQC", data)
        else:
            return b'\x6D\x00'

    def disconnect(self):
        """
        Disconnect and clean up.
        """
        if self.serial_conn:
            self.serial_conn.close()
            if self.logger:
                self.logger.log("[ChameleonMini] Disconnected")


    def read_response(self):
        """
        Reads response lines from the Chameleon.
        """
        response = []
        start = time.time()
        while time.time() - start < 2:
            line = self.serial_conn.readline().decode(errors='ignore').strip()
            if line:
                response.append(line)
                if self.logger:
                    self.logger.log(f"[ChameleonMini] {line}")
                if line.endswith(">"):
                    break
        return "\n".join(response)
