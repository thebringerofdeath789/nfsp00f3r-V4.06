#!/usr/bin/env python3
# =====================================================================
# File: visa_card_extractor_advanced.py
# Project: nfsp00f3r V4.05 - EMV/NFC Card Data Extractor
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Advanced Visa card data extractor that uses multiple techniques
#   to extract PAN, cardholder name, expiry date, and all payment
#   data without requiring PIN authentication. Uses various EMV
#   commands and data parsing methods.
# =====================================================================

import os
import sys
import time
from typing import Dict, List, Optional, Tuple, Any

try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    print("✅ Smart card library loaded successfully")
except ImportError as e:
    print(f"❌ Failed to import smartcard library: {e}")
    sys.exit(1)

class AdvancedVisaExtractor:
    """Advanced Visa card data extractor with multiple extraction methods"""
    
    def __init__(self):
        self.connection = None
        self.applications = []
        self.card_data = {}
        
    def connect_to_card(self) -> bool:
        """Connect to the first available card"""
        try:
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found")
                return False
            
            print(f"📱 Found {len(available_readers)} readers")
            reader = available_readers[0]
            print(f"🔗 Connecting to: {reader}")
            
            self.connection = reader.createConnection()
            self.connection.connect()
            
            # Get ATR
            atr = self.connection.getATR()
            print(f"✅ Card connected - ATR: {toHexString(atr)}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send_apdu(self, apdu_cmd: List[int]) -> Tuple[List[int], int, int]:
        """Send APDU command and return response"""
        try:
            response, sw1, sw2 = self.connection.transmit(apdu_cmd)
            return response, sw1, sw2
        except Exception as e:
            print(f"❌ APDU transmission failed: {e}")
            return [], 0x6F, 0x00
    
    def parse_tlv(self, data: List[int]) -> Dict[str, Any]:
        """Parse TLV (Tag-Length-Value) encoded data"""
        tlv_data = {}
        i = 0
        
        while i < len(data):
            if i >= len(data):
                break
                
            # Parse tag
            tag = data[i]
            if tag & 0x1F == 0x1F:  # Multi-byte tag
                i += 1
                if i < len(data):
                    tag = (tag << 8) | data[i]
            i += 1
            
            if i >= len(data):
                break
                
            # Parse length
            length = data[i]
            i += 1
            
            if length & 0x80:  # Long form length
                length_bytes = length & 0x7F
                length = 0
                for j in range(length_bytes):
                    if i < len(data):
                        length = (length << 8) | data[i]
                        i += 1
            
            # Extract value
            if i + length <= len(data):
                value = data[i:i + length]
                tlv_data[f"{tag:02X}"] = value
                i += length
            else:
                break
        
        return tlv_data
    
    def extract_pan_from_track2(self, track2_data: List[int]) -> Optional[str]:
        """Extract PAN from Track 2 data"""
        try:
            # Track 2 format: PAN + separator (D) + expiry + service code + ...
            track2_hex = ''.join([f"{b:02X}" for b in track2_data])
            
            # Find separator 'D'
            if 'D' in track2_hex:
                pan = track2_hex.split('D')[0]
                return pan
            elif '=' in track2_hex:  # Some cards use = instead of D
                pan = track2_hex.split('=')[0]
                return pan
                
        except Exception as e:
            print(f"  ⚠️ Track 2 parsing error: {e}")
            
        return None
    
    def bcd_to_string(self, bcd_data: List[int]) -> str:
        """Convert BCD encoded data to string"""
        result = ""
        for byte in bcd_data:
            high_nibble = (byte >> 4) & 0x0F
            low_nibble = byte & 0x0F
            
            if high_nibble <= 9:
                result += str(high_nibble)
            if low_nibble <= 9:
                result += str(low_nibble)
        return result
    
    def format_expiry_date(self, date_data: List[int]) -> str:
        """Format expiry date from BCD format"""
        try:
            if len(date_data) >= 2:
                year = f"{date_data[0]:02X}"
                month = f"{date_data[1]:02X}"
                return f"{month}/{year}"
        except:
            pass
        return "Unknown"
    
    def extract_cardholder_name(self, name_data: List[int]) -> str:
        """Extract cardholder name from binary data"""
        try:
            # Try ASCII decoding
            name = ''.join(chr(b) for b in name_data if 32 <= b <= 126)
            return name.strip()
        except:
            return "Not available"
    
    def find_visa_applications(self) -> List[Dict]:
        """Find all Visa applications on the card"""
        print("\n🔍 Searching for Visa applications...")
        
        # Known Visa AIDs
        visa_aids = [
            [0xA0, 0x00, 0x00, 0x00, 0x03, 0x10, 0x10],  # Visa Debit/Credit
            [0xA0, 0x00, 0x00, 0x00, 0x03, 0x20, 0x10],  # Visa Electron
            [0xA0, 0x00, 0x00, 0x00, 0x03, 0x30, 0x10],  # Visa Interlink
            [0xA0, 0x00, 0x00, 0x00, 0x03, 0x80, 0x10],  # Visa Plus
        ]
        
        applications = []
        
        # Try each known Visa AID
        for aid in visa_aids:
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid)] + aid
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Found Visa application: {toHexString(aid)}")
                
                # Parse FCI (File Control Information)
                fci_data = self.parse_tlv(response)
                app_info = {
                    'aid': aid,
                    'fci': fci_data,
                    'response': response
                }
                applications.append(app_info)
        
        # Also try PSE (Payment System Environment)
        print("\n🔍 Trying PSE (Payment System Environment)...")
        pse_aids = [
            "1PAY.SYS.DDF01",  # Contact PSE
            "2PAY.SYS.DDF01"   # Contactless PSE
        ]
        
        for pse_name in pse_aids:
            pse_bytes = [ord(c) for c in pse_name]
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(pse_bytes)] + pse_bytes
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 == 0x90:
                print(f"✅ PSE found: {pse_name}")
                # Try to read PSE records
                self.read_pse_records()
        
        return applications
    
    def read_pse_records(self):
        """Read PSE records to find applications"""
        print("  📄 Reading PSE records...")
        
        # Try to read records from SFI 1
        for record_num in range(1, 10):  # Try records 1-9
            read_cmd = [0x00, 0xB2, record_num, 0x0C]  # READ RECORD
            response, sw1, sw2 = self.send_apdu(read_cmd)
            
            if sw1 == 0x90:
                print(f"    📋 Record {record_num}: {toHexString(response)}")
                # Parse record for application entries
                tlv_data = self.parse_tlv(response)
                for tag, value in tlv_data.items():
                    if tag == "4F":  # AID
                        print(f"      🎯 Found AID: {toHexString(value)}")
            elif sw1 == 0x6A and sw2 == 0x83:  # Record not found
                break
    
    def extract_payment_data_method1(self, app_info: Dict) -> Dict:
        """Method 1: Extract data using READ RECORD commands"""
        print("\n📊 Method 1: Using READ RECORD commands")
        payment_data = {}
        
        # Try to read records from various SFIs
        sfis_to_try = [1, 2, 3, 4, 5, 8, 10, 11, 12, 13, 14]
        
        for sfi in sfis_to_try:
            print(f"  📁 Reading SFI {sfi}...")
            
            for record_num in range(1, 16):  # Try up to 15 records
                # READ RECORD command: CLA INS P1 P2
                # P1 = record number, P2 = (SFI << 3) | 0x04
                p2 = (sfi << 3) | 0x04
                read_cmd = [0x00, 0xB2, record_num, p2]
                
                response, sw1, sw2 = self.send_apdu(read_cmd)
                
                if sw1 == 0x90:
                    print(f"    📋 SFI {sfi}, Record {record_num}: Found data")
                    print(f"         Data: {toHexString(response)}")
                    
                    # Parse the record
                    tlv_data = self.parse_tlv(response)
                    for tag, value in tlv_data.items():
                        self.process_emv_tag(tag, value, payment_data)
                        
                elif sw1 == 0x6A and sw2 == 0x83:  # Record not found
                    break
        
        return payment_data
    
    def extract_payment_data_method2(self, app_info: Dict) -> Dict:
        """Method 2: Extract data using GET DATA commands"""
        print("\n📊 Method 2: Using GET DATA commands")
        payment_data = {}
        
        # Common EMV data tags to request
        data_tags = [
            [0x5A],        # PAN
            [0x5F, 0x20],  # Cardholder Name
            [0x5F, 0x24],  # Expiry Date
            [0x5F, 0x25],  # Effective Date
            [0x5F, 0x30],  # Service Code
            [0x57],        # Track 2 Equivalent Data
            [0x5F, 0x34],  # PAN Sequence Number
            [0x9F, 0x08],  # Application Version Number
            [0x9F, 0x42],  # Application Currency Code
            [0x8A],        # Authorization Response Code
            [0x95],        # Terminal Verification Results
            [0x9A],        # Transaction Date
            [0x9C],        # Transaction Type
            [0x5F, 0x2A],  # Transaction Currency Code
        ]
        
        for tag in data_tags:
            # GET DATA command
            if len(tag) == 1:
                get_data_cmd = [0x80, 0xCA, 0x00, tag[0]]
            else:
                get_data_cmd = [0x80, 0xCA, tag[0], tag[1]]
            
            response, sw1, sw2 = self.send_apdu(get_data_cmd)
            
            if sw1 == 0x90:
                tag_hex = ''.join([f"{t:02X}" for t in tag])
                print(f"    📋 Tag {tag_hex}: {toHexString(response)}")
                self.process_emv_tag(tag_hex, response, payment_data)
        
        return payment_data
    
    def extract_payment_data_method3(self, app_info: Dict) -> Dict:
        """Method 3: Try GPO with minimal PDOL"""
        print("\n📊 Method 3: Using Get Processing Options (GPO)")
        payment_data = {}
        
        # Try GPO with empty or minimal PDOL
        gpo_variations = [
            [0x80, 0xA8, 0x00, 0x00, 0x02, 0x83, 0x00],  # Empty PDOL
            [0x80, 0xA8, 0x00, 0x00, 0x04, 0x83, 0x02, 0x00, 0x00],  # Minimal PDOL
        ]
        
        for gpo_cmd in gpo_variations:
            response, sw1, sw2 = self.send_apdu(gpo_cmd)
            
            if sw1 == 0x90:
                print(f"    ✅ GPO successful: {toHexString(response)}")
                
                # Parse GPO response
                tlv_data = self.parse_tlv(response)
                for tag, value in tlv_data.items():
                    self.process_emv_tag(tag, value, payment_data)
                    
                # Try to read application data after GPO
                self.read_application_data(payment_data)
                break
            else:
                print(f"    ❌ GPO failed: {sw1:02X}{sw2:02X}")
        
        return payment_data
    
    def read_application_data(self, payment_data: Dict):
        """Read application data after successful GPO"""
        print("    📄 Reading application data...")
        
        # Try common application file locators
        afls = [
            [0x08, 0x01, 0x01, 0x00],  # SFI 1, records 1-1
            [0x08, 0x01, 0x02, 0x00],  # SFI 1, records 1-2
            [0x10, 0x01, 0x01, 0x00],  # SFI 2, records 1-1
        ]
        
        for afl in afls:
            sfi = afl[0] >> 3
            start_record = afl[1]
            end_record = afl[2]
            
            for record in range(start_record, end_record + 1):
                p2 = (sfi << 3) | 0x04
                read_cmd = [0x00, 0xB2, record, p2]
                
                response, sw1, sw2 = self.send_apdu(read_cmd)
                if sw1 == 0x90:
                    print(f"      📋 AFL Record: {toHexString(response)}")
                    tlv_data = self.parse_tlv(response)
                    for tag, value in tlv_data.items():
                        self.process_emv_tag(tag, value, payment_data)
    
    def process_emv_tag(self, tag: str, value: List[int], payment_data: Dict):
        """Process EMV tag and extract meaningful data"""
        tag_upper = tag.upper()
        
        if tag_upper == "5A":  # PAN
            pan = self.bcd_to_string(value)
            payment_data['pan'] = pan
            print(f"      💳 PAN: {pan}")
            
        elif tag_upper == "5F20":  # Cardholder Name
            name = self.extract_cardholder_name(value)
            payment_data['cardholder_name'] = name
            print(f"      👤 Cardholder: {name}")
            
        elif tag_upper == "5F24":  # Expiry Date
            expiry = self.format_expiry_date(value)
            payment_data['expiry_date'] = expiry
            print(f"      📅 Expiry: {expiry}")
            
        elif tag_upper == "5F30":  # Service Code
            service_code = self.bcd_to_string(value)
            payment_data['service_code'] = service_code
            print(f"      🔧 Service Code: {service_code}")
            
        elif tag_upper == "57":  # Track 2 Equivalent Data
            track2_hex = toHexString(value)
            payment_data['track2'] = track2_hex
            print(f"      🎵 Track 2: {track2_hex}")
            
            # Extract PAN from Track 2 if not already found
            if 'pan' not in payment_data:
                pan = self.extract_pan_from_track2(value)
                if pan:
                    payment_data['pan'] = pan
                    print(f"      💳 PAN (from Track2): {pan}")
        
        elif tag_upper == "5F34":  # PAN Sequence Number
            pan_seq = self.bcd_to_string(value)
            payment_data['pan_sequence'] = pan_seq
            print(f"      🔢 PAN Sequence: {pan_seq}")
            
        elif tag_upper == "9F42":  # Application Currency Code
            currency_code = toHexString(value)
            payment_data['currency_code'] = currency_code
            print(f"      💰 Currency Code: {currency_code}")
    
    def comprehensive_extraction(self) -> Dict:
        """Perform comprehensive data extraction using all methods"""
        print("=" * 60)
        print("🎯 COMPREHENSIVE VISA CARD DATA EXTRACTION")
        print("=" * 60)
        
        all_data = {}
        
        # Find Visa applications
        applications = self.find_visa_applications()
        
        if not applications:
            print("❌ No Visa applications found")
            return all_data
        
        # Extract data using multiple methods for each application
        for i, app_info in enumerate(applications):
            print(f"\n{'='*50}")
            print(f"🔍 PROCESSING APPLICATION {i+1}")
            print(f"{'='*50}")
            
            # Select the application
            aid = app_info['aid']
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid)] + aid
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 != 0x90:
                print(f"❌ Failed to select application")
                continue
            
            app_data = {}
            
            # Method 1: READ RECORD
            method1_data = self.extract_payment_data_method1(app_info)
            app_data.update(method1_data)
            
            # Method 2: GET DATA
            method2_data = self.extract_payment_data_method2(app_info)
            app_data.update(method2_data)
            
            # Method 3: GPO + Application Data
            method3_data = self.extract_payment_data_method3(app_info)
            app_data.update(method3_data)
            
            all_data[f"app_{i+1}"] = app_data
        
        return all_data
    
    def display_results(self, extracted_data: Dict):
        """Display all extracted payment data"""
        print("\n" + "=" * 60)
        print("🏆 FINAL EXTRACTION RESULTS")
        print("=" * 60)
        
        if not extracted_data:
            print("❌ No payment data extracted")
            return
        
        for app_name, app_data in extracted_data.items():
            print(f"\n📱 {app_name.upper().replace('_', ' ')}")
            print("-" * 40)
            
            # Key payment information
            print("🔑 KEY PAYMENT INFORMATION:")
            pan = app_data.get('pan', 'Not found')
            cardholder = app_data.get('cardholder_name', 'Not found')
            expiry = app_data.get('expiry_date', 'Not found')
            service_code = app_data.get('service_code', 'Not found')
            track2 = app_data.get('track2', 'Not found')
            
            print(f"  💳 PAN (Primary Account Number): {pan}")
            print(f"  👤 Cardholder Name: {cardholder}")
            print(f"  📅 Expiry Date: {expiry}")
            print(f"  🔧 Service Code: {service_code}")
            print(f"  🎵 Track 2 Data: {track2}")
            
            # Additional data
            print("\n📊 ADDITIONAL CARD DATA:")
            for key, value in app_data.items():
                if key not in ['pan', 'cardholder_name', 'expiry_date', 'service_code', 'track2']:
                    print(f"  📋 {key.replace('_', ' ').title()}: {value}")
    
    def disconnect(self):
        """Disconnect from card"""
        if self.connection:
            try:
                self.connection.disconnect()
                print("🔌 Disconnected from card")
            except:
                pass

def main():
    """Main execution function"""
    print("🚀 Advanced Visa Card Data Extractor")
    print("Place your Visa card on the ACR122 reader...")
    
    extractor = AdvancedVisaExtractor()
    
    try:
        # Connect to card
        if not extractor.connect_to_card():
            return 1
        
        # Perform comprehensive extraction
        extracted_data = extractor.comprehensive_extraction()
        
        # Display results
        extractor.display_results(extracted_data)
        
        print("\n✅ Extraction complete!")
        
    except KeyboardInterrupt:
        print("\n🛑 Extraction cancelled by user")
    except Exception as e:
        print(f"\n❌ Extraction error: {e}")
        return 1
    finally:
        extractor.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
