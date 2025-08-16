# =====================================================================
# File: main.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-01-10
#
# Description:
#   Main entry point for the nfsp00f3r application. Launches the
#   Advanced Card Manager UI for real card data processing.
#   NO SAMPLE/TEST CARDS - REAL CARDS ONLY.
#
# Classes/Functions:
#   - main()
# =====================================================================

import sys
from PyQt5.QtWidgets import QApplication
from advanced_card_manager_ui import AdvancedCardManagerUI

def main():
    """Initialize application and start the Advanced Card Manager UI"""
    app = QApplication(sys.argv)
    app.setApplicationName("NFCSpoofer Advanced Card Manager")
    app.setApplicationVersion("4.05")
    
    # Create and show the Advanced Card Manager UI
    window = AdvancedCardManagerUI()
    window.show()
    
    # Start the application event loop
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
