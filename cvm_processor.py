#!/usr/bin/env python3
# =====================================================================
# File: cvm_processor.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Comprehensive Cardholder Verification Method (CVM) processing engine.
#   Handles CVM List parsing, rule evaluation, PIN verification flows,
#   and CVM Results construction for EMV transactions.
#
# Classes:
#   - CVMProcessor
#   - CVMRule
#   - CVMResult
# =====================================================================

import struct
from typing import List, Dict, Optional, Tuple, Any
from dataclasses import dataclass
from enum import IntEnum

class CVMType(IntEnum):
    """CVM Method types as defined in EMV specification"""
    FAIL_CVM = 0x00
    PLAINTEXT_PIN_BY_ICC = 0x01
    ENCIPHERED_PIN_ONLINE = 0x02
    PLAINTEXT_PIN_BY_ICC_AND_SIGNATURE = 0x03
    ENCIPHERED_PIN_BY_ICC = 0x04
    ENCIPHERED_PIN_BY_ICC_AND_SIGNATURE = 0x05
    SIGNATURE = 0x1E
    NO_CVM_REQUIRED = 0x1F
    # Additional contactless CVM types
    CDCVM = 0x43  # Consumer Device CVM (mobile payments)
    
class CVMCondition(IntEnum):
    """CVM Condition codes as defined in EMV specification"""
    ALWAYS = 0x00
    IF_UNATTENDED_CASH = 0x01
    IF_NOT_UNATTENDED_CASH_AND_NOT_MANUAL_CASH_AND_NOT_PURCHASE_WITH_CASHBACK = 0x02
    IF_TERMINAL_SUPPORTS_CVM = 0x03
    IF_MANUAL_CASH = 0x04
    IF_PURCHASE_WITH_CASHBACK = 0x05
    IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_X_VALUE = 0x06
    IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_OVER_X_VALUE = 0x07
    IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_Y_VALUE = 0x08
    IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_OVER_Y_VALUE = 0x09

@dataclass
class CVMRule:
    """Represents a single CVM rule from the CVM List"""
    method: int          # CVM method (6 bits)
    condition: int       # CVM condition (6 bits) 
    apply_succeeding: bool  # If set, apply succeeding rule on failure
    fail_cardholder_verification: bool  # If set, fail CVM on failure
    
    def __str__(self):
        method_name = CVMType(self.method & 0x3F).name if (self.method & 0x3F) in CVMType._value2member_map_ else f"UNKNOWN_{self.method:02X}"
        condition_name = CVMCondition(self.condition).name if self.condition in CVMCondition._value2member_map_ else f"UNKNOWN_{self.condition:02X}"
        return f"CVM({method_name}, {condition_name}, apply_next={self.apply_succeeding})"

@dataclass 
class CVMResult:
    """Result of CVM processing"""
    method_used: int
    condition_satisfied: bool
    successful: bool
    result_code: bytes  # 3-byte CVM Results (9F34)
    pin_required: bool = False
    signature_required: bool = False
    
class CVMProcessor:
    """
    Comprehensive CVM processing engine for EMV transactions.
    Handles CVM List parsing, rule evaluation, and result construction.
    """
    
    def __init__(self, logger=None):
        self.logger = logger
        
    def parse_cvm_list(self, cvm_data: bytes) -> Tuple[int, int, List[CVMRule]]:
        """
        Parse CVM List (tag 8E) into amount limits and rules.
        
        Format:
        - Bytes 1-4: Amount (X) for offline PIN (BCD)  
        - Bytes 5-8: Amount (Y) for online PIN (BCD)
        - Remaining: CVM Rules (2 bytes each)
        
        Returns: (amount_x, amount_y, rules_list)
        """
        if len(cvm_data) < 8:
            if self.logger:
                self.logger.log("CVM List too short, using defaults", "WARN")
            return 0, 0, []
            
        # Parse amount limits (BCD format)
        amount_x = struct.unpack('>I', cvm_data[0:4])[0]
        amount_y = struct.unpack('>I', cvm_data[4:8])[0]
        
        # Parse CVM rules
        rules = []
        for i in range(8, len(cvm_data), 2):
            if i + 1 < len(cvm_data):
                byte1 = cvm_data[i]
                byte2 = cvm_data[i + 1]
                
                # Extract CVM method (6 bits)
                method = byte1 & 0x3F
                
                # Extract condition code (6 bits) 
                condition = byte2 & 0x3F
                
                # Extract control bits
                apply_succeeding = (byte1 & 0x40) == 0  # Bit 7 clear = apply next rule
                fail_cardholder_verification = (byte2 & 0x40) != 0  # Bit 7 set = fail CVM
                
                rule = CVMRule(
                    method=method,
                    condition=condition,
                    apply_succeeding=apply_succeeding,
                    fail_cardholder_verification=fail_cardholder_verification
                )
                rules.append(rule)
                
        if self.logger:
            self.logger.log(f"Parsed CVM List: X={amount_x}, Y={amount_y}, {len(rules)} rules")
            
        return amount_x, amount_y, rules
    
    def evaluate_cvm_condition(self, rule: CVMRule, transaction_context: Dict[str, Any]) -> bool:
        """
        Evaluate whether a CVM condition is satisfied given transaction context.
        
        Args:
            rule: CVM rule to evaluate
            transaction_context: Dict with transaction details
                - amount: transaction amount in cents
                - currency: currency code  
                - terminal_type: terminal type
                - transaction_type: transaction type
                - amount_x: offline PIN limit
                - amount_y: online PIN limit
        
        Returns: True if condition is satisfied
        """
        condition = rule.condition
        amount = transaction_context.get('amount', 0)
        terminal_type = transaction_context.get('terminal_type', 0x22)
        tx_type = transaction_context.get('transaction_type', 0x00)
        amount_x = transaction_context.get('amount_x', 0)
        amount_y = transaction_context.get('amount_y', 0)
        
        if condition == CVMCondition.ALWAYS:
            return True
            
        elif condition == CVMCondition.IF_UNATTENDED_CASH:
            # Check if unattended cash transaction
            return (terminal_type & 0x0F) == 0x03 and tx_type == 0x01
            
        elif condition == CVMCondition.IF_NOT_UNATTENDED_CASH_AND_NOT_MANUAL_CASH_AND_NOT_PURCHASE_WITH_CASHBACK:
            # Exclude specific transaction types
            is_unattended_cash = (terminal_type & 0x0F) == 0x03 and tx_type == 0x01
            is_manual_cash = (terminal_type & 0x0F) == 0x01 and tx_type == 0x01  
            is_cashback = tx_type == 0x09
            return not (is_unattended_cash or is_manual_cash or is_cashback)
            
        elif condition == CVMCondition.IF_TERMINAL_SUPPORTS_CVM:
            # Assume terminal supports CVM if method is implemented
            return True
            
        elif condition == CVMCondition.IF_MANUAL_CASH:
            return (terminal_type & 0x0F) == 0x01 and tx_type == 0x01
            
        elif condition == CVMCondition.IF_PURCHASE_WITH_CASHBACK:
            return tx_type == 0x09
            
        elif condition == CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_X_VALUE:
            return amount < amount_x
            
        elif condition == CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_OVER_X_VALUE:
            return amount >= amount_x
            
        elif condition == CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_Y_VALUE:
            return amount < amount_y
            
        elif condition == CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_OVER_Y_VALUE:
            return amount >= amount_y
            
        else:
            if self.logger:
                self.logger.log(f"Unknown CVM condition: {condition:02X}", "WARN")
            return False
    
    def process_cvm_list(self, cvm_data: bytes, transaction_context: Dict[str, Any], 
                        pin_manager=None) -> CVMResult:
        """
        Process complete CVM List and return verification result.
        
        Args:
            cvm_data: Raw CVM List data (tag 8E)
            transaction_context: Transaction details
            pin_manager: PIN manager for verification
            
        Returns: CVMResult with verification outcome
        """
        # Parse CVM List
        amount_x, amount_y, rules = self.parse_cvm_list(cvm_data)
        
        # Add amount limits to context
        transaction_context['amount_x'] = amount_x
        transaction_context['amount_y'] = amount_y
        
        # Process rules in order
        for rule in rules:
            if self.logger:
                self.logger.log(f"Evaluating CVM rule: {rule}")
                
            # Check if condition is satisfied
            if not self.evaluate_cvm_condition(rule, transaction_context):
                if self.logger:
                    self.logger.log("CVM condition not satisfied, trying next rule")
                continue
                
            # Process the CVM method
            result = self._process_cvm_method(rule, transaction_context, pin_manager)
            
            if result.successful or rule.fail_cardholder_verification:
                # CVM succeeded or rule says to fail on unsuccessful CVM
                return result
                
            if not rule.apply_succeeding:
                # Rule says not to try next rule on failure
                break
        
        # No successful CVM found - fail cardholder verification
        if self.logger:
            self.logger.log("No CVM rule satisfied - failing cardholder verification", "WARN")
            
        return CVMResult(
            method_used=CVMType.FAIL_CVM,
            condition_satisfied=False,
            successful=False,
            result_code=self._build_cvm_results(CVMType.FAIL_CVM, False, False)
        )
    
    def _process_cvm_method(self, rule: CVMRule, transaction_context: Dict[str, Any], 
                          pin_manager=None) -> CVMResult:
        """Process a specific CVM method and return result"""
        method = rule.method
        
        if method == CVMType.NO_CVM_REQUIRED:
            if self.logger:
                self.logger.log("No CVM required")
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=True,
                result_code=self._build_cvm_results(method, True, True)
            )
            
        elif method == CVMType.SIGNATURE:
            if self.logger:
                self.logger.log("Signature CVM")
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=True,
                result_code=self._build_cvm_results(method, True, True),
                signature_required=True
            )
            
        elif method == CVMType.PLAINTEXT_PIN_BY_ICC:
            if self.logger:
                self.logger.log("Offline plaintext PIN verification")
            
            # Perform offline PIN verification
            pin_success = False
            if pin_manager:
                try:
                    # For testing, use default PIN
                    test_pin = transaction_context.get('offline_pin', '1234')
                    pin_success = pin_manager.verify_offline_pin(
                        transaction_context.get('card'), test_pin
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Offline PIN verification error: {e}", "ERROR")
            
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=pin_success,
                result_code=self._build_cvm_results(method, True, pin_success),
                pin_required=True
            )
            
        elif method == CVMType.ENCIPHERED_PIN_ONLINE:
            if self.logger:
                self.logger.log("Online enciphered PIN verification")
            
            # Online PIN - assume successful for testing
            # In real implementation, this would be sent to issuer
            pin_success = transaction_context.get('online_pin_success', True)
            
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=pin_success,
                result_code=self._build_cvm_results(method, True, pin_success),
                pin_required=True
            )
            
        elif method == CVMType.ENCIPHERED_PIN_BY_ICC:
            if self.logger:
                self.logger.log("Offline enciphered PIN verification")
                
            # Enciphered offline PIN verification 
            pin_success = False
            if pin_manager:
                try:
                    test_pin = transaction_context.get('offline_pin', '1234')
                    pin_success = pin_manager.verify_offline_pin(
                        transaction_context.get('card'), test_pin
                    )
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"Enciphered PIN verification error: {e}", "ERROR")
            
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=pin_success,
                result_code=self._build_cvm_results(method, True, pin_success),
                pin_required=True
            )
            
        elif method == CVMType.CDCVM:
            if self.logger:
                self.logger.log("Consumer Device CVM (mobile payment)")
            
            # CDCVM - assume successful for mobile payments
            cdcvm_success = transaction_context.get('cdcvm_success', True)
            
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=cdcvm_success,
                result_code=self._build_cvm_results(method, True, cdcvm_success)
            )
            
        else:
            if self.logger:
                self.logger.log(f"Unsupported CVM method: {method:02X}", "WARN")
            
            return CVMResult(
                method_used=method,
                condition_satisfied=True,
                successful=False,
                result_code=self._build_cvm_results(method, True, False)
            )
    
    def _build_cvm_results(self, method: int, condition_satisfied: bool, successful: bool) -> bytes:
        """
        Build CVM Results (tag 9F34) - 3 bytes
        
        Byte 1: CVM method used
        Byte 2: CVM condition and result
        Byte 3: Reserved (usually 00)
        """
        byte1 = method & 0x3F
        
        byte2 = 0x00
        if condition_satisfied:
            byte2 |= 0x40  # Bit 6 set = condition satisfied
        if successful:
            byte2 |= 0x80  # Bit 7 set = CVM successful
            
        byte3 = 0x00  # Reserved
        
        return bytes([byte1, byte2, byte3])
    
    def get_default_cvm_list(self, offline_limit: int = 5000, online_limit: int = 10000) -> bytes:
        """
        Generate a default CVM List for testing/fallback scenarios.
        
        Args:
            offline_limit: Amount limit for offline PIN (cents)
            online_limit: Amount limit for online PIN (cents)
            
        Returns: CVM List bytes suitable for tag 8E
        """
        # Amount X (offline PIN limit) in BCD
        amount_x = struct.pack('>I', offline_limit)
        
        # Amount Y (online PIN limit) in BCD  
        amount_y = struct.pack('>I', online_limit)
        
        # Default CVM rules:
        # 1. Offline PIN if under offline limit
        # 2. Online PIN if under online limit
        # 3. Signature otherwise
        # 4. No CVM as fallback
        
        rules = []
        
        # Rule 1: Offline PIN if amount < X
        rules.append(bytes([
            CVMType.PLAINTEXT_PIN_BY_ICC,  # Method
            CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_X_VALUE  # Condition
        ]))
        
        # Rule 2: Online PIN if amount < Y  
        rules.append(bytes([
            CVMType.ENCIPHERED_PIN_ONLINE,  # Method
            CVMCondition.IF_TRANSACTION_IN_APPLICATION_CURRENCY_AND_UNDER_Y_VALUE  # Condition
        ]))
        
        # Rule 3: Signature for higher amounts
        rules.append(bytes([
            CVMType.SIGNATURE,  # Method  
            CVMCondition.ALWAYS  # Condition
        ]))
        
        # Rule 4: No CVM as final fallback (should not fail)
        rules.append(bytes([
            CVMType.NO_CVM_REQUIRED | 0x80,  # Method with "last rule" bit
            CVMCondition.ALWAYS  # Condition
        ]))
        
        return amount_x + amount_y + b''.join(rules)
    
    def format_cvm_results_for_display(self, result: CVMResult) -> Dict[str, str]:
        """Format CVM results for UI display"""
        method_name = CVMType(result.method_used).name if result.method_used in CVMType._value2member_map_ else f"Unknown ({result.method_used:02X})"
        
        return {
            "method": method_name,
            "condition_satisfied": "Yes" if result.condition_satisfied else "No",
            "successful": "Yes" if result.successful else "No", 
            "result_code": result.result_code.hex().upper(),
            "pin_required": "Yes" if result.pin_required else "No",
            "signature_required": "Yes" if result.signature_required else "No"
        }
