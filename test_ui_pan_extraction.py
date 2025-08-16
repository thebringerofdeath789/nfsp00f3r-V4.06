#!/usr/bin/env python3
"""
Test UI PAN Extraction
Tests the UI's PAN extraction functionality with real card data.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from advanced_card_manager import CardDataExtractor

def test_ui_pan_extraction():
    """Test UI PAN extraction with user's real card data"""
    
    print("🎯 Testing UI PAN Extraction with Real Card Data")
    print("=" * 70)
    
    # Initialize card data extractor (same as UI uses)
    extractor = CardDataExtractor()
    
    print("📋 SIMULATING DIFFERENT DATA SOURCES:")
    print()
    
    # Test 1: Real card data from TLV (how EMV cards work)
    print("🔍 TEST 1: TLV Data Extraction (EMV Standard)")
    tlv_card_data = {
        "tlv_data": {
            "5A": "4031160000000000",  # Application PAN - USER'S REAL PAN
            "5F20": "4A4F484E20444F45",  # Cardholder Name
            "5F24": "251201",  # Application Expiry Date
        },
        "pin": "6998"  # USER'S REAL PIN
    }
    
    pan_from_tlv = extractor._extract_real_pan(tlv_card_data)
    print(f"   Extracted PAN: {pan_from_tlv}")
    print(f"   Expected: 4031160000000000 (USER'S REAL CARD)")
    print(f"   ✅ Match: {'YES' if pan_from_tlv == '4031160000000000' else 'NO'}")
    print()
    
    # Test 2: Track2 data extraction  
    print("🔍 TEST 2: Track2 Data Extraction")
    track2_card_data = {
        "track2": "4031160000000000=25121019999999999?",  # USER'S REAL PAN in track2
        "pin": "6998"
    }
    
    pan_from_track2 = extractor._extract_real_pan(track2_card_data)
    print(f"   Extracted PAN: {pan_from_track2}")
    print(f"   Expected: 4031160000000000 (USER'S REAL CARD)")
    print(f"   ✅ Match: {'YES' if pan_from_track2 == '4031160000000000' else 'NO'}")
    print()
    
    # Test 3: Track1 data extraction
    print("🔍 TEST 3: Track1 Data Extraction")
    track1_card_data = {
        "track1": "%B4031160000000000^HOLDER/CARD^29081019999999999999?",  # USER'S REAL PAN in track1
        "pin": "6998"
    }
    
    pan_from_track1 = extractor._extract_real_pan(track1_card_data)
    print(f"   Extracted PAN: {pan_from_track1}")
    print(f"   Expected: 4031160000000000 (USER'S REAL CARD)")
    print(f"   ✅ Match: {'YES' if pan_from_track1 == '4031160000000000' else 'NO'}")
    print()
    
    # Test 4: Direct PAN field
    print("🔍 TEST 4: Direct PAN Field")
    direct_card_data = {
        "pan": "4031160000000000",  # USER'S REAL PAN directly
        "pin": "6998"
    }
    
    pan_from_direct = extractor._extract_real_pan(direct_card_data)
    print(f"   Extracted PAN: {pan_from_direct}")
    print(f"   Expected: 4031160000000000 (USER'S REAL CARD)")
    print(f"   ✅ Match: {'YES' if pan_from_direct == '4031160000000000' else 'NO'}")
    print()
    
    # Test 5: Empty/No data (should return NO_REAL_PAN_DETECTED)
    print("🔍 TEST 5: No Card Data (Expected Behavior)")
    empty_card_data = {}
    
    pan_from_empty = extractor._extract_real_pan(empty_card_data)
    print(f"   Extracted PAN: {pan_from_empty}")
    print(f"   Expected: NO_REAL_PAN_DETECTED")
    print(f"   ✅ Correct: {'YES' if pan_from_empty == 'NO_REAL_PAN_DETECTED' else 'NO'}")
    print()
    
    # Test 6: Test PAN with filtered sample/test cards
    print("🔍 TEST 6: Sample Card Filtering (Should be rejected)")
    sample_card_data = {
        "pan": "4111111111111111",  # Common test card - should be rejected
        "pin": "1234"
    }
    
    pan_from_sample = extractor._extract_real_pan(sample_card_data)
    print(f"   Extracted PAN: {pan_from_sample}")
    print(f"   Expected: NO_REAL_PAN_DETECTED (filtered out)")
    print(f"   ✅ Filtered: {'YES' if pan_from_sample == 'NO_REAL_PAN_DETECTED' else 'NO'}")
    print()
    
    # Test 7: Complete card data extraction with real PAN
    print("🔍 TEST 7: Complete Card Data Extraction")
    complete_card_data = {
        "pan": "4031160000000000",  # USER'S REAL PAN
        "cardholder_name": "JOHN DOE",
        "expiry": "2512",
        "pin": "6998",  # USER'S REAL PIN
        "cvv": "720",   # USER'S REAL CVV2 (from earlier)
        "tlv_data": {
            "5A": "4031160000000000",  # Confirm with TLV
        },
        "track2": "4031160000000000=25121019999999999?"
    }
    
    extracted_data = extractor.extract_complete_card_data(complete_card_data)
    basic_info = extracted_data.get('basic_info', {})
    extracted_pan = basic_info.get('pan', 'NOT_FOUND')
    
    print(f"   Extracted PAN from UI method: {extracted_pan}")
    print(f"   Expected: 4031160000000000 (USER'S REAL CARD)")
    print(f"   ✅ UI Match: {'YES' if extracted_pan == '4031160000000000' else 'NO'}")
    print()
    
    print("🎯 PAN EXTRACTION TEST SUMMARY:")
    print("=" * 70)
    
    tests_results = [
        ("TLV Extraction", pan_from_tlv == "4031160000000000"),
        ("Track2 Extraction", pan_from_track2 == "4031160000000000"), 
        ("Track1 Extraction", pan_from_track1 == "4031160000000000"),
        ("Direct PAN Extraction", pan_from_direct == "4031160000000000"),
        ("Empty Data Handling", pan_from_empty == "NO_REAL_PAN_DETECTED"),
        ("Sample Card Filtering", pan_from_sample == "NO_REAL_PAN_DETECTED"),
        ("UI Complete Extraction", extracted_pan == "4031160000000000")
    ]
    
    passed = sum(1 for _, result in tests_results if result)
    total = len(tests_results)
    
    for test_name, result in tests_results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"   {test_name}: {status}")
    
    print()
    print(f"📊 OVERALL RESULT: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL PAN EXTRACTION TESTS PASSED!")
        print("✅ UI will display USER'S REAL PAN: 4031160000000000")
    else:
        print("⚠️  Some tests failed - PAN extraction needs attention")
    
    print("=" * 70)

if __name__ == "__main__":
    test_ui_pan_extraction()
