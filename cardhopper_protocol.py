# cardhopper_protocol.py
# Portions of this file incorporate code and logic from:
# - "Cardhopper" by Tiernan Messmer (Neo-Vortex) – https://github.com/nvx/cardhopper (GPL v3+)
# Licensed under GPL v3+
#
# Implements Cardhopper packet framing/parsing for ISO14443-A frames.

import struct
import time
import logging

logger = logging.getLogger(__name__)

class CardhopperProtocol:
    def __init__(self, transport):
        # transport must provide .read(size) and .write(data)
        self.transport = transport

    def send_frame(self, frame_bytes):
        if not frame_bytes:
            return
        length = len(frame_bytes)
        packet = struct.pack('B', length) + frame_bytes
        logger.debug('cardhopper send %dB: %s', length, frame_bytes.hex())
        self.transport.write(packet)

    def receive_frame(self, timeout=1.0):
        start = time.time()
        while time.time() - start < timeout:
            lb = self.transport.read(1)
            if not lb:
                continue
            length = lb[0]
            if length == 0:
                continue
            data = self.transport.read(length)
            if len(data) != length:
                logger.warning('cardhopper short read: expected %d got %d', length, len(data))
                continue
            logger.debug('cardhopper recv %dB: %s', length, data.hex())
            return data
        return None

    def flush(self):
        try:
            while getattr(self.transport, 'in_waiting', 0):
                n = self.transport.in_waiting
                self.transport.read(n)
        except Exception:
            pass
