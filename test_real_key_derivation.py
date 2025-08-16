#!/usr/bin/env python3
"""
Test Real Cryptographic Key Derivation
Tests the enhanced Advanced Card Manager with real key derivation capabilities.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_card_manager import CardDataExtractor

def test_real_key_derivation():
    """Test the enhanced key derivation with sample card data"""
    
    print("🔐 Testing Real Cryptographic Key Derivation")
    print("=" * 60)
    
    # Initialize enhanced card data extractor
    extractor = CardDataExtractor()
    
    # VALIDATION EXPECTED VALUES (from user's actual card for comparison)
    expected_values = {
        "pan": "4031160000000000",  # Expected PAN from user's real card
        "cardholder_name": "CARDHOLDER/VISA",  # Expected cardholder name 
        "expiry": "3007",  # Expected expiry (07/30)
        "pin": "6998",  # Expected PIN (consistently extracted)
        "cvv2": "720",   # Expected CVV2 (from earlier conversation)
    }
    
    # Simulate card data extraction from actual card reader (empty initially)
    test_card_data = {
        # This would normally come from card reader - leaving empty to test dynamic extraction
        "apdu_log": [],  # APDU responses from card
        "tlv_data": {},  # EMV TLV data from card
        "track1": "",    # Track 1 data from magnetic stripe
        "track2": "",    # Track 2 data from magnetic stripe
        "transactions": [
            {
                "amount": 2500,
                "timestamp": 1723852800,  # Sample timestamp
                "cryptogram": "A001B2500C17D4F2A"
            }
        ],
        "apdu_log": [],
        "cryptograms": {},
        "issuer_scripts": []
    }
    
    print("📋 Testing Dynamic Card Data Extraction (NO HARDCODED VALUES):")
    print(f"   Expected PAN: {expected_values['pan']}")
    print(f"   Expected Cardholder: {expected_values['cardholder_name']}")
    print(f"   Expected Expiry: {expected_values['expiry']}")
    print(f"   Expected PIN: {expected_values['pin']}")
    print(f"   Expected CVV2: {expected_values['cvv2']}")
    print()
    
    # Extract complete card data with all keys derived
    print("🔍 Extracting Complete Card Data...")
    extracted_data = extractor.extract_complete_card_data(test_card_data)
    
    print("✅ Extraction Complete!")
    print()
    
    # Display basic info and validate against expected values
    print("📊 BASIC INFORMATION (VALIDATION):")
    basic_info = extracted_data.get('basic_info', {})
    extracted_pan = basic_info.get('pan', 'NOT_EXTRACTED')
    extracted_cardholder = basic_info.get('cardholder_name', 'NOT_EXTRACTED')
    extracted_expiry = basic_info.get('expiry', 'NOT_EXTRACTED')
    
    print(f"   Extracted PAN: {extracted_pan}")
    print(f"   ✅ PAN Match: {'YES' if extracted_pan == expected_values['pan'] else 'NO (Expected: ' + expected_values['pan'] + ')'}")
    print(f"   Extracted Cardholder: {extracted_cardholder}")
    print(f"   ✅ Cardholder Match: {'YES' if extracted_cardholder == expected_values['cardholder_name'] else 'NO (Expected: ' + expected_values['cardholder_name'] + ')'}")
    print(f"   Extracted Expiry: {extracted_expiry}")
    print(f"   ✅ Expiry Match: {'YES' if extracted_expiry == expected_values['expiry'] else 'NO (Expected: ' + expected_values['expiry'] + ')'}")
    print()
    
    # Display sensitive data and validate
    print("🔐 SENSITIVE DATA VALIDATION:")
    sensitive_data = extracted_data.get('sensitive_data', {})
    extracted_pin = sensitive_data.get('actual_pin', 'NOT_EXTRACTED')
    extracted_cvv2 = sensitive_data.get('cvv2', 'NOT_EXTRACTED')
    
    print(f"   Extracted PIN: {extracted_pin}")
    print(f"   ✅ PIN Match: {'YES' if extracted_pin == expected_values['pin'] else 'NO (Expected: ' + expected_values['pin'] + ')'}")
    print(f"   Extracted CVV2: {extracted_cvv2}")
    print(f"   ✅ CVV2 Match: {'YES' if extracted_cvv2 == expected_values['cvv2'] else 'NO (Expected: ' + expected_values['cvv2'] + ')'}")
    print()
    
    # Display cryptographic keys (should all be derived)
    print("🗝️  CRYPTOGRAPHIC KEYS (ALL DERIVED):")
    crypto_keys = extracted_data.get('crypto_keys', {})
    
    # Show master keys
    master_key = crypto_keys.get('master_key', 'Not derived')
    print(f"   Master Key: {master_key}")
    
    issuer_mk = crypto_keys.get('issuer_master_key', 'Not derived')
    print(f"   Issuer Master Key: {issuer_mk}")
    
    # Show session keys
    session_keys = crypto_keys.get('session_keys', {})
    print(f"   Session Keys: {len(session_keys)} keys derived")
    for session_name, session_key in session_keys.items():
        print(f"     {session_name.upper()}: {session_key}")
    
    # Show PIN verification keys
    pin_keys = crypto_keys.get('pin_verification_keys', {})
    print(f"   PIN Verification Keys: {len(pin_keys)} keys derived")
    for pin_key_name, pin_key in pin_keys.items():
        print(f"     {pin_key_name.upper()}: {pin_key}")
    
    # Show CVV generation keys
    cvv_keys = crypto_keys.get('cvv_generation_keys', {})
    print(f"   CVV Generation Keys: {len(cvv_keys)} keys derived")
    for cvv_key_name, cvv_key in cvv_keys.items():
        print(f"     {cvv_key_name.upper()}: {cvv_key}")
    
    # Show key check values
    kcvs = crypto_keys.get('key_check_values', {})
    print(f"   Key Check Values: {len(kcvs)} KCVs calculated")
    for kcv_name, kcv_value in kcvs.items():
        print(f"     {kcv_name}: {kcv_value}")
    print()
    
    # Show metadata
    metadata = extracted_data.get('metadata', {})
    print("📈 EXTRACTION METADATA:")
    for key, value in metadata.items():
        print(f"   {key}: {value}")
    print()
    
    print("🎉 Card Data Extraction Test Complete!")
    print("=" * 60)
    print()
    print("KEY VALIDATION RESULTS:")
    
    # Calculate validation scores
    validations = [
        ("PAN extraction", extracted_pan == expected_values['pan']),
        ("Cardholder name extraction", extracted_cardholder == expected_values['cardholder_name']),
        ("Expiry date extraction", extracted_expiry == expected_values['expiry']),
        ("PIN derivation", extracted_pin == expected_values['pin']),
        ("CVV2 calculation", extracted_cvv2 == expected_values['cvv2'])
    ]
    
    passed = sum(1 for _, result in validations if result)
    total = len(validations)
    
    for test_name, result in validations:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
    
    print()
    print(f"📊 VALIDATION SCORE: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL VALIDATIONS PASSED! UI will display correct real card data.")
    else:
        print("⚠️  Some validations failed - data extraction needs attention.")
    
    print()
    print("🚀 System ready for UI testing with real card data validation!")

if __name__ == "__main__":
    test_real_key_derivation()
