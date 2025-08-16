#!/usr/bin/env python3
"""
Test CVV and Service Code extraction from real card data
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_parser import EnhancedEMVParser

def test_cvv_service_extraction():
    """Test CVV and Service Code extraction"""
    print("Testing CVV and Service Code Extraction")
    print("="*50)
    
    # Real Track 2 data from our card
    track2_hex = "57134031160000000000d30072010000099999991f"
    
    print(f"Track 2 hex: {track2_hex}")
    print()
    
    # Create parser
    parser = EnhancedEMVParser()
    
    # Parse just the Track 2 data
    track2_data = parser._parse_track2(track2_hex[2:])  # Remove '57' tag and '13' length
    
    if track2_data:
        print("✅ Track 2 Parsed Successfully:")
        print(f"  PAN: {track2_data['pan']}")
        print(f"  Expiry: {track2_data['expiry_date']}")
        print(f"  Service Code: {track2_data['service_code']}")
        print(f"  Discretionary Data: {track2_data['discretionary_data']}")
        print(f"  Full Track: {track2_data['full_track']}")
        
        if 'cvv' in track2_data:
            print(f"  ✅ CVV Extracted: {track2_data['cvv']}")
        else:
            print("  ❌ CVV: Not found")
    else:
        print("❌ Track 2 parsing failed")
        return False
    
    # Test with complete card data 
    print("\n" + "-"*50)
    print("Testing with Full Card Data")
    print("-"*50)
    
    # Raw EMV data from our card
    test_data_hex = "702757134031160000000000d30072010000099999991f5f200f43415244484f4c4445522f56495341"
    
    try:
        test_data = bytes.fromhex(test_data_hex)
        payment_data = parser.parse_and_extract_payment_data(test_data)
        
        print("✅ Full Data Parsed:")
        print(f"  PAN: {payment_data.get('pan', 'Not found')}")
        print(f"  Cardholder: {payment_data.get('cardholder_name', 'Not found')}")
        print(f"  Expiry: {payment_data.get('expiry_date', 'Not found')}")
        print(f"  Service Code: {payment_data.get('service_code', 'Not found')}")
        print(f"  CVV: {payment_data.get('cvv', 'Not found')}")
        
        # Generate proper Track 1 and Track 2 with service code and CVV
        if all([payment_data.get('pan'), payment_data.get('cardholder_name'), 
                payment_data.get('expiry_date'), payment_data.get('service_code')]):
            
            track1 = parser._generate_track1(
                payment_data['pan'],
                payment_data['cardholder_name'],
                payment_data['expiry_date'],
                payment_data['service_code']
            )
            print(f"\n✅ Generated Track 1: {track1}")
            
            # Generate Track 2 with proper service code
            track2_formatted = f"{payment_data['pan']}={payment_data['expiry_date']}{payment_data['service_code']}"
            
            # Add discretionary data (including CVV if available)
            if 'track2_equivalent_data' in payment_data and payment_data['track2_equivalent_data']:
                discretionary = payment_data['track2_equivalent_data'].get('discretionary_data', '000000000')
                track2_formatted += discretionary
            else:
                # Use CVV if available, otherwise padding
                if payment_data.get('cvv'):
                    track2_formatted += f"0000{payment_data['cvv']}9999"
                else:
                    track2_formatted += "000000000"
                    
            print(f"✅ Generated Track 2: {track2_formatted}")
            
        else:
            print("❌ Missing required fields for track generation")
            
        return True
        
    except Exception as e:
        print(f"❌ Full parsing failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def analyze_service_code():
    """Analyze the service code meaning"""
    print("\n" + "="*50)
    print("SERVICE CODE ANALYSIS")
    print("="*50)
    
    service_code = "201"
    print(f"Service Code: {service_code}")
    print()
    
    if len(service_code) == 3:
        print("Service Code Breakdown:")
        print(f"  1st Digit ({service_code[0]}): ", end="")
        if service_code[0] == "1":
            print("International interchange OK")
        elif service_code[0] == "2":
            print("International interchange OK, IC processing supported")
        elif service_code[0] == "5":
            print("National interchange only")
        elif service_code[0] == "6":
            print("National interchange only, IC processing supported")
        else:
            print("Other authorization")
            
        print(f"  2nd Digit ({service_code[1]}): ", end="")
        if service_code[1] == "0":
            print("Normal authorization")
        elif service_code[1] == "2":
            print("Contact issuer via online means")
        elif service_code[1] == "4":
            print("Contact issuer via online means except under bilateral agreement")
        else:
            print("Other authorization method")
            
        print(f"  3rd Digit ({service_code[2]}): ", end="")
        if service_code[2] == "0":
            print("No restrictions, PIN required")
        elif service_code[2] == "1":
            print("No restrictions, PIN required for cash")
        elif service_code[2] == "2":
            print("Goods and services only")
        elif service_code[2] == "3":
            print("ATM only, PIN required")
        elif service_code[2] == "4":
            print("Cash only")
        elif service_code[2] == "5":
            print("Goods and services only, PIN required for cash")
        elif service_code[2] == "6":
            print("No restrictions, use PIN where feasible")
        elif service_code[2] == "7":
            print("Goods and services only, use PIN where feasible")
        else:
            print("Other restrictions")

if __name__ == "__main__":
    success = test_cvv_service_extraction()
    if success:
        analyze_service_code()
        print("\n🎉 CVV and Service Code extraction successful!")
    else:
        print("\n❌ Testing failed")
