# =====================================================================
# File: ui_debugwindow.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Debug window for color-coded APDU/log output and search.
#
# Classes:
#   - DebugWindow(QDialog)
# =====================================================================

from PyQt5.QtWidgets import QDialog, QTextEdit, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QColor, QTextCharFormat, QTextCursor

class DebugWindow(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Debug Console")
        self.resize(900, 480)
        layout = QVBoxLayout(self)
        self.txt = QTextEdit(self)
        self.txt.setReadOnly(True)
        self.txt.setStyleSheet("background-color: black; color: lightgray;")
        self.search = QLineEdit(self)
        self.search.setPlaceholderText("Search...")
        layout.addWidget(self.search)
        layout.addWidget(self.txt)
        self.search.textChanged.connect(self._do_search)

    def log_apdu(self, msg, color):
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        cursor = self.txt.textCursor()
        cursor.movePosition(QTextCursor.End)
        cursor.insertText(msg + "\n", fmt)
        self.txt.setTextCursor(cursor)
        self.txt.ensureCursorVisible()

    def log_outbound(self, msg):
        self.log_apdu(msg, "red")

    def log_inbound(self, msg):
        self.log_apdu(msg, "green")

    def log_info(self, msg):
        self.log_apdu(msg, "lightgray")

    def _do_search(self, text):
        cursor = self.txt.document().find(text)
        if not cursor.isNull():
            self.txt.setTextCursor(cursor)
