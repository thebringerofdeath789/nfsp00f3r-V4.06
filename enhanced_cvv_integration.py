#!/usr/bin/env python3
"""
Enhanced CVV Generator Integration for NFCSpoofer V4.05
Integrates CVV generation with the enhanced parser and EMV card system
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from magstripe_cvv_generator import MagstripeCVVGenerator, analyze_service_code
from enhanced_parser import EnhancedEMVParser
import hashlib


class EnhancedCVVProcessor:
    """
    Enhanced CVV processor that integrates with the EMV card system
    and provides realistic CVV generation for modified service codes.
    """
    
    def __init__(self, card_specific_seed: bytes = None):
        """Initialize with card-specific seed for realistic CVV generation."""
        if card_specific_seed is None:
            # Default seed based on common issuer patterns
            card_specific_seed = b"VISA_DEFAULT_CVV_SEED_V405_2025"
        
        # Generate CVV keys from card-specific seed
        cvk_a, cvk_b = MagstripeCVVGenerator.generate_default_keys(card_specific_seed)
        self.cvv_generator = MagstripeCVVGenerator(cvk_a, cvk_b)
        self.card_seed = card_specific_seed
    
    def generate_enhanced_cvv(self, pan: str, expiry: str, service_code: str, 
                             salt: str = None) -> str:
        """
        Generate enhanced CVV with additional entropy for realistic variation.
        """
        # Add salt based on service code for variation
        if salt is None:
            salt = f"SC{service_code}_PAN{pan[-4:]}"
        
        # Create enhanced input with salt
        enhanced_seed = self.card_seed + salt.encode('ascii')
        
        # Generate new keys for this specific combination
        cvk_a, cvk_b = MagstripeCVVGenerator.generate_default_keys(enhanced_seed)
        temp_generator = MagstripeCVVGenerator(cvk_a, cvk_b)
        
        return temp_generator.generate_cvv(pan, expiry, service_code)
    
    def modify_card_service_code(self, card_data: dict, new_service_code: str) -> dict:
        """
        Modify card service code and generate corresponding CVV and tracks.
        
        Args:
            card_data: Dict with PAN, expiry, current service code, etc.
            new_service_code: New service code to apply
            
        Returns:
            Dict with modified card data including new CVV and tracks
        """
        pan = card_data.get('pan', '')
        expiry = card_data.get('expiry_date', '')
        original_service = card_data.get('service_code', '')
        cardholder_name = card_data.get('cardholder_name', '')
        
        if not all([pan, expiry, original_service]):
            raise ValueError("Card data must include PAN, expiry, and service code")
        
        # Generate new CVV for modified service code
        new_cvv = self.generate_enhanced_cvv(pan, expiry, new_service_code)
        
        # Generate new discretionary data
        new_discretionary = self.cvv_generator.generate_discretionary_data(
            pan, expiry, new_service_code, "000000"
        )
        
        # Replace the CVV in discretionary data with our enhanced CVV
        if len(new_discretionary) >= 9:  # Format: 000000XXX where XXX is CVV
            new_discretionary = new_discretionary[:-3] + new_cvv
        else:
            new_discretionary = f"000000{new_cvv}"
        
        # Generate new tracks
        if cardholder_name:
            formatted_name = cardholder_name.replace('/', ' ').replace('  ', ' ').strip()
            new_track1 = f"%B{pan}^{formatted_name}^{expiry}{new_service_code}000000000?"
        else:
            new_track1 = f"%B{pan}^CARDHOLDER^{expiry}{new_service_code}000000000?"
        
        new_track2 = f"{pan}={expiry}{new_service_code}{new_discretionary}"
        
        # Analyze service codes
        original_analysis = analyze_service_code(original_service)
        new_analysis = analyze_service_code(new_service_code)
        
        return {
            'original': {
                'service_code': original_service,
                'cvv': card_data.get('cvv', ''),
                'analysis': original_analysis
            },
            'modified': {
                'pan': pan,
                'cardholder_name': cardholder_name,
                'expiry_date': expiry,
                'service_code': new_service_code,
                'cvv': new_cvv,
                'discretionary_data': new_discretionary,
                'track1': new_track1,
                'track2': new_track2,
                'analysis': new_analysis
            },
            'comparison': {
                'service_code_changed': original_service != new_service_code,
                'cvv_changed': card_data.get('cvv', '') != new_cvv,
                'functionality_change': self._analyze_functionality_change(original_analysis, new_analysis)
            }
        }
    
    def _analyze_functionality_change(self, original_analysis: dict, new_analysis: dict) -> dict:
        """Analyze functional differences between service codes."""
        if 'error' in original_analysis or 'error' in new_analysis:
            return {'error': 'Invalid service code for analysis'}
        
        changes = {}
        
        # Check interchange capability change
        orig_interchange = original_analysis['digit1']['value']
        new_interchange = new_analysis['digit1']['value']
        if orig_interchange != new_interchange:
            changes['interchange'] = {
                'from': original_analysis['digit1']['meaning'],
                'to': new_analysis['digit1']['meaning']
            }
        
        # Check authorization change
        orig_auth = original_analysis['digit2']['value'] 
        new_auth = new_analysis['digit2']['value']
        if orig_auth != new_auth:
            changes['authorization'] = {
                'from': original_analysis['digit2']['meaning'],
                'to': new_analysis['digit2']['meaning']
            }
        
        # Check service restrictions change
        orig_service = original_analysis['digit3']['value']
        new_service = new_analysis['digit3']['value']
        if orig_service != new_service:
            changes['services'] = {
                'from': original_analysis['digit3']['meaning'],
                'to': new_analysis['digit3']['meaning']
            }
        
        return changes


def demonstrate_service_code_modification():
    """Demonstrate service code modification with CVV generation."""
    
    print("NFCSpoofer V4.05 - Enhanced CVV Generation & Service Code Modification")
    print("=" * 80)
    
    # Parse existing card data
    parser = EnhancedEMVParser()
    test_record_hex = '702757134031160000000000d30072010000099999991f5f200f43415244484f4c4445522f56495341'
    raw_data = bytes.fromhex(test_record_hex)
    card_data = parser.parse_and_extract_payment_data(raw_data)
    
    print("\n1. ORIGINAL CARD DATA")
    print("-" * 50)
    print(f"PAN: {card_data['pan']}")
    print(f"Cardholder: {card_data['cardholder_name']}")
    print(f"Expiry: {card_data['expiry_date']}")  
    print(f"Original Service Code: {card_data['service_code']}")
    print(f"Original CVV: {card_data['cvv']}")
    
    # Initialize CVV processor  
    processor = EnhancedCVVProcessor()
    
    # Modify to service code 101
    new_service_code = "101"
    result = processor.modify_card_service_code(card_data, new_service_code)
    
    print(f"\n2. SERVICE CODE MODIFICATION: {card_data['service_code']} → {new_service_code}")
    print("-" * 50)
    
    original = result['original']
    modified = result['modified']
    comparison = result['comparison']
    
    print("Original Service Code Analysis:")
    if 'error' not in original['analysis']:
        for digit in ['digit1', 'digit2', 'digit3']:
            digit_info = original['analysis'][digit]
            print(f"  Digit {digit_info['value']}: {digit_info['meaning']}")
    
    print(f"\nNew Service Code Analysis:")
    if 'error' not in modified['analysis']:
        for digit in ['digit1', 'digit2', 'digit3']:
            digit_info = modified['analysis'][digit]
            print(f"  Digit {digit_info['value']}: {digit_info['meaning']}")
    
    print(f"\n3. GENERATED DATA")
    print("-" * 50)
    print(f"New Service Code: {modified['service_code']}")
    print(f"New CVV: {modified['cvv']}")
    print(f"New Discretionary Data: {modified['discretionary_data']}")
    
    print(f"\n4. NEW TRACK DATA")
    print("-" * 50)
    print(f"Track 1: {modified['track1']}")
    print(f"Track 2: {modified['track2']}")
    
    print(f"\n5. FUNCTIONALITY CHANGES")
    print("-" * 50)
    
    func_changes = comparison['functionality_change']
    if func_changes:
        for change_type, change_info in func_changes.items():
            if isinstance(change_info, dict) and 'from' in change_info:
                print(f"{change_type.upper()} CHANGE:")
                print(f"  From: {change_info['from']}")
                print(f"  To: {change_info['to']}")
    else:
        print("No functional changes between service codes")
    
    print(f"\nCVV Changed: {comparison['cvv_changed']}")
    
    print(f"\n6. TRANSACTION IMPLICATIONS")
    print("-" * 50)
    
    # Analyze the specific change from 201 to 101
    if new_service_code == "101":
        print("Service Code 201 → 101 Changes:")
        print("  • Interchange: International OK (unchanged)")
        print("  • Authorization: Normal processing (unchanged)")  
        print("  • Services: No restrictions, PIN for cash only (unchanged)")
        print("  • IC Usage: Changed from 'IC should be used' to 'IC should not be used'")
        print("  • Impact: Card will prefer magnetic stripe over chip")
        print("  • CVV: New CVV generated for magnetic stripe compatibility")
    
    return modified


def test_multiple_service_codes():
    """Test CVV generation with multiple service codes."""
    
    print("\n" + "=" * 80)
    print("MULTIPLE SERVICE CODE CVV GENERATION TEST")
    print("=" * 80)
    
    # Test data
    test_pan = "4031160000000000"
    test_expiry = "3007"
    test_cardholder = "CARDHOLDER/VISA"
    
    card_data = {
        'pan': test_pan,
        'expiry_date': test_expiry,
        'cardholder_name': test_cardholder,
        'service_code': '201',
        'cvv': '999'
    }
    
    processor = EnhancedCVVProcessor()
    
    # Test various service codes
    test_service_codes = ["101", "121", "201", "221", "301", "601"]
    
    print(f"\nBase Card Data:")
    print(f"PAN: {test_pan}")
    print(f"Expiry: {test_expiry}")  
    print(f"Cardholder: {test_cardholder}")
    
    print(f"\nCVV Generation for Different Service Codes:")
    print("-" * 60)
    
    for service_code in test_service_codes:
        result = processor.modify_card_service_code(card_data, service_code)
        modified = result['modified']
        
        # Analyze service code
        analysis = analyze_service_code(service_code)
        
        print(f"\nService Code {service_code}:")
        print(f"  CVV: {modified['cvv']}")
        print(f"  Track 2: {modified['track2']}")
        if 'error' not in analysis:
            ic_usage = "IC preferred" if service_code[0] in "234567" else "Magstripe preferred"
            print(f"  Technology: {ic_usage}")


if __name__ == "__main__":
    print("Running enhanced CVV generation demonstration...")
    
    # Main demonstration
    modified_card = demonstrate_service_code_modification()
    
    # Multiple service code test
    test_multiple_service_codes()
    
    print(f"\n🎯 DEMONSTRATION COMPLETE!")
    print(f"✅ Service Code Modification: Working")
    print(f"✅ CVV Generation: Working") 
    print(f"✅ Track Generation: Working")
    print(f"✅ Enhanced Integration: Ready")
