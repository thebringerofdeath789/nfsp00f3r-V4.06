# =====================================================================
# File: ui_mainwindow.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   MainWindow UI layout and widget setup (designer code or direct).
#   Contains panels for Card Info, TLV tree, APDU log, and all buttons.
#
# Classes:
#   - Ui_MainWindow(object)
# =====================================================================

import importlib
try:
    QtWidgets = importlib.import_module('PyQt5.QtWidgets')
    QtCore = importlib.import_module('PyQt5.QtCore')
    QWidget = QtWidgets.QWidget  # type: ignore
    QVBoxLayout = QtWidgets.QVBoxLayout  # type: ignore
    QHBoxLayout = QtWidgets.QHBoxLayout  # type: ignore
    QLabel = QtWidgets.QLabel  # type: ignore
    QTreeWidget = QtWidgets.QTreeWidget  # type: ignore
    QTextEdit = QtWidgets.QTextEdit  # type: ignore
    QPushButton = QtWidgets.QPushButton  # type: ignore
    QComboBox = QtWidgets.QComboBox  # type: ignore
    QGridLayout = QtWidgets.QGridLayout  # type: ignore
    QFrame = QtWidgets.QFrame  # type: ignore
    Qt = QtCore.Qt  # type: ignore
except Exception:
    class _D: pass  # type: ignore
    QWidget = QVBoxLayout = QHBoxLayout = QLabel = _D  # type: ignore
    QTreeWidget = QTextEdit = QPushButton = QComboBox = _D  # type: ignore
    QGridLayout = QFrame = _D  # type: ignore
    class Qt: pass  # type: ignore


class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        MainWindow.setWindowTitle("nfsp00f3r V4.05")
        MainWindow.resize(1200, 800)
        self.central_widget = QWidget(MainWindow)
        MainWindow.setCentralWidget(self.central_widget)

        # Main layout
        self.main_layout = QVBoxLayout(self.central_widget)

        # Button row 1
        self.button_row1 = QHBoxLayout()
        self.btnReadCard = QPushButton("Read Card")
        self.btnExportCard = QPushButton("Export Card")
        self.btnImportCard = QPushButton("Import Card")
        self.btnTransaction = QPushButton("Transaction")
        self.btnReplayCard = QPushButton("Replay Card")
        self.btnRelayCard = QPushButton("Relay Card")
        # Reader device selection (for read card)
        self.cmbDevice = QComboBox()
        for btn in [self.btnReadCard, self.btnExportCard, self.btnImportCard,
                    self.btnTransaction, self.btnReplayCard, self.btnRelayCard]:
            self.button_row1.addWidget(btn)
        self.button_row1.addWidget(self.cmbDevice)
        self.main_layout.addLayout(self.button_row1)

        # Button row 2
        self.button_row2 = QHBoxLayout()
        self.btnSyncToPhone = QPushButton("Sync To Phone")
        self.btnOfflinePINTest = QPushButton("Offline PIN Test")
        self.btnThemeToggle = QPushButton("Theme Toggle")
        self.btnDebugConsole = QPushButton("Debug Console")
        self.btnMSRWrite = QPushButton("MSR Write")
        self.btnMagspoofDowngrade = QPushButton("Magspoof Downgrade")
        self.btnBulkAC = QPushButton("Bulk AC")
        self.btnCredits = QPushButton("Credits")
        self.btnKeyMgmt = QPushButton("🔐 Key Derivation")
        self.btnPdolSettings = QPushButton("PDOL Settings")
        self.cmbMSRDevice = QComboBox()
        for btn in [self.btnSyncToPhone, self.btnOfflinePINTest,
                    self.btnThemeToggle, self.btnDebugConsole,
                    self.btnMSRWrite, self.btnMagspoofDowngrade, self.btnBulkAC, self.btnCredits,
                    self.btnKeyMgmt, self.btnPdolSettings]:
            self.button_row2.addWidget(btn)
        self.button_row2.addWidget(self.cmbMSRDevice)
        self.main_layout.addLayout(self.button_row2)

        # Card Info Panel (labels)
        self.info_panel = QFrame()
        self.info_panel.setFrameShape(QFrame.StyledPanel)
        self.info_layout = QGridLayout(self.info_panel)
        labels = ["PAN", "Name", "Expiry", "CVV", "Service Code", "ZIP", "PIN"]
        self.lblPAN = QLabel("")
        self.lblName = QLabel("")
        self.lblExpiry = QLabel("")
        self.lblCVV = QLabel("")
        self.lblServiceCode = QLabel("")
        self.lblZIP = QLabel("")
        self.lblPIN = QLabel("")
        value_labels = [
            self.lblPAN, self.lblName, self.lblExpiry,
            self.lblCVV, self.lblServiceCode, self.lblZIP, self.lblPIN
        ]
        for i, text in enumerate(labels):
            self.info_layout.addWidget(QLabel(text + ":"), i, 0)
            self.info_layout.addWidget(value_labels[i], i, 1)
        self.main_layout.addWidget(self.info_panel)

        # TLV Tree and APDU log, side by side
        self.panel_row = QHBoxLayout()
        self.treeTLV = QTreeWidget()
        self.treeTLV.setHeaderLabels(["Tag", "Name", "Value"])
        self.treeTLV.setColumnCount(3)
        self.panel_row.addWidget(self.treeTLV, 2)

        self.txtAPDU = QTextEdit()
        self.txtAPDU.setReadOnly(True)
        self.panel_row.addWidget(self.txtAPDU, 3)
        self.main_layout.addLayout(self.panel_row)

        # Card selector
        self.cmbCards = QComboBox()
        self.main_layout.addWidget(self.cmbCards)

        # Card preview panel
        self.cardPreviewPanel = QFrame()
        self.cardPreviewPanel.setFrameShape(QFrame.StyledPanel)
        self.cardPreviewLayout = QGridLayout(self.cardPreviewPanel)
        self.lblPreviewPAN = QLabel("")
        self.lblPreviewName = QLabel("")
        self.lblPreviewExpiry = QLabel("")
        self.lblPreviewIssuer = QLabel("")
        self.cardPreviewLayout.addWidget(QLabel("PAN:"), 0, 0)
        self.cardPreviewLayout.addWidget(self.lblPreviewPAN, 0, 1)
        self.cardPreviewLayout.addWidget(QLabel("Name:"), 1, 0)
        self.cardPreviewLayout.addWidget(self.lblPreviewName, 1, 1)
        self.cardPreviewLayout.addWidget(QLabel("Expiry:"), 2, 0)
        self.cardPreviewLayout.addWidget(self.lblPreviewExpiry, 2, 1)
        self.cardPreviewLayout.addWidget(QLabel("Issuer:"), 3, 0)
        self.cardPreviewLayout.addWidget(self.lblPreviewIssuer, 3, 1)
        self.main_layout.addWidget(self.cardPreviewPanel)

        # Indicator placeholders
        self.readerIndicator = QLabel()
        self.btIndicator = QLabel()
        self.main_layout.addWidget(self.readerIndicator)
        self.main_layout.addWidget(self.btIndicator)

        # Cardhopper Panel
        self.cardhopperPanel = QFrame()
        self.cardhopperPanel.setFrameShape(QFrame.StyledPanel)
        self.cardhopperLayout = QGridLayout(self.cardhopperPanel)
        self.lblCHStatus = QLabel("Cardhopper: disconnected")
        self.cmbCHDevice = QComboBox()
        self.cmbCHDevice.addItems(["Auto", "PCSC", "PN532", "ACR", "Proxmark3", "Chameleon"])
        self.btnCHConnect = QPushButton("Connect")
        self.btnCHDisconnect = QPushButton("Disconnect")
        self.btnCHStart = QPushButton("Start Relay")
        self.btnCHStartServer = QPushButton("Start Server")
        self.btnCHStopServer = QPushButton("Stop Server")
        self.txtCHHost = QLabel("0.0.0.0:9000")
        self.btnCHInsert = QPushButton("Insert")
        self.btnCHEject = QPushButton("Eject")
        self.btnCHMove = QPushButton("Move")
        self.btnCHReset = QPushButton("Reset")
        self.btnCHBatchStart = QPushButton("Batch Start")
        self.btnCHBatchStop = QPushButton("Batch Stop")

        self.cardhopperLayout.addWidget(self.lblCHStatus, 0, 0, 1, 2)
        self.cardhopperLayout.addWidget(QLabel("Device:"), 1, 0)
        self.cardhopperLayout.addWidget(self.cmbCHDevice, 1, 1)
        self.cardhopperLayout.addWidget(self.btnCHConnect, 2, 0)
        self.cardhopperLayout.addWidget(self.btnCHDisconnect, 2, 1)
        self.cardhopperLayout.addWidget(self.btnCHStart, 3, 0)
        self.cardhopperLayout.addWidget(self.btnCHStartServer, 3, 1)
        self.cardhopperLayout.addWidget(self.btnCHStopServer, 4, 1)
        self.cardhopperLayout.addWidget(QLabel("Server:"), 4, 0)
        self.cardhopperLayout.addWidget(self.txtCHHost, 5, 0, 1, 2)
        self.cardhopperLayout.addWidget(self.btnCHInsert, 6, 0)
        self.cardhopperLayout.addWidget(self.btnCHEject, 6, 1)
        self.cardhopperLayout.addWidget(self.btnCHMove, 7, 0)
        self.cardhopperLayout.addWidget(self.btnCHReset, 7, 1)
        self.cardhopperLayout.addWidget(self.btnCHBatchStart, 8, 0)
        self.cardhopperLayout.addWidget(self.btnCHBatchStop, 8, 1)

        self.main_layout.addWidget(self.cardhopperPanel)

        # Tooltips
        self.btnReadCard.setToolTip("Read card from selected device")
        self.btnExportCard.setToolTip("Export selected card profile")
        self.btnImportCard.setToolTip("Import card profile from file")
        self.btnTransaction.setToolTip("Run EMV transaction (purchase/refund)")
        self.btnReplayCard.setToolTip("Replay card to POS terminal")
        self.btnRelayCard.setToolTip("Relay card via BLE to phone")
        self.btnSyncToPhone.setToolTip("Sync card profile to companion app")
        self.btnOfflinePINTest.setToolTip("Test offline PIN verification")
        self.btnThemeToggle.setToolTip("Toggle light/dark theme")
        self.btnDebugConsole.setToolTip("Open debug console")
        self.btnMSRWrite.setToolTip("Write magstripe data to MSR/MagSpoof device")
        self.btnMagspoofDowngrade.setToolTip("Enhanced EMV to magstripe conversion (201→101) with PIN 1337 and proper CVV")
        self.btnBulkAC.setToolTip("Run bulk GENERATE AC transactions")
        self.btnCredits.setToolTip("Show credits and attributions")
        self.btnKeyMgmt.setToolTip("Manage EMV cryptographic keys")
        self.btnPdolSettings.setToolTip("Configure PDOL/CDOL terminal settings")
        self.cmbMSRDevice.setToolTip("Select serial device for MSR/MagSpoof")
        self.cmbDevice.setToolTip("Select reader device (PCSC/PN532/etc)")
        self.cmbCards.setToolTip("Select card profile")
        self.cardPreviewPanel.setToolTip("Preview selected card details")
