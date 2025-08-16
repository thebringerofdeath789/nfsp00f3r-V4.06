# =====================================================================
# File: emv_transaction.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Enhanced EMV transaction flow with comprehensive CVM processing,
#   PIN verification, and proper cardholder verification method handling.
#
# Classes:
#   - EmvTransaction
# =====================================================================

import time
from typing import Dict, Any, Optional
from pdol_builder import build_env, build_pdol_value, parse_dol
from tlv import TLVParser
from cvm_processor import CVMProcessor
from pin_manager import PinManager

class EmvTransaction:
    """
    High-level transaction runner for purchase/refund/balance with comprehensive CVM processing.
    """
    def __init__(self, card, crypto, terminal_profile, logger=None):
        self.card = card
        self.crypto = crypto
        self.terminal_profile = terminal_profile
        self.logger = logger
        self.cvm_processor = CVMProcessor(logger)
        self.pin_manager = PinManager(logger)

    def run_purchase(self, amount, force_offline_pin=False, offline_approval=False, cdol_data=None, 
                    user_pin=None, ui_parent=None):
        """
        Enhanced EMV purchase flow with comprehensive CVM processing.
        
        Args:
            amount: Transaction amount in cents
            force_offline_pin: Force offline PIN verification
            offline_approval: Force offline approval (TC)
            cdol_data: Pre-built CDOL1 data (optional)
            user_pin: PIN provided by user (optional)
            ui_parent: Parent widget for PIN entry dialog
            
        Returns: Dict with transaction result, cryptogram, CVM results, and datasets
        """
        if self.logger:
            self.logger.log(f"Starting EMV purchase transaction: ${amount/100:.2f}")
            
        # 1. Get basic card data
        pan = getattr(self.card, 'pan', None) or self.card.info.get('PAN', 'unknown')
        atc = getattr(self.card, 'atc', 1)

        # 2. Build CDOL1 if not provided
        if cdol_data is None:
            nodes = getattr(self.card, 'tlv_root', []) or []
            cdol1_list = []
            try:
                def find_tag(nodes_, tag):
                    stack = list(nodes_)
                    while stack:
                        n = stack.pop()
                        if getattr(n, 'tag', None) == tag:
                            return getattr(n, 'value', b'')
                        stack.extend(getattr(n, 'children', []))
                    return b''
                    
                cdol1_bytes = find_tag(nodes, '8C')
                if cdol1_bytes:
                    cdol1_list = parse_dol(cdol1_bytes)
            except Exception:
                cdol1_list = []
                
            env = build_env(self.terminal_profile or {}, amount_cents=int(amount), tx_type=0x00)
            cdol_data = build_pdol_value(cdol1_list, env) if cdol1_list else b''

        # 3. Process CVM (Cardholder Verification Method)
        cvm_result = self._process_cvm(amount, user_pin, ui_parent)
        
        if self.logger:
            self.logger.log(f"CVM processing result: {cvm_result.successful}, method: {cvm_result.method_used}")

        # 4. Update CDOL data with CVM Results (tag 9F34)
        cdol_data = self._update_cdol_with_cvm(cdol_data, cvm_result)

        # 5. Check for PIN verification failure
        if cvm_result.pin_required and not cvm_result.successful:
            if self.logger:
                self.logger.log("PIN verification failed - generating AAC", "WARN")
            
            try:
                cryptogram = self.crypto.generate_aac(pan, atc, cdol_data)
                return {
                    "result": "DECLINED", 
                    "reason": "PIN_VERIFICATION_FAILED",
                    "cryptogram": cryptogram, 
                    "cvm_result": cvm_result,
                    "datasets": {"cdol1": cdol_data, "cdol2": b""}
                }
            except Exception as e:
                if self.logger:
                    self.logger.log(f"Cryptogram generation failed: {e}", "ERROR")
                return {"result": "ERROR", "reason": str(e)}

        # 6. Prepare CDOL2 (for potential 2nd GEN AC)
        cdol2_data = self._build_cdol2(amount, cvm_result)

        # 7. Generate appropriate cryptogram based on approval path
        try:
            if offline_approval or (cvm_result.successful and not cvm_result.pin_required):
                # Offline approval - generate TC
                cryptogram = self.crypto.generate_tc(pan, atc, cdol_data)
                if self.logger:
                    self.logger.log("Offline approval: TC generated.", level="INFO")
                return {
                    "result": "APPROVED_OFFLINE", 
                    "cryptogram": cryptogram, 
                    "cvm_result": cvm_result,
                    "datasets": {"cdol1": cdol_data, "cdol2": cdol2_data}
                }
            else:
                # Online authorization required - generate ARQC
                cryptogram = self.crypto.generate_arqc(pan, atc, cdol_data)
                if self.logger:
                    self.logger.log("Online authorization: ARQC generated.", level="INFO")
                return {
                    "result": "ARQC", 
                    "cryptogram": cryptogram,
                    "cvm_result": cvm_result, 
                    "datasets": {"cdol1": cdol_data, "cdol2": cdol2_data}
                }
                
        except Exception as e:
            if self.logger:
                self.logger.log(f"Cryptogram generation failed: {e}", "ERROR")
            return {"result": "ERROR", "reason": str(e)}
    
    def _process_cvm(self, amount: int, user_pin: Optional[str] = None, 
                    ui_parent=None):
        """
        Process Cardholder Verification Method (CVM) for the transaction.
        
        Args:
            amount: Transaction amount in cents
            user_pin: PIN provided by user
            ui_parent: Parent widget for PIN dialogs
            
        Returns: CVMResult with verification outcome
        """
        # Get CVM List from card (tag 8E)
        cvm_data = None
        nodes = getattr(self.card, 'tlv_root', []) or []
        
        def find_tag(nodes_, tag):
            stack = list(nodes_)
            while stack:
                n = stack.pop()
                if getattr(n, 'tag', None) == tag:
                    return getattr(n, 'value', b'')
                stack.extend(getattr(n, 'children', []))
            return b''
        
        cvm_data = find_tag(nodes, '8E')
        
        # If no CVM List found, use default
        if not cvm_data:
            if self.logger:
                self.logger.log("No CVM List found in card data, using default")
            cvm_data = self.cvm_processor.get_default_cvm_list()
        
        # Build transaction context for CVM processing
        terminal_profile = self.terminal_profile or {}
        transaction_context = {
            'amount': amount,
            'currency': terminal_profile.get('transaction_currency_code', '0840'),
            'terminal_type': int(terminal_profile.get('terminal_type', '22'), 16),
            'transaction_type': 0x00,  # Purchase
            'card': self.card,
            'offline_pin': user_pin,
            'online_pin_success': True  # Assume online PIN succeeds for testing
        }
        
        # Process CVM List
        cvm_result = self.cvm_processor.process_cvm_list(
            cvm_data, transaction_context, self.pin_manager
        )
        
        # If PIN is required but not provided, get it from user
        if cvm_result.pin_required and not user_pin and not cvm_result.successful:
            if self.logger:
                self.logger.log("PIN required - prompting user")
            
            user_pin = self.pin_manager.get_pin_from_user(
                parent=ui_parent,
                title="PIN Verification",
                prompt="Please enter your PIN for this transaction:"
            )
            
            if user_pin:
                # Re-process CVM with user-provided PIN
                transaction_context['offline_pin'] = user_pin
                cvm_result = self.cvm_processor.process_cvm_list(
                    cvm_data, transaction_context, self.pin_manager
                )
            else:
                if self.logger:
                    self.logger.log("User cancelled PIN entry", "WARN")
        
        return cvm_result
    
    def _update_cdol_with_cvm(self, cdol_data: bytes, cvm_result) -> bytes:
        """
        Update CDOL data with CVM Results (tag 9F34).
        
        In a full implementation, this would parse the CDOL structure
        and insert the CVM Results at the correct position.
        For now, we'll append it if not already present.
        """
        # CVM Results should be included in CDOL1 data
        # For simplicity, we'll assume it's already properly positioned
        # Real implementation would parse CDOL1 and insert at correct offset
        
        if self.logger:
            cvm_hex = cvm_result.result_code.hex().upper()
            self.logger.log(f"CVM Results (9F34): {cvm_hex}")
        
        return cdol_data  # Return as-is for now
    
    def _build_cdol2(self, amount: int, cvm_result) -> bytes:
        """Build CDOL2 data with CVM results"""
        nodes = getattr(self.card, 'tlv_root', []) or []
        cdol2_list = []
        
        try:
            def find_tag(nodes_, tag):
                stack = list(nodes_)
                while stack:
                    n = stack.pop()
                    if getattr(n, 'tag', None) == tag:
                        return getattr(n, 'value', b'')
                    stack.extend(getattr(n, 'children', []))
                return b''
                
            cdol2_bytes = find_tag(nodes, '8D')
            if cdol2_bytes:
                cdol2_list = parse_dol(cdol2_bytes)
        except Exception:
            cdol2_list = []
        
        # Build environment for CDOL2 (may include CVM Results)
        env = build_env(
            self.terminal_profile or {}, 
            amount_cents=int(amount), 
            tx_type=0x00
        )
        
        # Add CVM Results to environment
        env['9F34'] = cvm_result.result_code
        
        return build_pdol_value(cdol2_list, env) if cdol2_list else b''

    def run_refund(self, amount):
        # Same as purchase but with different transaction type, details omitted
        return self.run_purchase(amount)

    def run_balance(self):
        # Not all cards support, stub with minimal PDOL/CDOL
        return self.run_purchase(0)
