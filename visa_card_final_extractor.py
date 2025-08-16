#!/usr/bin/env python3
# =====================================================================
# File: visa_card_final_extractor.py
# Project: nfsp00f3r V4.05 - EMV/NFC Payment Data Extractor
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Final version payment data extractor that handles nested TLV
#   structures and extracts all payment data from the EMV records.
# =====================================================================

import sys
from typing import Dict, List, Tuple

try:
    from smartcard.System import readers
    from smartcard.util import toHexString
except ImportError as e:
    print(f"❌ Failed to import smartcard library: {e}")
    sys.exit(1)

class FinalVisaExtractor:
    """Final payment data extractor with proper TLV parsing"""
    
    def __init__(self):
        self.connection = None
        
    def connect_to_card(self) -> bool:
        """Connect to card"""
        try:
            reader = readers()[0]
            self.connection = reader.createConnection()
            self.connection.connect()
            print(f"✅ Connected - ATR: {toHexString(self.connection.getATR())}")
            return True
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send_apdu(self, cmd: List[int]) -> Tuple[List[int], int, int]:
        """Send APDU"""
        try:
            return self.connection.transmit(cmd)
        except:
            return [], 0x6F, 0x00
    
    def parse_tlv_recursive(self, data: bytes, level: int = 0) -> Dict:
        """Recursively parse TLV data"""
        result = {}
        i = 0
        indent = "  " * level
        
        while i < len(data):
            if i >= len(data):
                break
                
            # Parse tag
            tag_start = i
            tag = data[i]
            i += 1
            
            # Multi-byte tag handling
            if tag & 0x1F == 0x1F:
                while i < len(data) and data[i] & 0x80:
                    tag = (tag << 8) | data[i]
                    i += 1
                if i < len(data):
                    tag = (tag << 8) | data[i]
                    i += 1
            
            if i >= len(data):
                break
                
            # Parse length
            length = data[i]
            i += 1
            
            if length & 0x80:
                length_bytes = length & 0x7F
                length = 0
                for j in range(length_bytes):
                    if i < len(data):
                        length = (length << 8) | data[i]
                        i += 1
            
            # Extract value
            if i + length <= len(data):
                value = data[i:i + length]
                tag_hex = f"{tag:02X}" if tag < 256 else f"{tag:04X}"
                
                print(f"{indent}🏷️  Tag {tag_hex} (Len {length}): {value.hex().upper()}")
                
                # Process specific EMV tags
                if tag_hex == "57":  # Track 2 Equivalent Data
                    self.parse_track2(value)
                    result['track2'] = value.hex().upper()
                    
                elif tag_hex == "5F20":  # Cardholder Name
                    name = self.parse_cardholder_name(value)
                    result['cardholder_name'] = name
                    print(f"{indent}    👤 Cardholder: {name}")
                    
                elif tag_hex == "5A":  # PAN
                    pan = self.parse_pan(value)
                    result['pan'] = pan
                    print(f"{indent}    💳 PAN: {pan}")
                    
                elif tag_hex == "5F24":  # Expiry Date
                    expiry = self.parse_expiry(value)
                    result['expiry_date'] = expiry
                    print(f"{indent}    📅 Expiry: {expiry}")
                    
                elif tag_hex in ["70", "77", "80"]:  # Template tags - recurse
                    nested = self.parse_tlv_recursive(value, level + 1)
                    result.update(nested)
                
                else:
                    result[tag_hex] = value.hex().upper()
                
                i += length
            else:
                break
        
        return result
    
    def parse_track2(self, track2_data: bytes) -> Dict:
        """Parse Track 2 equivalent data"""
        track2_hex = track2_data.hex().upper()
        print(f"      🎵 Track 2 Data: {track2_hex}")
        
        # Remove padding F characters
        track2_clean = track2_hex.rstrip('F')
        
        # Find separator D
        separator_pos = track2_clean.find('D')
        if separator_pos == -1:
            print("      ⚠️  No separator found")
            return {}
        
        # Extract PAN
        pan = track2_clean[:separator_pos]
        print(f"      💳 PAN (from Track2): {pan}")
        
        # Extract data after separator
        after_sep = track2_clean[separator_pos + 1:]
        
        if len(after_sep) >= 4:
            year = after_sep[:2]
            month = after_sep[2:4]
            print(f"      📅 Expiry (from Track2): {month}/{year}")
            
        if len(after_sep) >= 7:
            service_code = after_sep[4:7]
            print(f"      🔧 Service Code: {service_code}")
        
        return {'pan': pan, 'expiry': f"{month}/{year}", 'service_code': service_code}
    
    def parse_cardholder_name(self, name_data: bytes) -> str:
        """Parse cardholder name"""
        try:
            name = name_data.decode('ascii', errors='ignore').strip()
            return ' '.join(name.split())
        except:
            return "UNKNOWN"
    
    def parse_pan(self, pan_data: bytes) -> str:
        """Parse PAN from BCD format"""
        return pan_data.hex().upper().rstrip('F')
    
    def parse_expiry(self, expiry_data: bytes) -> str:
        """Parse expiry date"""
        if len(expiry_data) >= 2:
            hex_date = expiry_data.hex().upper()
            year = hex_date[:2]
            month = hex_date[2:4]
            return f"{month}/{year}"
        return "Unknown"
    
    def extract_all_payment_data(self) -> Dict:
        """Extract all payment data"""
        print("\n" + "="*60)
        print("💳 COMPREHENSIVE PAYMENT DATA EXTRACTION")
        print("="*60)
        
        # Select Visa app
        visa_aid = [0xA0, 0x00, 0x00, 0x00, 0x03, 0x10, 0x10]
        select_cmd = [0x00, 0xA4, 0x04, 0x00, len(visa_aid)] + visa_aid
        response, sw1, sw2 = self.send_apdu(select_cmd)
        
        if sw1 != 0x90:
            print("❌ Failed to select Visa application")
            return {}
        
        print("✅ Visa application selected")
        
        # Read all available records
        all_data = {}
        
        # Read the main payment record (SFI 1, Record 1)
        print(f"\n📋 Reading SFI 1, Record 1 (Main Payment Data):")
        read_cmd = [0x00, 0xB2, 0x01, 0x0C]  # SFI 1, Record 1
        response, sw1, sw2 = self.send_apdu(read_cmd)
        
        if sw1 == 0x90:
            print("✅ Payment record found!")
            record_data = self.parse_tlv_recursive(bytes(response))
            all_data.update(record_data)
        
        return all_data
    
    def display_final_results(self, payment_data: Dict):
        """Display final payment card information"""
        print("\n" + "="*60)
        print("🎉 FINAL PAYMENT CARD INFORMATION")
        print("="*60)
        
        if not payment_data:
            print("❌ No payment data found")
            return
        
        print("🔑 EXTRACTED PAYMENT DATA:")
        
        # PAN
        pan = payment_data.get('pan', 'Not found')
        print(f"  💳 Primary Account Number: {pan}")
        
        # Cardholder Name
        cardholder = payment_data.get('cardholder_name', 'Not found')
        print(f"  👤 Cardholder Name: {cardholder}")
        
        # Expiry Date
        expiry = payment_data.get('expiry_date', payment_data.get('expiry', 'Not found'))
        print(f"  📅 Expiry Date: {expiry}")
        
        # Service Code
        service_code = payment_data.get('service_code', 'Not found')
        print(f"  🔧 Service Code: {service_code}")
        
        # Track 2 Data
        track2 = payment_data.get('track2', 'Not found')
        print(f"  🎵 Track 2 Data: {track2}")
        
        # Card Type Analysis
        print(f"\n💼 CARD ANALYSIS:")
        if pan != 'Not found':
            if pan.startswith('4'):
                print(f"  🏛️  Card Network: VISA")
                print(f"  📏 PAN Length: {len(pan)} digits")
                
                # Check card type
                if pan.startswith('4031'):
                    print(f"  💳 Product Type: Visa Debit")
                else:
                    print(f"  💳 Product Type: Visa Credit/Debit")
        
        print(f"\n📊 ALL EXTRACTED DATA:")
        for key, value in payment_data.items():
            if key not in ['pan', 'cardholder_name', 'expiry_date', 'expiry', 'service_code', 'track2']:
                print(f"  📋 {key}: {value}")
        
        print(f"\n⚠️  LEGAL NOTICE:")
        print(f"    This data extraction is for authorized security testing only.")
        print(f"    Comply with all applicable laws and regulations.")

def main():
    """Main execution"""
    print("="*60)
    print("🚀 FINAL VISA PAYMENT DATA EXTRACTOR")
    print("="*60)
    print("🎯 Target: PAN, Cardholder Name, Expiry, Service Code, Track 2")
    print("🎯 Method: Direct EMV record parsing")
    print("\nPlace your Visa card on the ACR122 reader...\n")
    
    extractor = FinalVisaExtractor()
    
    try:
        if not extractor.connect_to_card():
            return 1
        
        payment_data = extractor.extract_all_payment_data()
        extractor.display_final_results(payment_data)
        
        print("\n✅ Extraction complete!")
        
    except KeyboardInterrupt:
        print("\n🛑 Cancelled by user")
    except Exception as e:
        print(f"\n❌ Error: {e}")
        return 1
    finally:
        if extractor.connection:
            extractor.connection.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
