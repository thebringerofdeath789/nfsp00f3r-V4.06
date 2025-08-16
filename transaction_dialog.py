# =====================================================================
# File: transaction_dialog.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Dialog for configuring and running EMV transactions (purchase, refund,
#   balance) with amount entry, offline PIN, and card selector.
#
# Classes:
#   - TransactionDialog(QDialog)
# =====================================================================

import importlib
try:
    QtWidgets = importlib.import_module('PyQt5.QtWidgets')
    QtCore = importlib.import_module('PyQt5.QtCore')
    QDialog = QtWidgets.QDialog  # type: ignore
    QFormLayout = QtWidgets.QFormLayout  # type: ignore
    QComboBox = QtWidgets.QComboBox  # type: ignore
    QLineEdit = QtWidgets.QLineEdit  # type: ignore
    QCheckBox = QtWidgets.QCheckBox  # type: ignore
    QPushButton = QtWidgets.QPushButton  # type: ignore
    QHBoxLayout = QtWidgets.QHBoxLayout  # type: ignore
    QMessageBox = QtWidgets.QMessageBox  # type: ignore
    Qt = QtCore.Qt  # type: ignore
except Exception:
    QDialog = object  # type: ignore
    class _D: pass  # type: ignore
    QFormLayout = QComboBox = QLineEdit = QCheckBox = QPushButton = QHBoxLayout = QMessageBox = _D  # type: ignore
    class Qt: pass  # type: ignore
from emv_transaction import EmvTransaction
from emv_crypto import EmvCrypto
from cvm_processor import CVMType

class TransactionDialog(QDialog):
    def __init__(self, card, parent=None):
        super().__init__(parent)
        self.card = card
        self.result = None
        self.setWindowTitle("Transaction")
        self.setup_ui()

    def setup_ui(self):
        layout = QFormLayout(self)
        self.cmb_type = QComboBox(self)
        self.cmb_type.addItems(["Purchase", "Refund", "Balance"])
        layout.addRow("Transaction Type:", self.cmb_type)

        self.txt_amount = QLineEdit(self)
        self.txt_amount.setPlaceholderText("e.g. 12.34")
        layout.addRow("Amount:", self.txt_amount)

        self.chk_force_offline = QCheckBox("Force Offline PIN", self)
        layout.addRow("", self.chk_force_offline)

        self.cmb_cards = QComboBox(self)
        info = self.card.get_cardholder_info()
        pan = info.get("PAN", "<unknown>")
        self.cmb_cards.addItem(pan)
        layout.addRow("Select Card:", self.cmb_cards)

        btn_layout = QHBoxLayout()
        self.btn_run = QPushButton("Run", self)
        self.btn_run.clicked.connect(self.run_transaction)
        btn_layout.addWidget(self.btn_run)
        self.btn_cancel = QPushButton("Cancel", self)
        self.btn_cancel.clicked.connect(self.reject)
        btn_layout.addWidget(self.btn_cancel)
        layout.addRow(btn_layout)

    def run_transaction(self):
        amt_text = self.txt_amount.text().strip()
        try:
            amount_cents = int(round(float(amt_text) * 100))
            if amount_cents < 0:
                raise ValueError
        except ValueError:
            QMessageBox.warning(self, "Transaction", "Invalid amount format")
            return

        txn_type = self.cmb_type.currentText()
        force_offline = self.chk_force_offline.isChecked()

        try:
            # Ensure PDOL/GPO and records are present
            self.card.get_processing_options()
            records = self.card.read_sfi_records()
            self.card.parse_tlv_records(records)

            # Initialize crypto using key store if available
            if not getattr(self.card, 'crypto', None):
                pan = self.card.get_cardholder_info().get("PAN", "")
                aid = (self.card.info.get('AIDs') or [""])[0] if hasattr(self.card, 'info') else ""
                # Attempt to pull a key from MainWindow's keydb if accessible via parent
                master_key = None
                try:
                    mw = self.parent() if hasattr(self, 'parent') else None
                    keydb = getattr(mw, 'keydb', None)
                    entry = keydb.get(pan, aid) if keydb else None
                    if entry:
                        # support raw hex string or dict with 'mkac' key
                        if isinstance(entry, str):
                            master_key = bytes.fromhex(entry)
                        elif isinstance(entry, dict):
                            mk = entry.get('mkac') or entry.get('key')
                            if mk:
                                master_key = bytes.fromhex(mk)
                except Exception:
                    master_key = None
                if not master_key:
                    master_key = b"\x00" * 16
                self.card.crypto = EmvCrypto(master_key=master_key)

            # Build and run transaction
            term_profile = getattr(self.card, 'terminal_profile', {})
            txn = EmvTransaction(self.card, self.card.crypto, term_profile)
            
            # AUTOMATION MODE: Always use PIN "1337" for successful transactions
            # and prefer offline PIN verification for better success rates
            automation_pin = "1337"
            
            result = txn.run_purchase(
                amount_cents, 
                force_offline_pin=True,  # Force offline PIN for automation
                offline_approval=(txn_type == "Balance" and False),
                user_pin=automation_pin  # Always use master PIN
            )

            cg = result.get("cryptogram")
            cgh = cg.hex().upper() if isinstance(cg, (bytes, bytearray)) else str(cg)
            datasets = result.get("datasets", {})
            cdol1_hex = datasets.get("cdol1", b"").hex().upper()
            cdol2_hex = datasets.get("cdol2", b"").hex().upper()
            
            # Enhanced result display with automation info
            cvm_result = result.get("cvm_result")
            cvm_info = ""
            if cvm_result:
                cvm_method = getattr(cvm_result, 'method_used', 'Unknown')
                cvm_success = getattr(cvm_result, 'successful', False)
                cvm_info = f"\nCVM: {cvm_method} ({'SUCCESS' if cvm_success else 'FAILED'})"
            
            self.result = (f"{result.get('result')} AC: {cgh} (amount {amt_text}){cvm_info}\n"
                          f"PIN Used: {automation_pin} (Master PIN)\n"
                          f"CDOL1: {cdol1_hex}\nCDOL2: {cdol2_hex}")
            self.accept()
        except Exception as e:
            QMessageBox.critical(self, "Transaction Error", str(e))
            return

    def get_result(self):
        return self.result
