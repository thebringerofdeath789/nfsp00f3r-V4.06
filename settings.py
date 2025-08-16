# =====================================================================
# File: main.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Main entry point for the nfsp00f3r application. Initializes
#   persistent settings, logger, device and card managers, and launches
#   the main window with full UI, theme, and BLE-based companion support.
#
# Classes/Functions:
#   - main()
# =====================================================================

import sys
from PyQt5.QtWidgets import QApplication
from nfsp00f3r.settings import SettingsManager
from nfsp00f3r.logger import Logger
from nfsp00f3r.device_manager import DeviceManager
from nfsp00f3r.cardmanager import CardManager
from nfsp00f3r.mainwindow import MainWindow

def main():
    # Persistent settings for user preferences
    settings = SettingsManager()

    # Initialize logger (log to file and optionally to UI)
    logger = Logger(settings.get("logfile", "nfsp00f3r.log"))

    # Initialize device manager for PCSC, PN532, BLE, Magstripe
    devices = DeviceManager(logger=logger, settings=settings)

    # CardManager for card insert/remove, switching, APDU routing
    cards = CardManager(logger=logger, devices=devices)

    # Start the Qt application
    app = QApplication(sys.argv)
    # MainWindow wires UI, theme, dialogs, debug, all manager classes
    window = MainWindow(settings=settings, logger=logger, devices=devices, cards=cards)
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
