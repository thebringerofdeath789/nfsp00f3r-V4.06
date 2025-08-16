# cardhopper_server.py
# Portions of this file incorporate code and logic from:
# - "Cardhopper" by Tiernan Messmer (Neo-Vortex) – https://github.com/nvx/cardhopper (GPL v3+)
# Licensed under GPL v3+
#
# TCP relay server bridging a Proxmark3 in 'hf cardhopper' with a remote client.

import socket
import threading
import logging
from cardhopper_protocol import CardhopperProtocol

logger = logging.getLogger(__name__)

class CardhopperRelayServer:
    def __init__(self, pm3_transport, host='0.0.0.0', port=9000):
        self.pm3 = CardhopperProtocol(pm3_transport)
        self.host = host
        self.port = port
        self.server = None
        self.client = None
        self.running = False

    def start(self):
        self.running = True
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind((self.host, self.port))
        self.server.listen(1)
        threading.Thread(target=self._accept_loop, daemon=True).start()
        threading.Thread(target=self._pm3_to_client, daemon=True).start()
        logger.info('cardhopper server listening on %s:%d', self.host, self.port)

    def _accept_loop(self):
        while self.running:
            c, addr = self.server.accept()
            self.client = c
            logger.info('cardhopper client %s connected', addr)
            threading.Thread(target=self._client_to_pm3, daemon=True).start()

    def _client_to_pm3(self):
        try:
            while self.running and self.client:
                lb = self.client.recv(1)
                if not lb:
                    break
                length = lb[0]
                if length == 0:
                    continue
                data = self.client.recv(length)
                if len(data) != length:
                    logger.warning('client short read')
                    continue
                self.pm3.send_frame(data)
        except Exception as e:
            logger.error('client_to_pm3 error: %s', e)
        finally:
            try:
                self.client.close()
            except Exception:
                pass
            self.client = None
            logger.info('cardhopper client disconnected')

    def _pm3_to_client(self):
        while self.running:
            if not self.client:
                continue
            try:
                frame = self.pm3.receive_frame(timeout=0.1)
                if frame:
                    pkt = bytes([len(frame)]) + frame
                    self.client.sendall(pkt)
            except Exception as e:
                logger.error('pm3_to_client error: %s', e)

    def stop(self):
        self.running = False
        try:
            if self.server:
                self.server.close()
        except Exception:
            pass
        try:
            if self.client:
                self.client.close()
        except Exception:
            pass
