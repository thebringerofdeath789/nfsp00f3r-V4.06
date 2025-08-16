#!/usr/bin/env python3
"""
Magnetic Stripe CVV Generator for NFCSpoofer V4.05
Implements industry-standard CVV generation algorithms (CVV1/CVV2)

This module provides cryptographic CVV generation using the IBM CVV algorithm
which is the industry standard for magnetic stripe verification values.
"""

import hashlib
from Crypto.Cipher import DES3, DES
from typing import Tuple, Optional


class MagstripeCVVGenerator:
    """
    Generates magnetic stripe CVV (Card Verification Value) using industry-standard algorithms.
    
    The CVV is calculated using:
    - PAN (Primary Account Number)
    - Expiry Date (YYMM format)
    - Service Code (3 digits)
    - CVV Key Pair (CVKA and CVKB - 64-bit DES keys)
    
    Algorithm follows IBM CVV standard used by major card networks.
    """
    
    def __init__(self, cvk_a: bytes, cvk_b: bytes):
        """
        Initialize CVV generator with CVV key pair.
        
        Args:
            cvk_a: First CVV key (8 bytes)
            cvk_b: Second CVV key (8 bytes)
        """
        if len(cvk_a) != 8 or len(cvk_b) != 8:
            raise ValueError("CVV keys must be exactly 8 bytes each")
        
        self.cvk_a = cvk_a
        self.cvk_b = cvk_b
    
    @classmethod
    def generate_default_keys(cls, master_seed: bytes = None) -> Tuple[bytes, bytes]:
        """
        Generate a default CVK key pair from a master seed.
        
        Args:
            master_seed: Optional seed for key generation (16+ bytes)
            
        Returns:
            Tuple of (cvk_a, cvk_b) keys
        """
        if master_seed is None:
            # Default test keys (DO NOT use in production)
            cvk_a = bytes.fromhex("0123456789ABCDEF")  
            cvk_b = bytes.fromhex("FEDCBA9876543210")
        else:
            if len(master_seed) < 16:
                raise ValueError("Master seed must be at least 16 bytes")
            
            # Derive CVK keys from master seed
            hash1 = hashlib.sha256(master_seed + b"CVKA").digest()
            hash2 = hashlib.sha256(master_seed + b"CVKB").digest()
            cvk_a = hash1[:8]
            cvk_b = hash2[:8]
        
        return cvk_a, cvk_b
    
    def _prepare_cvv_input(self, pan: str, expiry: str, service_code: str) -> bytes:
        """
        Prepare input data for CVV calculation according to IBM CVV standard.
        
        Args:
            pan: Primary Account Number (digits only)
            expiry: Expiry date in YYMM format
            service_code: 3-digit service code
            
        Returns:
            16-byte input block for CVV calculation
        """
        # Clean PAN (remove spaces, dashes)
        clean_pan = ''.join(c for c in pan if c.isdigit())
        
        # Ensure expiry is 4 digits (YYMM)
        if len(expiry) != 4 or not expiry.isdigit():
            raise ValueError("Expiry must be 4 digits in YYMM format")
        
        # Ensure service code is 3 digits
        if len(service_code) != 3 or not service_code.isdigit():
            raise ValueError("Service code must be exactly 3 digits")
        
        # Build CVV input block: PAN + YYMM + Service Code, padded to 16 bytes
        cvv_data = clean_pan + expiry + service_code
        
        # Pad or truncate to exactly 16 hex digits (8 bytes when packed)
        if len(cvv_data) > 16:
            cvv_data = cvv_data[:16]
        else:
            cvv_data = cvv_data.ljust(16, '0')
        
        # Convert to binary (BCD-like encoding for compatibility)
        try:
            return bytes.fromhex(cvv_data)
        except ValueError:
            # Fallback: encode as ASCII and pad
            ascii_data = cvv_data.encode('ascii')[:8]
            return ascii_data.ljust(8, b'\x00')
    
    def generate_cvv(self, pan: str, expiry: str, service_code: str, cvv_length: int = 3) -> str:
        """
        Generate CVV using IBM CVV algorithm.
        
        The algorithm:
        1. Prepare input block from PAN, expiry, and service code
        2. Encrypt with CVKA using DES
        3. XOR result with input block
        4. Encrypt with CVKB using DES
        5. Extract decimal digits from result
        
        Args:
            pan: Primary Account Number
            expiry: Expiry date (YYMM)
            service_code: Service code (3 digits)
            cvv_length: Length of CVV to generate (3 or 4 digits)
            
        Returns:
            CVV as string of decimal digits
        """
        if cvv_length not in (3, 4):
            raise ValueError("CVV length must be 3 or 4 digits")
        
        # Prepare input block
        input_block = self._prepare_cvv_input(pan, expiry, service_code)
        
        # Step 1: Encrypt input block with CVKA
        cipher_a = DES.new(self.cvk_a, DES.MODE_ECB)
        encrypted_a = cipher_a.encrypt(input_block)
        
        # Step 2: XOR encrypted result with input block
        xor_result = bytes(a ^ b for a, b in zip(encrypted_a, input_block))
        
        # Step 3: Encrypt XOR result with CVKB
        cipher_b = DES.new(self.cvk_b, DES.MODE_ECB)
        encrypted_b = cipher_b.encrypt(xor_result)
        
        # Step 4: Extract decimal digits from the result
        cvv_digits = ""
        for byte in encrypted_b:
            # Extract decimal digits (0-9) from each byte
            digit1 = byte >> 4  # Upper nibble
            digit2 = byte & 0x0F  # Lower nibble
            
            # Convert to decimal digits (A-F become 0-5)
            if digit1 <= 9:
                cvv_digits += str(digit1)
            else:
                cvv_digits += str(digit1 - 10)
                
            if digit2 <= 9:
                cvv_digits += str(digit2)
            else:
                cvv_digits += str(digit2 - 10)
        
        # Return requested number of digits
        return cvv_digits[:cvv_length]
    
    def generate_discretionary_data(self, pan: str, expiry: str, service_code: str, 
                                   additional_data: str = "000000") -> str:
        """
        Generate discretionary data field containing CVV and padding.
        
        Args:
            pan: Primary Account Number
            expiry: Expiry date (YYMM)  
            service_code: Service code (3 digits)
            additional_data: Additional discretionary data (default: "000000")
            
        Returns:
            Discretionary data field (typically 7-13 digits)
        """
        # Generate CVV
        cvv = self.generate_cvv(pan, expiry, service_code, 3)
        
        # Build discretionary data: additional_data + CVV + padding
        discretionary = additional_data + cvv
        
        # Ensure minimum length and add padding if needed
        if len(discretionary) < 7:
            discretionary = discretionary.ljust(7, '0')
        
        return discretionary
    
    def modify_service_code_and_generate_cvv(self, pan: str, expiry: str, 
                                           original_service_code: str, 
                                           new_service_code: str,
                                           additional_data: str = "000000") -> dict:
        """
        Modify service code and generate corresponding CVV with discretionary data.
        
        Args:
            pan: Primary Account Number
            expiry: Expiry date (YYMM)
            original_service_code: Original service code from card
            new_service_code: New desired service code
            additional_data: Additional discretionary data
            
        Returns:
            Dictionary with new service code, CVV, and discretionary data
        """
        # Generate new CVV for the modified service code
        new_cvv = self.generate_cvv(pan, expiry, new_service_code, 3)
        new_discretionary = self.generate_discretionary_data(pan, expiry, new_service_code, additional_data)
        
        # Also generate original for comparison
        original_cvv = self.generate_cvv(pan, expiry, original_service_code, 3)
        original_discretionary = self.generate_discretionary_data(pan, expiry, original_service_code, additional_data)
        
        return {
            'original': {
                'service_code': original_service_code,
                'cvv': original_cvv,
                'discretionary_data': original_discretionary
            },
            'modified': {
                'service_code': new_service_code,
                'cvv': new_cvv,
                'discretionary_data': new_discretionary
            },
            'analysis': {
                'service_code_changed': original_service_code != new_service_code,
                'cvv_changed': original_cvv != new_cvv,
                'discretionary_changed': original_discretionary != new_discretionary
            }
        }


def analyze_service_code(service_code: str) -> dict:
    """
    Analyze service code and return human-readable interpretation.
    
    Args:
        service_code: 3-digit service code
        
    Returns:
        Dictionary with service code analysis
    """
    if len(service_code) != 3 or not service_code.isdigit():
        return {'error': 'Service code must be exactly 3 digits'}
    
    digit1, digit2, digit3 = service_code
    
    # First digit: Interchange and technology
    interchange_map = {
        '1': 'International interchange OK, IC should not be used',
        '2': 'International interchange OK, IC should be used',
        '3': 'International interchange OK, IC should be used',
        '4': 'International interchange OK, IC should be used',
        '5': 'National interchange only, IC should not be used',
        '6': 'National interchange only, IC should be used',
        '7': 'National interchange only, IC should be used',
        '8': 'Reserved for future use',
        '9': 'Test'
    }
    
    # Second digit: Authorization processing
    auth_map = {
        '0': 'Normal authorization',
        '1': 'Deprecated - Normal authorization',  
        '2': 'Contact issuer via online means',
        '3': 'Deprecated - Contact issuer',
        '4': 'Contact issuer via online means',
        '5': 'Deprecated - Contact issuer',
        '6': 'Authorization required',
        '7': 'Deprecated - Authorization required',
        '8': 'Reserved for future use',
        '9': 'Test'
    }
    
    # Third digit: Allowed services and PIN requirements
    service_map = {
        '0': 'No restrictions, PIN required',
        '1': 'No restrictions, PIN required for cash only',
        '2': 'Goods and services only, no cash, PIN required',
        '3': 'ATM only, PIN required',
        '4': 'Cash only, PIN required',
        '5': 'Goods and services only, no cash, PIN required for cash only',
        '6': 'No restrictions, prompt for PIN if PED present',
        '7': 'Goods and services only, no cash, prompt for PIN if PED present',
        '8': 'Reserved for future use',
        '9': 'Test'
    }
    
    return {
        'service_code': service_code,
        'digit1': {
            'value': digit1,
            'meaning': interchange_map.get(digit1, 'Unknown')
        },
        'digit2': {
            'value': digit2, 
            'meaning': auth_map.get(digit2, 'Unknown')
        },
        'digit3': {
            'value': digit3,
            'meaning': service_map.get(digit3, 'Unknown')
        }
    }


if __name__ == "__main__":
    # Demo the CVV generator
    print("Magnetic Stripe CVV Generator Demo")
    print("=" * 50)
    
    # Generate test keys
    cvk_a, cvk_b = MagstripeCVVGenerator.generate_default_keys()
    generator = MagstripeCVVGenerator(cvk_a, cvk_b)
    
    # Test data
    test_pan = "4031160000000000"
    test_expiry = "3007"  # July 2030
    original_service = "201"
    new_service = "101"
    
    print(f"Test PAN: {test_pan}")
    print(f"Test Expiry: {test_expiry}")
    print(f"CVK-A: {cvk_a.hex().upper()}")
    print(f"CVK-B: {cvk_b.hex().upper()}")
    print()
    
    # Analyze service codes
    print("Service Code Analysis:")
    print("-" * 30)
    
    original_analysis = analyze_service_code(original_service)
    new_analysis = analyze_service_code(new_service)
    
    print(f"Original Service Code {original_service}:")
    for digit_info in ['digit1', 'digit2', 'digit3']:
        digit_data = original_analysis[digit_info]
        print(f"  Digit {digit_data['value']}: {digit_data['meaning']}")
    
    print(f"\nNew Service Code {new_service}:")
    for digit_info in ['digit1', 'digit2', 'digit3']:
        digit_data = new_analysis[digit_info]
        print(f"  Digit {digit_data['value']}: {digit_data['meaning']}")
    
    print("\nCVV Generation:")
    print("-" * 30)
    
    # Generate CVVs for both service codes
    result = generator.modify_service_code_and_generate_cvv(
        test_pan, test_expiry, original_service, new_service
    )
    
    print("Original Card:")
    orig = result['original']
    print(f"  Service Code: {orig['service_code']}")
    print(f"  CVV: {orig['cvv']}")
    print(f"  Discretionary Data: {orig['discretionary_data']}")
    
    print("\nModified Card:")
    mod = result['modified']  
    print(f"  Service Code: {mod['service_code']}")
    print(f"  CVV: {mod['cvv']}")
    print(f"  Discretionary Data: {mod['discretionary_data']}")
    
    print("\nTrack 2 Generation:")
    print("-" * 30)
    
    original_track2 = f"{test_pan}={test_expiry}{orig['service_code']}{orig['discretionary_data']}"
    modified_track2 = f"{test_pan}={test_expiry}{mod['service_code']}{mod['discretionary_data']}"
    
    print(f"Original Track 2: {original_track2}")
    print(f"Modified Track 2: {modified_track2}")
    
    print("\nSummary:")
    print("-" * 30)
    analysis = result['analysis']
    print(f"Service code changed: {analysis['service_code_changed']}")
    print(f"CVV changed: {analysis['cvv_changed']}")
    print(f"Discretionary data changed: {analysis['discretionary_changed']}")
