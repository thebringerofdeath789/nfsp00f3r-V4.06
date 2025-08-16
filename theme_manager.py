# =====================================================================
# File: theme_manager.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Toggles between light and dark themes using QPalette. Can be
#   triggered from the main UI or on startup from settings.
#
# Classes:
#   - ThemeManager
# =====================================================================

from PyQt5.QtWidgets import QApplication
from nfsp00f3r.theme import get_dark_palette, get_light_palette

class ThemeManager:
    def __init__(self):
        self.app = QApplication.instance()
        self.dark_mode = False

    def toggle_theme(self):
        if self.dark_mode:
            self._apply_light()
        else:
            self._apply_dark()
        self.dark_mode = not self.dark_mode

    def _apply_light(self):
        palette = get_light_palette()
        self.app.setPalette(palette)

    def _apply_dark(self):
        palette = get_dark_palette()
        self.app.setPalette(palette)
