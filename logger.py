# =====================================================================
# File: logger.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Unified logger with file and UI signal output. Threadsafe, supports
#   multiple sinks. Used by all managers and debug window.
#
# Classes:
#   - Logger
# =====================================================================

import threading
import time
from PyQt5.QtCore import QObject, pyqtSignal

class Logger(QObject):
    """
    Threadsafe logger: logs to file and emits to UI.
    """
    log_updated = pyqtSignal(str)

    def __init__(self, logfile=None):
        super().__init__()
        self.lock = threading.Lock()
        self.logfile = logfile
        self._buffer = []

    def log(self, msg, level="INFO"):
        """
        Log a message with a level (INFO, WARN, ERROR).
        Threadsafe, emits to UI and writes to log file (if set).
        """
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        entry = f"[{ts}] [{level}] {msg}"
        with self.lock:
            self._buffer.append(entry)
            if len(self._buffer) > 1000:
                self._buffer = self._buffer[-1000:]
            if self.logfile:
                try:
                    with open(self.logfile, "a", encoding="utf-8") as f:
                        f.write(entry + "\n")
                except Exception as e:
                    # If file write fails, print to stderr as fallback
                    import sys
                    print(f"[Logger] File log write error: {e}", file=sys.stderr)
        self.log_updated.emit(entry)

    def get_log(self):
        """
        Returns a copy of the log buffer (up to 1000 most recent entries).
        """
        with self.lock:
            return list(self._buffer)
    
    def clear(self):
        """
        Clears the log buffer and emits a cleared message.
        """
        with self.lock:
            self._buffer.clear()
        self.log_updated.emit("[CLEARED]")

    def set_logfile(self, logfile):
        """
        Sets a new log file to write to.
        """
        with self.lock:
            self.logfile = logfile

    def flush_to_file(self):
        """
        Flushes the buffer to the logfile (if set).
        """
        if self.logfile:
            with self.lock:
                try:
                    with open(self.logfile, "w", encoding="utf-8") as f:
                        for entry in self._buffer:
                            f.write(entry + "\n")
                except Exception as e:
                    import sys
                    print(f"[Logger] Error flushing log buffer: {e}", file=sys.stderr)
