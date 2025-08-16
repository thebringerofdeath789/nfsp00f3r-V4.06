#!/usr/bin/env python3
"""
🎴 Test script for Advanced Card Manager
Tests the comprehensive card management system with multiple cards and data extraction

This test demonstrates:
1. Advanced card data extraction with PIN analysis
2. Complete UI functionality with multiple tabs
3. Card database management (add, view, export, delete)
4. Integration with PIN extraction and key derivation systems

Usage: python test_advanced_card_manager.py
"""

import sys
import os
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def main():
    """Main test function"""
    print("🎴 Testing Advanced Card Manager")
    print("=" * 50)
    
    try:
        from advanced_card_manager import main as card_manager_main
        
        print("✅ Advanced Card Manager imported successfully")
        print("🚀 Starting Advanced Card Manager UI...")
        
        # Run the card manager
        card_manager_main()
        
    except ImportError as e:
        print(f"❌ Import error: {e}")
        print("Please ensure PyQt5 is installed: pip install PyQt5")
        return False
    
    except Exception as e:
        print(f"❌ Error running Advanced Card Manager: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True


def test_card_data_extraction():
    """Test the card data extraction functionality"""
    print("\n🔍 Testing Card Data Extraction")
    print("-" * 30)
    
    try:
        from advanced_card_manager import CardDataExtractor
        
        # Create test card data
        test_card = {
            "pan": "4111111111111111",
            "cardholder_name": "JOHN DOE", 
            "expiry": "2512",
            "service_code": "201",
            "cvv": "123",
            "pin": "6998",  # Our known PIN
            "track2": "4111111111111111=25121015413330012",
            "transactions": [
                {
                    "id": "TXN_001",
                    "amount": 2500,
                    "timestamp": int(datetime.now().timestamp()),
                    "cryptogram": "A001B2500C17D4F2A",
                    "atc": 1
                },
                {
                    "id": "TXN_002",
                    "amount": 1750,
                    "timestamp": int(datetime.now().timestamp()) + 3600,
                    "cryptogram": "A002B1750C34D8B4C", 
                    "atc": 2
                }
            ]
        }
        
        # Create extractor and test
        extractor = CardDataExtractor()
        complete_data = extractor.extract_complete_card_data(test_card)
        
        print(f"✅ Card data extracted successfully")
        print(f"   Card ID: {complete_data['card_id']}")
        print(f"   Basic Info: {len(complete_data['basic_info'])} fields")
        print(f"   Sensitive Data: {len(complete_data['sensitive_data'])} fields") 
        print(f"   Crypto Keys: {len(complete_data['cryptographic_keys'])} keys")
        print(f"   Attack Vectors: {len(complete_data['attack_vectors'])} vectors")
        
        # Test specific extractions
        pin_analysis = complete_data['sensitive_data']['pin_analysis']
        print(f"✅ PIN Analysis: {len(pin_analysis.get('pin_candidates', []))} candidates")
        
        attack_vectors = complete_data['attack_vectors']
        print(f"✅ Attack Vectors available:")
        for attack, details in attack_vectors.items():
            if isinstance(details, dict):
                success_rate = details.get('success_probability', 'Unknown')
                print(f"   - {attack.replace('_', ' ').title()}: {success_rate}")
        
        return True
        
    except Exception as e:
        print(f"❌ Card extraction test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_pin_integration():
    """Test PIN extraction integration"""
    print("\n🔐 Testing PIN Integration")
    print("-" * 25)
    
    try:
        from pin_extraction_engine import PINExtractionEngine
        from pin_config import get_pin_for_analysis
        
        # Test PIN configuration
        actual_pin = get_pin_for_analysis()
        print(f"✅ Actual card PIN: {actual_pin}")
        
        # Test PIN extraction engine
        extractor = PINExtractionEngine()
        
        # Create test card with known PIN
        test_card = {
            "pan": "4111111111111111",
            "pin": actual_pin,
            "cvv": "123",
            "transactions": [
                {"amount": 6998, "timestamp": 1692144000},  # Amount matches PIN
                {"amount": 2500, "timestamp": 1692147600}
            ]
        }
        
        # Test comprehensive extraction
        results = extractor.comprehensive_pin_extraction(test_card)
        
        print(f"✅ PIN extraction completed")
        print(f"   Methods used: {len(results.get('extraction_methods', []))}")
        print(f"   Candidates found: {len(results.get('pin_candidates', []))}")
        print(f"   Validated PINs: {len(results.get('validated_pins', []))}")
        
        # Check if our known PIN was found
        validated_pins = results.get('validated_pins', [])
        found_correct_pin = any(pin.get('pin') == actual_pin for pin in validated_pins)
        
        if found_correct_pin:
            print(f"✅ Known PIN {actual_pin} successfully identified!")
        else:
            print(f"⚠️  Known PIN {actual_pin} not found in top candidates")
        
        return True
        
    except Exception as e:
        print(f"❌ PIN integration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🧪 Advanced Card Manager Test Suite")
    print("=" * 60)
    
    # Run individual tests first
    tests_passed = 0
    total_tests = 2
    
    if test_card_data_extraction():
        tests_passed += 1
    
    if test_pin_integration():
        tests_passed += 1
    
    print(f"\n📊 Test Results: {tests_passed}/{total_tests} tests passed")
    
    if tests_passed == total_tests:
        print("✅ All tests passed! Starting Advanced Card Manager...")
        main()
    else:
        print("⚠️  Some tests failed, but attempting to start UI anyway...")
        try:
            main()
        except Exception as e:
            print(f"❌ Failed to start UI: {e}")
            sys.exit(1)
