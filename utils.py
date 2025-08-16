# =====================================================================
# File: utils.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   General utilities for pathing, hex conversion, and OS detection.
#
# Functions:
#   - resource_path
#   - hexify
#   - dehexify
#   - app_version
#   - safe_open
#   - is_windows, is_linux, is_mac
#   - random_bytes, random_string, try_int
# =====================================================================

import os
import sys
import random
import string

def resource_path(relative_path):
    """
    Returns the absolute path to a resource, compatible with PyInstaller.
    """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(os.path.dirname(__file__))
    return os.path.join(base_path, relative_path)

def hexify(data, sep=" "):
    """
    Converts data (bytes or str) to hex representation.
    """
    if isinstance(data, (bytes, bytearray)):
        return sep.join(f"{b:02X}" for b in data)
    if isinstance(data, str):
        return sep.join(f"{ord(c):02X}" for c in data)
    retu
