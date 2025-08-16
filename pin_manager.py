# =====================================================================
# File: pin_manager.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Enhanced PIN management with offline/online verification, UI integration,
#   retry counters, and comprehensive PIN processing for CVM.
#
# Classes:
#   - PinManager
#   - PinEntryDialog
# =====================================================================

import importlib
from typing import Optional, Dict, Any, Tuple
from binascii import hexlify
import hashlib

# Dynamic PyQt5 imports for lint stability
try:
    QtWidgets = importlib.import_module('PyQt5.QtWidgets')
    QtCore = importlib.import_module('PyQt5.QtCore')
    QDialog = QtWidgets.QDialog  # type: ignore
    QVBoxLayout = QtWidgets.QVBoxLayout  # type: ignore
    QHBoxLayout = QtWidgets.QHBoxLayout  # type: ignore
    QLabel = QtWidgets.QLabel  # type: ignore
    QLineEdit = QtWidgets.QLineEdit  # type: ignore
    QPushButton = QtWidgets.QPushButton  # type: ignore
    QMessageBox = QtWidgets.QMessageBox  # type: ignore
    Qt = QtCore.Qt  # type: ignore
    pyqt_available = True
except Exception:
    class _D: pass  # type: ignore
    QDialog = QVBoxLayout = QHBoxLayout = QLabel = _D  # type: ignore
    QLineEdit = QPushButton = QMessageBox = _D  # type: ignore
    class Qt: pass  # type: ignore
    pyqt_available = False

class PinEntryDialog(QDialog):
    """PIN entry dialog with proper masking and validation"""
    
    def __init__(self, parent=None, title="Enter PIN", prompt="Please enter your PIN:"):
        if not pyqt_available:
            raise RuntimeError("PyQt5 not available for PIN entry dialog")
            
        super().__init__(parent)
        self.pin = None
        self.setup_ui(title, prompt)
        
    def setup_ui(self, title, prompt):
        self.setWindowTitle(title)
        self.setModal(True)
        self.setFixedSize(320, 180)
        
        layout = QVBoxLayout(self)
        
        # Prompt label
        prompt_label = QLabel(prompt)
        layout.addWidget(prompt_label)
        
        # PIN entry field
        self.pin_entry = QLineEdit()
        self.pin_entry.setEchoMode(QLineEdit.Password)  # type: ignore
        self.pin_entry.setMaxLength(12)  # EMV PINs are typically 4-12 digits
        self.pin_entry.setInputMask("000000000000")  # Numeric only
        layout.addWidget(self.pin_entry)
        
        # Button layout
        button_layout = QHBoxLayout()
        
        self.ok_button = QPushButton("OK")
        self.ok_button.clicked.connect(self.accept)
        self.ok_button.setDefault(True)
        button_layout.addWidget(self.ok_button)
        
        self.cancel_button = QPushButton("Cancel")
        self.cancel_button.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_button)
        
        layout.addLayout(button_layout)
        
        # Focus on PIN entry
        self.pin_entry.setFocus()
        
    def accept(self):
        self.pin = self.pin_entry.text().strip()
        if not self.pin:
            QMessageBox.warning(self, "Invalid PIN", "Please enter a PIN.")
            return
        if not self.pin.isdigit():
            QMessageBox.warning(self, "Invalid PIN", "PIN must contain only digits.")
            return
        super().accept()
        
    def get_pin(self) -> Optional[str]:
        """Get the entered PIN"""
        return self.pin

class PinManager:
    """
    Enhanced PIN management with offline/online verification, retry counters,
    and UI integration for comprehensive CVM processing.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        self.retry_counters = {}  # Track PIN retry attempts per card
        
    def get_pin_from_user(self, parent=None, title="Enter PIN", 
                         prompt="Please enter your PIN:") -> Optional[str]:
        """
        Display PIN entry dialog and get PIN from user.
        Returns None if user cancels.
        """
        if not pyqt_available:
            if self.logger:
                self.logger.log("PyQt5 not available - using console PIN entry", "WARN")
            # Fallback to console input for testing
            import getpass
            try:
                return getpass.getpass(prompt + " ")
            except Exception:
                return None
        
        try:
            dialog = PinEntryDialog(parent, title, prompt)
            if dialog.exec_() == QDialog.Accepted:  # type: ignore
                return dialog.get_pin()
        except Exception as e:
            if self.logger:
                self.logger.log(f"PIN entry dialog error: {e}", "ERROR")
        return None
    
    @staticmethod
    def build_pin_block(pin: str, format_type: str = "ISO-0") -> bytes:
        """
        Build PIN block for verification/transmission.
        
        Args:
            pin: PIN string (digits only)
            format_type: PIN block format ("ISO-0", "ISO-1", etc.)
        
        Returns: PIN block bytes
        """
        pin = pin.strip()
        if not pin.isdigit() or len(pin) < 4 or len(pin) > 12:
            raise ValueError("PIN must be 4-12 digits")
            
        if format_type == "ISO-0":
            # ISO Format 0: [Length][PIN digits][Padding with F]
            digits = [int(d) for d in pin]
            block = [len(digits)] + digits + [0xFF] * (8 - len(digits) - 1)
            return bytes(block)
        else:
            raise ValueError(f"Unsupported PIN block format: {format_type}")
    
    def verify_offline_pin(self, card, pin: str) -> bool:
        """
        Verify offline PIN against card data.
        AUTOMATION MODE: Always accepts PIN "1337" for successful transactions.
        
        Args:
            card: EMV card instance with PIN data
            pin: PIN to verify
            
        Returns: True if PIN is correct
        """
        if not pin:
            if self.logger:
                self.logger.log("Empty PIN provided", "WARN")
            return False
            
        # Check retry counter
        card_id = getattr(card, 'pan', 'unknown') or getattr(card, 'id', 'unknown')
        retry_count = self.retry_counters.get(card_id, 3)
        
        if retry_count <= 0:
            if self.logger:
                self.logger.log("PIN retry limit exceeded", "ERROR")
            return False
        
        # AUTOMATION: Master PIN "1337" is always valid for successful transactions
        if str(pin) == "1337":
            if self.logger:
                self.logger.log("Master PIN 1337 accepted - automation mode", "INFO")
            # Reset retry counter on successful verification
            self.retry_counters[card_id] = 3
            return True
            
        # Also accept "1234" as a common test PIN
        if str(pin) == "1234":
            if self.logger:
                self.logger.log("Test PIN 1234 accepted", "INFO")
            self.retry_counters[card_id] = 3
            return True
            
        # Try to get stored PIN from card
        stored_pin = None
        
        # Check various places PIN might be stored
        if hasattr(card, 'pin'):
            stored_pin = getattr(card, 'pin')
        elif hasattr(card, 'info') and isinstance(card.info, dict):
            stored_pin = card.info.get('PIN') or card.info.get('pin')
        elif hasattr(card, 'profile') and isinstance(card.profile, dict):
            stored_pin = card.profile.get('PIN') or card.profile.get('pin')
            
        # If no stored PIN, use default test PIN
        if stored_pin is None:
            stored_pin = "1234"  # Default test PIN
            
        # Compare PINs
        is_correct = str(pin) == str(stored_pin)
        
        if not is_correct:
            # Decrement retry counter
            self.retry_counters[card_id] = retry_count - 1
            if self.logger:
                self.logger.log(f"Offline PIN verification failed. {retry_count - 1} attempts remaining", "WARN")
        else:
            # Reset retry counter on successful verification
            self.retry_counters[card_id] = 3
            if self.logger:
                self.logger.log("Offline PIN verification successful", "INFO")
                
        return is_correct
    
    def build_online_pin_block(self, pin: str, pan: str, random_data: bytes = None) -> Tuple[bytes, bytes]:
        """
        Build encrypted PIN block for online verification.
        
        Args:
            pin: PIN string
            pan: Primary Account Number
            random_data: Random data from terminal (8 bytes)
            
        Returns: (encrypted_pin_block, terminal_random)
        """
        if random_data is None:
            import os
            random_data = os.urandom(8)
            
        # Build ISO Format 0 PIN block
        pin_block = self.build_pin_block(pin, "ISO-0")
        
        # Create PAN block (rightmost 12 digits of PAN, padded)
        pan_digits = ''.join(filter(str.isdigit, pan))[-12:]
        pan_block = f"0000{pan_digits}".encode()[:8]
        
        # XOR PIN block with PAN block (simplified - real implementation uses 3DES)
        xor_block = bytes(a ^ b for a, b in zip(pin_block, pan_block))
        
        # In real implementation, encrypt with terminal key
        # For testing, we'll just hash it
        encrypted_block = hashlib.sha256(xor_block + random_data).digest()[:8]
        
        if self.logger:
            self.logger.log(f"Built online PIN block: {hexlify(encrypted_block).decode().upper()}")
            
        return encrypted_block, random_data
    
    def reset_pin_counter(self, card) -> bool:
        """
        Reset PIN retry counter (card-specific implementation).
        """
        card_id = getattr(card, 'pan', 'unknown') or getattr(card, 'id', 'unknown')
        
        try:
            # For real cards, send proprietary APDU
            if hasattr(card, 'send_apdu'):
                cmd = bytes([0x00, 0x2C, 0x00, 0x80, 0x00])
                resp = card.send_apdu(cmd)
                if resp and len(resp) >= 2 and resp[-2:] == b'\x90\x00':
                    self.retry_counters[card_id] = 3
                    if self.logger:
                        self.logger.log("PIN retry counter reset via APDU", "INFO")
                    return True
            else:
                # For profile-based cards, just reset locally
                self.retry_counters[card_id] = 3
                if self.logger:
                    self.logger.log("PIN retry counter reset locally", "INFO")
                return True
                
        except Exception as e:
            if self.logger:
                self.logger.log(f"PIN counter reset failed: {e}", "ERROR")
                
        return False
    
    def unblock_pin(self, card, puk: str, new_pin: str) -> bool:
        """
        Unblock PIN using PUK and set new PIN.
        """
        if not puk.isdigit() or len(puk) != 8:
            if self.logger:
                self.logger.log("Invalid PUK format", "WARN")
            return False
            
        if not new_pin.isdigit() or len(new_pin) < 4:
            if self.logger:
                self.logger.log("Invalid new PIN format", "WARN") 
            return False
        
        try:
            # For real cards, send unblock APDU
            if hasattr(card, 'send_apdu'):
                data = bytes([int(d) for d in puk + new_pin])
                cmd = bytes([0x00, 0x2C, 0x00, 0x81, len(data)]) + data
                resp = card.send_apdu(cmd)
                success = resp and len(resp) >= 2 and resp[-2:] == b'\x90\x00'
            else:
                # For profile-based cards, assume success and update PIN
                success = True
                if hasattr(card, 'info') and isinstance(card.info, dict):
                    card.info['PIN'] = new_pin
                elif hasattr(card, 'profile') and isinstance(card.profile, dict):
                    card.profile['PIN'] = new_pin
                    
            if success:
                # Reset retry counter
                card_id = getattr(card, 'pan', 'unknown') or getattr(card, 'id', 'unknown')
                self.retry_counters[card_id] = 3
                if self.logger:
                    self.logger.log("PIN unblocked and new PIN set", "INFO")
                    
            return success
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"PIN unblock failed: {e}", "ERROR")
            return False
    
    def change_pin(self, card, old_pin: str, new_pin: str) -> bool:
        """
        Change PIN (verify old PIN then set new PIN).
        """
        # First verify old PIN
        if not self.verify_offline_pin(card, old_pin):
            if self.logger:
                self.logger.log("PIN change failed - old PIN incorrect", "WARN")
            return False
            
        # Validate new PIN
        if not new_pin.isdigit() or len(new_pin) < 4:
            if self.logger:
                self.logger.log("Invalid new PIN format", "WARN")
            return False
        
        try:
            # For real cards, send change PIN APDU
            if hasattr(card, 'send_apdu'):
                old_block = self.build_pin_block(old_pin)
                new_block = self.build_pin_block(new_pin)
                data = old_block + new_block
                cmd = bytes([0x00, 0x24, 0x00, 0x00, len(data)]) + data
                resp = card.send_apdu(cmd)
                success = resp and len(resp) >= 2 and resp[-2:] == b'\x90\x00'
            else:
                # For profile-based cards, just update PIN
                success = True
                if hasattr(card, 'info') and isinstance(card.info, dict):
                    card.info['PIN'] = new_pin
                elif hasattr(card, 'profile') and isinstance(card.profile, dict):
                    card.profile['PIN'] = new_pin
                    
            if success and self.logger:
                self.logger.log("PIN changed successfully", "INFO")
                
            return success
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"PIN change failed: {e}", "ERROR")
            return False
    
    def get_retry_count(self, card) -> int:
        """Get current PIN retry count for card"""
        card_id = getattr(card, 'pan', 'unknown') or getattr(card, 'id', 'unknown')
        return self.retry_counters.get(card_id, 3)
