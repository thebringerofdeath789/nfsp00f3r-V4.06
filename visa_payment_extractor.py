#!/usr/bin/env python3
# =====================================================================
# File: visa_payment_extractor.py
# Project: nfsp00f3r V4.05 - EMV/NFC Payment Data Extractor
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Specialized payment data extractor that directly parses the EMV
#   record data we found. Extracts PAN, cardholder name, expiry date,
#   and service code from the Track 2 equivalent data.
# =====================================================================

import os
import sys
import time
import re
from typing import Dict, List, Optional, Tuple, Any

try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    print("✅ Smart card library loaded successfully")
except ImportError as e:
    print(f"❌ Failed to import smartcard library: {e}")
    sys.exit(1)

class PaymentDataExtractor:
    """Specialized payment data extractor"""
    
    def __init__(self):
        self.connection = None
        
    def connect_to_card(self) -> bool:
        """Connect to the first available card"""
        try:
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found")
                return False
            
            reader = available_readers[0]
            print(f"🔗 Connecting to: {reader}")
            
            self.connection = reader.createConnection()
            self.connection.connect()
            
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
    
    def select_visa_application(self) -> bool:
        """Select Visa application"""
        # Visa Debit/Credit AID
        visa_aid = [0xA0, 0x00, 0x00, 0x00, 0x03, 0x10, 0x10]
        select_cmd = [0x00, 0xA4, 0x04, 0x00, len(visa_aid)] + visa_aid
        
        response, sw1, sw2 = self.send_apdu(select_cmd)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✅ Visa application selected successfully")
            return True
        else:
            print(f"❌ Failed to select Visa application: {sw1:02X}{sw2:02X}")
            return False
    
    def parse_track2_data(self, track2_hex: str) -> Dict[str, str]:
        """Parse Track 2 equivalent data"""
        payment_info = {}
        
        print(f"🎵 Parsing Track 2 data: {track2_hex}")
        
        # Remove any padding (F characters)
        track2_clean = track2_hex.replace('F', '').rstrip('0')
        
        # Track 2 format: PAN + separator (D or =) + YYMM + Service Code + Additional Data
        # Look for separator D or =
        separator_pos = -1
        for i, char in enumerate(track2_clean):
            if char in ['D', '=']:
                separator_pos = i
                break
        
        if separator_pos == -1:
            print("  ⚠️ No separator found in Track 2 data")
            return payment_info
        
        # Extract PAN (everything before separator)
        pan = track2_clean[:separator_pos]
        payment_info['pan'] = pan
        print(f"  💳 PAN: {pan}")
        
        # Extract data after separator
        after_separator = track2_clean[separator_pos + 1:]
        
        if len(after_separator) >= 4:
            # Extract expiry date (YYMM format)
            expiry_raw = after_separator[:4]
            year = expiry_raw[:2]
            month = expiry_raw[2:4]
            payment_info['expiry_date'] = f"{month}/{year}"
            print(f"  📅 Expiry Date: {month}/{year}")
            
        if len(after_separator) >= 7:
            # Extract service code (3 digits)
            service_code = after_separator[4:7]
            payment_info['service_code'] = service_code
            print(f"  🔧 Service Code: {service_code}")
            
        if len(after_separator) > 7:
            # Additional discretionary data
            discretionary = after_separator[7:]
            payment_info['discretionary_data'] = discretionary
            print(f"  📊 Discretionary Data: {discretionary}")
        
        return payment_info
    
    def parse_cardholder_name(self, name_hex: str) -> str:
        """Parse cardholder name from hex data"""
        try:
            # Convert hex to ASCII
            name_bytes = bytes.fromhex(name_hex)
            name = name_bytes.decode('ascii', errors='ignore').strip()
            
            # Clean up the name (remove null chars and extra spaces)
            name = ' '.join(name.split())
            return name
        except:
            return "UNKNOWN"
    
    def parse_emv_tlv_record(self, record_data: List[int]) -> Dict[str, Any]:
        """Parse EMV TLV record data"""
        payment_info = {}
        hex_data = ''.join([f"{b:02X}" for b in record_data])
        
        print(f"📄 Parsing record: {hex_data}")
        
        i = 0
        while i < len(record_data):
            if i >= len(record_data):
                break
                
            # Get tag
            tag = record_data[i]
            original_i = i
            
            # Handle multi-byte tags
            if tag & 0x1F == 0x1F:  # Multi-byte tag
                tag_bytes = [tag]
                i += 1
                while i < len(record_data) and (record_data[i] & 0x80):
                    tag_bytes.append(record_data[i])
                    i += 1
                if i < len(record_data):
                    tag_bytes.append(record_data[i])
                tag_hex = ''.join([f"{b:02X}" for b in tag_bytes])
            else:
                tag_hex = f"{tag:02X}"
            i += 1
            
            if i >= len(record_data):
                break
                
            # Get length
            length = record_data[i]
            i += 1
            
            if length & 0x80:  # Long form length
                length_bytes = length & 0x7F
                if length_bytes == 0:  # Indefinite length
                    print(f"  ⚠️ Indefinite length not supported for tag {tag_hex}")
                    break
                    
                length = 0
                for j in range(length_bytes):
                    if i < len(record_data):
                        length = (length << 8) | record_data[i]
                        i += 1
                    else:
                        break
            
            # Extract value
            if i + length <= len(record_data):
                value_bytes = record_data[i:i + length]
                value_hex = ''.join([f"{b:02X}" for b in value_bytes])
                
                print(f"  🏷️ Tag {tag_hex} (Length {length}): {value_hex}")
                
                # Process specific tags
                if tag_hex == "57":  # Track 2 Equivalent Data
                    track2_info = self.parse_track2_data(value_hex)
                    payment_info.update(track2_info)
                    
                elif tag_hex == "5F20":  # Cardholder Name
                    cardholder_name = self.parse_cardholder_name(value_hex)
                    payment_info['cardholder_name'] = cardholder_name
                    print(f"      👤 Cardholder Name: {cardholder_name}")
                    
                elif tag_hex == "5A":  # PAN
                    # PAN is BCD encoded
                    pan = value_hex.replace('F', '').rstrip('0')
                    payment_info['pan'] = pan
                    print(f"      💳 PAN: {pan}")
                    
                elif tag_hex == "5F24":  # Application Expiry Date
                    if length == 3:  # YYMMDD format
                        year = value_hex[:2]
                        month = value_hex[2:4]
                        payment_info['expiry_date'] = f"{month}/{year}"
                        print(f"      📅 Expiry Date: {month}/{year}")
                
                i += length
            else:
                print(f"  ⚠️ Invalid length for tag {tag_hex}")
                break
        
        return payment_info
    
    def read_payment_records(self) -> Dict[str, Any]:
        """Read payment records from the card"""
        print("\n🔍 Reading payment records...")
        all_payment_data = {}
        
        # Based on our previous findings, read SFI 1, Record 1
        sfi = 1
        record = 1
        p2 = (sfi << 3) | 0x04
        read_cmd = [0x00, 0xB2, record, p2]
        
        print(f"📋 Reading SFI {sfi}, Record {record}...")
        response, sw1, sw2 = self.send_apdu(read_cmd)
        
        if sw1 == 0x90:
            print("✅ Record read successfully")
            payment_data = self.parse_emv_tlv_record(response)
            all_payment_data.update(payment_data)
        else:
            print(f"❌ Failed to read record: {sw1:02X}{sw2:02X}")
        
        # Try additional SFI/record combinations
        additional_reads = [
            (1, 2), (2, 1), (2, 2), (3, 1), (8, 1), (10, 1)
        ]
        
        for sfi, record in additional_reads:
            p2 = (sfi << 3) | 0x04
            read_cmd = [0x00, 0xB2, record, p2]
            
            response, sw1, sw2 = self.send_apdu(read_cmd)
            if sw1 == 0x90:
                print(f"📋 Additional record SFI {sfi}, Record {record}:")
                additional_data = self.parse_emv_tlv_record(response)
                # Merge non-duplicate data
                for key, value in additional_data.items():
                    if key not in all_payment_data or not all_payment_data[key]:
                        all_payment_data[key] = value
        
        return all_payment_data
    
    def display_payment_info(self, payment_data: Dict[str, Any]):
        """Display extracted payment information"""
        print("\n" + "=" * 60)
        print("💳 EXTRACTED PAYMENT CARD INFORMATION")
        print("=" * 60)
        
        if not payment_data:
            print("❌ No payment data extracted")
            return
        
        # Primary payment information
        print("🔑 PRIMARY PAYMENT DATA:")
        
        pan = payment_data.get('pan', 'Not found')
        print(f"  💳 Primary Account Number (PAN): {pan}")
        
        cardholder = payment_data.get('cardholder_name', 'Not found')
        print(f"  👤 Cardholder Name: {cardholder}")
        
        expiry = payment_data.get('expiry_date', 'Not found')
        print(f"  📅 Expiry Date: {expiry}")
        
        service_code = payment_data.get('service_code', 'Not found')
        print(f"  🔧 Service Code: {service_code}")
        
        # Card analysis
        print("\n📊 CARD ANALYSIS:")
        if pan != 'Not found':
            if pan.startswith('4'):
                print("  💼 Card Type: VISA")
                
                # Determine Visa product type
                if len(pan) == 16:
                    print("  📋 Product: Visa Classic/Gold/Platinum")
                elif len(pan) == 13:
                    print("  📋 Product: Visa Electron")
                    
            elif pan.startswith('5'):
                print("  💼 Card Type: MASTERCARD")
            elif pan.startswith('3'):
                print("  💼 Card Type: AMERICAN EXPRESS")
        
        if service_code != 'Not found' and len(service_code) >= 3:
            print(f"  🔧 Service Code Analysis:")
            print(f"    - Authorization: {service_code[0]}")
            print(f"    - PIN Requirements: {service_code[1]}")
            print(f"    - Authorization Restrictions: {service_code[2]}")
        
        # Additional data
        print("\n📋 ADDITIONAL DATA:")
        for key, value in payment_data.items():
            if key not in ['pan', 'cardholder_name', 'expiry_date', 'service_code']:
                print(f"  📊 {key.replace('_', ' ').title()}: {value}")
        
        # Security notice
        print("\n⚠️  SECURITY NOTICE:")
        print("    This information is extracted for authorized testing purposes only.")
        print("    Ensure compliance with applicable laws and regulations.")
    
    def disconnect(self):
        """Disconnect from card"""
        if self.connection:
            try:
                self.connection.disconnect()
                print("\n🔌 Disconnected from card")
            except:
                pass

def main():
    """Main execution"""
    print("=" * 60)
    print("💳 VISA PAYMENT DATA EXTRACTOR")
    print("=" * 60)
    print("🎯 Extracting PAN, Cardholder Name, Expiry, Service Code...")
    print("Place your Visa card on the ACR122 reader...\n")
    
    extractor = PaymentDataExtractor()
    
    try:
        # Connect to card
        if not extractor.connect_to_card():
            return 1
        
        # Select Visa application
        if not extractor.select_visa_application():
            return 1
        
        # Read payment data
        payment_data = extractor.read_payment_records()
        
        # Display results
        extractor.display_payment_info(payment_data)
        
        print("\n✅ Payment data extraction complete!")
        
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
