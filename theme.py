# =====================================================================
# File: theme.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Theme definitions for Qt Designer forms and the ThemeManager.
#   (Used for form design previews and as a palette base.)
#
# Variables:
#   - DARK_PALETTE (QPalette)
#   - LIGHT_PALETTE (QPalette)
# =====================================================================

from PyQt5.QtGui import QPalette, QColor

def get_dark_palette():
    palette = QPalette()
    palette.setColor(QPalette.Window, QColor(45, 45, 45))
    palette.setColor(QPalette.WindowText, QColor(230, 230, 230))
    palette.setColor(QPalette.Base, QColor(30, 30, 30))
    palette.setColor(QPalette.AlternateBase, QColor(45, 45, 45))
    palette.setColor(QPalette.ToolTipBase, QColor(230, 230, 230))
    palette.setColor(QPalette.ToolTipText, QColor(230, 230, 230))
    palette.setColor(QPalette.Text, QColor(230, 230, 230))
    palette.setColor(QPalette.Button, QColor(45, 45, 45))
    palette.setColor(QPalette.ButtonText, QColor(230, 230, 230))
    palette.setColor(QPalette.Highlight, QColor(80, 80, 80))
    palette.setColor(QPalette.HighlightedText, QColor(230, 230, 230))
    return palette

def get_light_palette():
    return QPalette()
