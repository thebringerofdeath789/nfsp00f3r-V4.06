#!/usr/bin/env python3
# =====================================================================
# File: enhanced_parser.py
# Project: nfsp00f3r V4.05
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Enhanced EMV data parser with deep TLV traversal and specific
#   logic for extracting nested payment information like PAN,
#   cardholder name, and Track 2 data, even from non-standard
#   EMV record structures.
# =====================================================================

import binascii
from typing import List, Dict, Any, Optional

# Assuming tlv.py and tag_dict.py are in the same directory
from tlv import TLVNode, TLVParser
from tag_dict import get_tag_info
from magstripe_cvv_generator import MagstripeCVVGenerator, analyze_service_code

class EnhancedEMVParser:
    """
    Advanced EMV data parser designed to extract critical payment
    information by deeply traversing nested TLV structures.
    """

    def __init__(self, logger=None):
        self.logger = logger
        self.tlv_parser = TLVParser()
        
        # Initialize CVV generator for service code modification
        default_seed = b"NFSP00F3R_V405_CVV_GENERATOR_SEED"
        cvk_a, cvk_b = MagstripeCVVGenerator.generate_default_keys(default_seed)
        self.cvv_generator = MagstripeCVVGenerator(cvk_a, cvk_b)

    def parse_and_extract_payment_data(self, raw_record_data: bytes) -> Dict[str, Any]:
        """
        Parses raw record data, traverses the TLV tree, and extracts
        key payment information.

        Args:
            raw_record_data: The raw bytes read from an EMV card record.

        Returns:
            A dictionary containing all extracted payment information.
        """
        if self.logger:
            self.logger.info(f"Starting enhanced parsing on {len(raw_record_data)} bytes of record data.")

        payment_data = {
            'pan': None,
            'cardholder_name': None,
            'expiry_date': None,
            'service_code': None,
            'track2_equivalent_data': None,
            'track1_generated': None,
            'track2_formatted': None,
            'raw_tlv_tree': None,
            'parsed_tags': {}
        }

        try:
            # First, parse the raw data into a TLV tree
            tlv_tree = self.tlv_parser.parse(raw_record_data)
            payment_data['raw_tlv_tree'] = [node.to_dict() for node in tlv_tree]

            # Now, traverse the tree to find our data
            for node in tlv_tree:
                self._traverse_and_extract(node, payment_data)

        except Exception as e:
            if self.logger:
                self.logger.error(f"Enhanced parsing failed: {e}")

        # Generate Track 1 and format Track 2 for display
        self._generate_tracks(payment_data)

        return payment_data

    def modify_service_code_with_cvv(self, payment_data: Dict[str, Any], new_service_code: str) -> Dict[str, Any]:
        """
        Modify service code and generate corresponding CVV and track data.
        
        Args:
            payment_data: Existing parsed payment data
            new_service_code: New service code to apply
            
        Returns:
            Updated payment data with new service code, CVV, and tracks
        """
        if not payment_data.get('pan') or not payment_data.get('expiry_date'):
            raise ValueError("Payment data must include PAN and expiry date for CVV generation")
        
        pan = payment_data['pan']
        expiry = payment_data['expiry_date']
        
        # Generate enhanced CVV using card-specific salt
        salt = f"SC{new_service_code}_PAN{pan[-4:]}_EXP{expiry}"
        enhanced_seed = b"NFSP00F3R_V405_CVV_GENERATOR_SEED" + salt.encode('ascii')
        
        # Create card-specific CVV generator
        cvk_a, cvk_b = MagstripeCVVGenerator.generate_default_keys(enhanced_seed)
        card_generator = MagstripeCVVGenerator(cvk_a, cvk_b)
        
        # Generate new CVV
        new_cvv = card_generator.generate_cvv(pan, expiry, new_service_code, 3)
        
        # Generate new discretionary data
        new_discretionary = card_generator.generate_discretionary_data(
            pan, expiry, new_service_code, "000000"
        )
        
        # Replace CVV in discretionary data with our generated CVV
        if len(new_discretionary) >= 9:
            new_discretionary = new_discretionary[:-3] + new_cvv
        else:
            new_discretionary = f"000000{new_cvv}"
        
        # Update payment data
        updated_data = payment_data.copy()
        updated_data['service_code'] = new_service_code
        updated_data['cvv'] = new_cvv
        
        # Update track data
        if updated_data.get('track2_equivalent_data'):
            updated_data['track2_equivalent_data']['service_code'] = new_service_code
            updated_data['track2_equivalent_data']['discretionary_data'] = new_discretionary
            updated_data['track2_equivalent_data']['cvv'] = new_cvv
        
        # Generate new tracks
        cardholder_name = updated_data.get('cardholder_name', 'CARDHOLDER')
        if cardholder_name:
            formatted_name = cardholder_name.replace('/', ' ').replace('  ', ' ').strip()
            updated_data['track1_generated'] = f"%B{pan}^{formatted_name}^{expiry}{new_service_code}000000000?"
        
        updated_data['track2_generated'] = f"{pan}={expiry}{new_service_code}{new_discretionary}"
        
        # Add service code analysis
        updated_data['service_code_analysis'] = analyze_service_code(new_service_code)
        
        if self.logger:
            self.logger.info(f"Modified service code to {new_service_code}, generated CVV: {new_cvv}")
        
        return updated_data
    
    def get_service_code_options(self, payment_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Get available service code modification options and their implications.
        
        Args:
            payment_data: Existing parsed payment data
            
        Returns:
            Dictionary of service code options with analysis
        """
        current_service = payment_data.get('service_code', '201')
        
        # Common service code options
        options = {
            '101': 'International, IC not used, PIN for cash only',
            '121': 'International, IC not used, PIN for cash only', 
            '201': 'International, IC preferred, PIN for cash only',
            '221': 'International, IC preferred, PIN for cash only',
            '301': 'International, IC preferred, PIN for cash only',
            '601': 'National only, IC preferred, PIN for cash only'
        }
        
        result = {
            'current_service_code': current_service,
            'current_analysis': analyze_service_code(current_service),
            'available_options': {}
        }
        
        for service_code, description in options.items():
            analysis = analyze_service_code(service_code)
            
            result['available_options'][service_code] = {
                'description': description,
                'analysis': analysis,
                'changes_from_current': self._compare_service_codes(
                    result['current_analysis'], analysis
                )
            }
        
        return result
    
    def _compare_service_codes(self, original: Dict[str, Any], new: Dict[str, Any]) -> Dict[str, str]:
        """Compare two service code analyses and return differences."""
        changes = {}
        
        if 'error' in original or 'error' in new:
            return {'error': 'Invalid service code for comparison'}
        
        # Compare each digit
        for digit in ['digit1', 'digit2', 'digit3']:
            orig_val = original[digit]['value']
            new_val = new[digit]['value']
            
            if orig_val != new_val:
                changes[digit] = {
                    'from': original[digit]['meaning'],
                    'to': new[digit]['meaning']
                }
        
        return changes

    def _generate_tracks(self, payment_data: Dict[str, Any]):
        """
        Generate Track 1 from parsed data and format Track 2 for display.
        """
        if self.logger:
            self.logger.info(f"Track generation - PAN: {payment_data.get('pan')}, Name: {payment_data.get('cardholder_name')}, Expiry: {payment_data.get('expiry_date')}, Service: {payment_data.get('service_code')}")
        
        # Generate Track 1 if we have the required data
        if (payment_data.get('pan') and 
            payment_data.get('cardholder_name') and 
            payment_data.get('expiry_date') and 
            payment_data.get('service_code')):
            
            payment_data['track1_generated'] = self._generate_track1(
                payment_data['pan'],
                payment_data['cardholder_name'],
                payment_data['expiry_date'],
                payment_data['service_code']
            )
            if self.logger:
                self.logger.info(f"Generated Track1: {payment_data['track1_generated']}")

        # Generate Track 2 if we have PAN, expiry, and service code (even without Track 2 equivalent data)
        if (payment_data.get('pan') and 
            payment_data.get('expiry_date') and 
            payment_data.get('service_code')):
            
            # Create synthetic Track 2 data
            pan = payment_data['pan']
            expiry = payment_data['expiry_date']
            service_code = payment_data['service_code']
            
            # Convert YYYYMM to YYMM if needed
            if len(expiry) == 6:
                yymm = expiry[2:6]  # Take YY and MM
            elif len(expiry) == 4:
                yymm = expiry  # Already YYMM or MMYY
            else:
                yymm = expiry[-4:]  # Take last 4 digits
            
            # Generate synthetic Track 2 format: PAN=YYMM+ServiceCode+DiscretionaryData
            discretionary = "000000000"  # Placeholder discretionary data
            payment_data['track2_formatted'] = f"{pan}={yymm}{service_code}{discretionary}"
            
            if self.logger:
                self.logger.info(f"Generated Track2: {payment_data['track2_formatted']}")

        # Format Track 2 for display if we have track2_equivalent_data
        if payment_data.get('track2_equivalent_data'):
            track2_data = payment_data['track2_equivalent_data']
            payment_data['track2_formatted'] = f"{track2_data['pan']}={track2_data['expiry_date']}{track2_data['service_code']}{track2_data['discretionary_data']}"
        # Remove stray '0' that was accidentally inserted
    def _traverse_and_extract(self, node: TLVNode, payment_data: Dict[str, Any]):
        """
        Recursively traverses a TLVNode and its children, extracting
        payment information based on known EMV tags.
        """
        # Get tag information for context
        tag_info = get_tag_info(node.tag)
        tag_desc = tag_info.get('desc', 'Unknown Tag')
        payment_data['parsed_tags'][node.tag] = {
            'desc': tag_desc,
            'value': node.value.hex().upper()
        }

        # --- Direct Data Extraction ---
        if node.tag == '5A':  # Primary Account Number (PAN)
            payment_data['pan'] = node.value.hex().rstrip('Ff')
            if self.logger:
                self.logger.info(f"Found PAN in tag 5A: {payment_data['pan']}")
        elif node.tag == '5F20':  # Cardholder Name
            try:
                payment_data['cardholder_name'] = node.value.decode('utf-8').strip()
            except UnicodeDecodeError:
                payment_data['cardholder_name'] = repr(node.value)
            if self.logger:
                self.logger.info(f"Found Name in tag 5F20: {payment_data['cardholder_name']}")
        elif node.tag == '5F24':  # Application Expiry Date (YYMMDD)
            payment_data['expiry_date'] = node.value.hex()
            if self.logger:
                self.logger.info(f"Found Expiry in tag 5F24: {payment_data['expiry_date']}")
        elif node.tag == '5F30':  # Service Code
            payment_data['service_code'] = node.value.hex()
            if self.logger:
                self.logger.info(f"Found Service Code in tag 5F30: {payment_data['service_code']}")
        elif node.tag == '57':  # Track 2 Equivalent Data
            track2_hex = node.value.hex()
            payment_data['track2_equivalent_data'] = self._parse_track2(track2_hex)
            # Also extract PAN and expiry from Track 2 if not found elsewhere
            if not payment_data['pan'] and payment_data['track2_equivalent_data']:
                payment_data['pan'] = payment_data['track2_equivalent_data'].get('pan')
            if not payment_data['expiry_date'] and payment_data['track2_equivalent_data']:
                payment_data['expiry_date'] = payment_data['track2_equivalent_data'].get('expiry_date')
            # Extract Service Code and CVV from Track 2 if not found elsewhere
            if not payment_data.get('service_code') and payment_data['track2_equivalent_data']:
                payment_data['service_code'] = payment_data['track2_equivalent_data'].get('service_code')
                if self.logger:
                    self.logger.info(f"Extracted Service Code from Track 2: {payment_data['service_code']}")
            if not payment_data.get('cvv') and payment_data['track2_equivalent_data']:
                cvv = payment_data['track2_equivalent_data'].get('cvv')
                if cvv:
                    payment_data['cvv'] = cvv
                    if self.logger:
                        self.logger.info(f"Extracted CVV from Track 2: {payment_data['cvv']}")


        # --- Recursive Traversal for Nested Data ---
        # If the node is constructed, it might contain other TLV objects.
        # This is common for tags like '70' (EMV Proprietary Template) or '77' (Response Message Template).
        if node.is_constructed() and node.children:
            if self.logger:
                self.logger.info(f"Traversing constructed tag {node.tag} ({tag_desc}) with {len(node.children)} children.")
            for child in node.children:
                self._traverse_and_extract(child, payment_data)

    def _parse_track2(self, track2_hex: str) -> Optional[Dict[str, str]]:
        """
        Parses Track 2 Equivalent Data.
        Format: PAN=ExpiryDateServiceCodeDiscretionaryData
        """
        try:
            hex_up = track2_hex.upper()
            track2_str = hex_up.replace('D', '=').rstrip('F')
            parts = track2_str.split('=')
            if len(parts) < 2:
                return None

            pan = parts[0]
            expiry_date = parts[1][:4]
            service_code = parts[1][4:7] if len(parts[1]) >= 7 else '000'
            discretionary_data = parts[1][7:] if len(parts[1]) > 7 else ''
            
            # Extract CVV from discretionary data
            cvv = self._extract_cvv_from_discretionary(discretionary_data)

            result = {
                'pan': pan,
                'expiry_date': expiry_date,
                'service_code': service_code,
                'discretionary_data': discretionary_data,
                'full_track': track2_str
            }
            
            if cvv:
                result['cvv'] = cvv
                
            return result
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not parse Track 2 data '{track2_hex}': {e}")
            return None

    def _extract_cvv_from_discretionary(self, discretionary: str) -> Optional[str]:
        """
        Extract CVV from discretionary data.
        CVV is typically the first 3 non-zero digits in the discretionary data.
        """
        if not discretionary or len(discretionary) < 3:
            return None
            
        try:
            # Remove padding zeros and look for CVV
            clean_data = discretionary.lstrip('0')
            if len(clean_data) >= 3:
                # CVV is typically first 3 digits after removing leading zeros
                potential_cvv = clean_data[:3]
                # Make sure it's all digits and not all zeros
                if potential_cvv.isdigit() and potential_cvv != '000':
                    if self.logger:
                        self.logger.info(f"Extracted CVV from discretionary data: {potential_cvv}")
                    return potential_cvv
                    
            # Alternative: look for 3-digit sequences that could be CVV
            import re
            cvv_pattern = re.findall(r'(\d{3})', discretionary)
            for potential in cvv_pattern:
                if potential != '000' and potential != '999':  # Skip obvious padding
                    if self.logger:
                        self.logger.info(f"Found potential CVV in discretionary: {potential}")
                    return potential
                    
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Error extracting CVV from discretionary '{discretionary}': {e}")
                
        return None

    def _generate_track1(self, pan: str, name: str, expiry: str, service_code: str) -> str:
        """
        Generate Track 1 from parsed EMV data.
        Format: %B{PAN}^{Name}^{YYMM}{Service Code}{Discretionary Data}?
        """
        try:
            # Format name (remove slashes, limit to 26 chars, pad with spaces)
            formatted_name = name.replace('/', ' ').strip()[:26].ljust(26)
            
            # Use YYMM from expiry (convert MMYY to YYMM if needed)
            if len(expiry) == 4:
                if expiry[:2] > '12':  # Likely YYMM format
                    yymm = expiry
                else:  # Likely MMYY format
                    yymm = expiry[2:] + expiry[:2]
            else:
                yymm = expiry[-4:]  # Take last 4 digits
            
            # Generate Track 1 with discretionary data (we'll use 000000000 as placeholder)
            track1 = f"%B{pan}^{formatted_name}^{yymm}{service_code}000000000?"
            
            return track1
            
        except Exception as e:
            if self.logger:
                self.logger.warning(f"Could not generate Track 1: {e}")
            return f"%B{pan}^{name}^{expiry}{service_code}000000000?"

# Example usage for testing
if __name__ == '__main__':
    import logging
    import json
    import re

    logging.basicConfig(level=logging.INFO)
    logger = logging.getLogger(__name__)

    # Example data from a real card read. If this line ever gets corrupted by copy/paste,
    # the sanitization below will remove any non-hex characters before decoding.
    # A compact, valid EMV TLV payload under tag '70' (constructed):
    # Real data from the live card: 70 + length + nested TLVs
    test_data_hex = (
        "701E"  # Tag 70, length 30 bytes
        "9F470103"  # 9F47 tag (1 byte), value 03
        "5A08" "4031160000000000"  # PAN tag (8 bytes)
        "5F2403" "300731"  # Expiry Date tag (3 bytes) 
        "9F690701000000000000"  # 9F69 tag (7 bytes)
    )

    # Sanitize: keep only hex digits; log what we removed (if anything)
    original = test_data_hex
    cleaned = re.sub(r"[^0-9A-Fa-f]", "", original)
    if cleaned != original:
        removed = [(i, ch) for i, ch in enumerate(original) if ch not in "0123456789abcdefABCDEF"]
        logger.warning(f"Sanitized input by removing non-hex characters at positions: {removed}")

    # Ensure even length (bytes.fromhex requires pairs of hex nibbles)
    if len(cleaned) % 2 != 0:
        logger.warning("Odd-length hex string after sanitization; dropping last nibble")
        cleaned = cleaned[:-1]

    try:
        test_data_bytes = bytes.fromhex(cleaned)

        parser = EnhancedEMVParser(logger=logger)
        extracted_data = parser.parse_and_extract_payment_data(test_data_bytes)

        print("\n--- Enhanced Parsing Results ---")
        print(json.dumps(extracted_data, indent=4))

        print("\n--- Key Information ---")
        print(f"PAN: {extracted_data.get('pan')}")
        print(f"Cardholder Name: {extracted_data.get('cardholder_name')}")
        print(f"Expiry Date: {extracted_data.get('expiry_date')}")
        if extracted_data.get('track2_equivalent_data'):
            print("Track 2 Data Found and Parsed.")

    except ValueError as e:
        logger.error(
            "CRITICAL ERROR: Failed to decode hex string. Check for invalid characters. Details: %s",
            e,
        )
        # Report any non-hex characters in the ORIGINAL string to help pinpoint issues
        bads = [(i, ch) for i, ch in enumerate(original) if ch not in "0123456789abcdefABCDEF"]
        if bads:
            logger.error(f"Non-hex characters detected in original input: {bads}")
        logger.error(f"Original length: {len(original)}, Cleaned length: {len(cleaned)}")
    except Exception as e:
        logger.error(f"An unexpected error occurred during parsing: {e}")
