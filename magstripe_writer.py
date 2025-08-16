# =====================================================================
# File: magstripe_writer.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Writes Track 1, 2, or 3 data to MSRx86BT or compatible magstripe encoder device.
#   Supports bit-flip (service code only, for EMV fallback) and encoding using MagstripeEmulator.
#
# Classes:
#   - MagstripeWriter
# =====================================================================

import serial
from serial.tools import list_ports
from magstripe import MagstripeEmulator

class MagstripeWriter:
    """
    Writes magstripe Track 1, 2, and 3 data to compatible encoder devices.
    Uses MagstripeEmulator for robust track encoding and service code bit-flip.
    """
    def __init__(self, logger=None):
        self.logger = logger
        self.device = None
        self.baudrate = 9600
        self.devices = []
        self.mag = MagstripeEmulator()

    def enumerate_devices(self):
        """
        Enumerates available serial ports for magstripe writers.
        """
        self.devices = []
        for port in list_ports.comports():
            self.devices.append(port.device)
        return self.devices

    def list_devices(self):
        return self.devices

    def get_device(self, index=0):
        if self.devices and index < len(self.devices):
            return self.devices[index]
        return None

    def write(self, track1=None, track2=None, track3=None, device=None, baudrate=None,
              bitflip_service=False, card_info=None):
        """
        Writes one or more tracks to the magstripe writer.
        - track1, track2, track3: string (raw track or input fields; see helpers)
        - bitflip_service: if True, bitflip the service code digit for Track 1/2
        - card_info: dict, to provide cardholder name if building Track 1 from Track 2
        Returns True on success, False on failure.
        """
        if device is None:
            device = self.get_device(0)
        if baudrate is None:
            baudrate = self.baudrate
        if not device:
            if self.logger:
                self.logger.log("[MSR] No magstripe device found", "ERROR")
            return False
        try:
            with serial.Serial(device, baudrate, timeout=1) as ser:
                written = False
                if track1:
                    # If track1 looks like a raw track, use as-is. Else, try to build from track2 and info.
                    if not track1.startswith('%B'):
                        if track2:
                            track1 = self.mag.build_track1_from_track2(track2, card_info, bitflip_service=bitflip_service)
                        else:
                            raise ValueError("No valid Track 1 or Track 2 provided for Track 1 write.")
                    ser.write(track1.encode("ascii"))
                    written = True
                    if self.logger:
                        self.logger.log(f"[MSR] Wrote Track1 to {device} (bitflip_service={bitflip_service})")
                if track2:
                    # If not raw, encode using MagstripeEmulator and bitflip_service
                    if not track2.startswith(';'):
                        raise ValueError("Track 2 must be a raw ISO string (start with ';')")
                    # Optionally re-encode if needed:
                    parsed = self.mag.parse_track2(track2)
                    if parsed:
                        track2_enc = self.mag.encode_track2(parsed["PAN"], parsed["EXP"], parsed["SERVICE"], parsed["DISCRETIONARY"], bitflip_service=bitflip_service)
                    else:
                        track2_enc = track2
                    ser.write(track2_enc.encode("ascii"))
                    written = True
                    if self.logger:
                        self.logger.log(f"[MSR] Wrote Track2 to {device} (bitflip_service={bitflip_service})")
                if track3:
                    if not track3.startswith(';'):
                        raise ValueError("Track 3 must be a raw ISO string (start with ';')")
                    ser.write(track3.encode("ascii"))
                    written = True
                    if self.logger:
                        self.logger.log(f"[MSR] Wrote Track3 to {device}")
            return written
        except Exception as e:
            if self.logger:
                self.logger.log(f"[MSR] Write error: {e}", "ERROR")
            return False

    def write_track1(self, track1=None, device=None, baudrate=None, bitflip_service=False, card_info=None, track2=None):
        """
        Writes only Track 1. If no raw track1 provided, builds from track2 and card_info.
        """
        return self.write(track1=track1, track2=track2, device=device, baudrate=baudrate,
                          bitflip_service=bitflip_service, card_info=card_info)

    def write_track2(self, track2, device=None, baudrate=None, bitflip_service=False):
        """
        Writes only Track 2. Expects a raw ISO Track 2 string.
        """
        return self.write(track2=track2, device=device, baudrate=baudrate, bitflip_service=bitflip_service)

    def write_track3(self, track3, device=None, baudrate=None):
        """
        Writes only Track 3. Expects a raw ISO Track 3 string.
        """
        return self.write(track3=track3, device=device, baudrate=baudrate)
