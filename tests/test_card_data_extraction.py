#!/usr/bin/env python3
# =====================================================================
# File: test_card_data_extraction.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-15
#
# Description:
#   Comprehensive card data extraction test for ACR122U reader.
#   Extracts complete EMV data including PAN, cardholder name, expiry,
#   service codes, discretionary data, track data, and all available
#   EMV application data objects.
#
# Hardware Requirements:
#   - Windows 10 + Python 3.9
#   - ACR122U USB NFC Reader
#   - EMV payment card for testing
# =====================================================================

import os
import sys
import time
import binascii
from typing import Dict, List, Optional, Tuple, Any

# Import smartcard libraries
try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.CardConnection import CardConnection
    from smartcard.Exceptions import CardConnectionException, NoCardException
    print("✅ Smartcard library imported successfully")
except ImportError as e:
    print(f"❌ Error importing smartcard library: {e}")
    print("Please install: pip install pyscard")
    sys.exit(1)

class EMVDataExtractor:
    """Comprehensive EMV card data extraction"""
    
    def __init__(self):
        self.connection = None
        self.card_data = {}
        self.emv_tags = self._initialize_emv_tags()
    
    def _initialize_emv_tags(self) -> Dict[str, str]:
        """Initialize EMV tag dictionary for data interpretation"""
        return {
            # Application Data
            '4F': 'Application Identifier (AID)',
            '50': 'Application Label',
            '57': 'Track 2 Equivalent Data',
            '5A': 'Application Primary Account Number (PAN)',
            '5F20': 'Cardholder Name',
            '5F24': 'Application Expiration Date',
            '5F25': 'Application Effective Date',
            '5F28': 'Issuer Country Code',
            '5F2A': 'Transaction Currency Code',
            '5F2D': 'Language Preference',
            '5F30': 'Service Code',
            '5F34': 'Application Primary Account Number (PAN) Sequence Number',
            
            # Track Data
            '9F0B': 'Cardholder Name Extended',
            '9F0D': 'Issuer Action Code - Default',
            '9F0E': 'Issuer Action Code - Denial',
            '9F0F': 'Issuer Action Code - Online',
            '9F11': 'Issuer Code Table Index',
            '9F12': 'Application Preferred Name',
            '9F1F': 'Track 1 Discretionary Data',
            
            # Cryptographic Data
            '8E': 'Cardholder Verification Method (CVM) List',
            '8F': 'Certification Authority Public Key Index',
            '90': 'Issuer Public Key Certificate',
            '92': 'Issuer Public Key Remainder',
            '93': 'Signed Static Application Data',
            '94': 'Application File Locator (AFL)',
            '95': 'Terminal Verification Results',
            '9A': 'Transaction Date',
            '9B': 'Transaction Status Information',
            '9C': 'Transaction Type',
            '9F02': 'Amount, Authorised',
            '9F03': 'Amount, Other',
            '9F07': 'Application Usage Control',
            '9F08': 'Application Version Number',
            '9F32': 'Issuer Public Key Exponent',
            '9F46': 'ICC Public Key Certificate',
            '9F47': 'ICC Public Key Exponent',
            '9F48': 'ICC Public Key Remainder',
            '9F49': 'Dynamic Data Authentication Data Object List (DDOL)',
            
            # Additional EMV Tags
            '61': 'Application Template',
            '6F': 'File Control Information (FCI) Template',
            '70': 'READ RECORD Response Message Template',
            '71': 'Issuer Script Template 1',
            '72': 'Issuer Script Template 2',
            '73': 'Directory Discretionary Template',
            '77': 'Response Message Template Format 2',
            '80': 'Response Message Template Format 1',
            '81': 'Amount, Authorised (Binary)',
            '82': 'Application Interchange Profile',
            '83': 'Command Template',
            '84': 'Dedicated File (DF) Name',
            '87': 'Application Priority Indicator',
            '88': 'Short File Identifier (SFI)',
            '8A': 'Authorisation Response Code',
            '8C': 'Card Risk Management Data Object List 1 (CDOL1)',
            '8D': 'Card Risk Management Data Object List 2 (CDOL2)',
            'A5': 'File Control Information (FCI) Proprietary Template',
            'BF0C': 'File Control Information (FCI) Issuer Discretionary Data',
        }
    
    def connect_to_card(self) -> bool:
        """Connect to the first available card"""
        try:
            # Get available readers
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found")
                return False
            
            print(f"📱 Found {len(available_readers)} readers:")
            for i, reader in enumerate(available_readers):
                print(f"  {i+1}. {reader}")
            
            # Use first reader
            reader = available_readers[0]
            print(f"🔗 Connecting to: {reader}")
            
            # Create connection
            self.connection = reader.createConnection()
            self.connection.connect()
            
            # Get ATR
            atr = self.connection.getATR()
            atr_hex = toHexString(atr)
            print(f"✅ Connected successfully")
            print(f"📋 ATR: {atr_hex}")
            
            return True
            
        except NoCardException:
            print("❌ No card present on reader")
            print("Please place a card on the reader and try again")
            return False
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def send_apdu(self, apdu_hex: str) -> Tuple[List[int], int, int]:
        """Send APDU command and return response"""
        try:
            apdu = toBytes(apdu_hex)
            response, sw1, sw2 = self.connection.transmit(apdu)
            return response, sw1, sw2
        except Exception as e:
            print(f"❌ APDU transmission failed: {e}")
            return [], 0x00, 0x00
    
    def select_application(self, aid: str) -> bool:
        """Select EMV application by AID"""
        try:
            aid_bytes = aid.replace(' ', '')
            aid_len = len(aid_bytes) // 2
            
            # SELECT command: 00 A4 04 00 [Lc] [AID]
            select_cmd = f"00 A4 04 00 {aid_len:02X} {aid}"
            
            print(f"🔍 Selecting application: {aid}")
            print(f"   Command: {select_cmd}")
            
            response, sw1, sw2 = self.send_apdu(select_cmd)
            status = (sw1 << 8) | sw2
            
            print(f"   Response: {toHexString(response)} {sw1:02X}{sw2:02X}")
            
            if status == 0x9000:
                print("✅ Application selected successfully")
                
                # Parse FCI response
                if response:
                    self._parse_fci_data(response)
                return True
            else:
                print(f"❌ Application selection failed: 0x{status:04X}")
                return False
                
        except Exception as e:
            print(f"❌ Application selection error: {e}")
            return False
    
    def _parse_fci_data(self, fci_data: List[int]):
        """Parse File Control Information from SELECT response"""
        try:
            print("📄 Parsing FCI (File Control Information):")
            fci_hex = toHexString(fci_data)
            print(f"   FCI Data: {fci_hex}")
            
            # Parse TLV structure
            parsed_data = self._parse_tlv(fci_data)
            self.card_data.update(parsed_data)
            
            # Display parsed FCI data
            for tag, value in parsed_data.items():
                tag_name = self.emv_tags.get(tag, f"Unknown Tag {tag}")
                print(f"   {tag}: {tag_name} = {value}")
                
        except Exception as e:
            print(f"❌ FCI parsing error: {e}")
    
    def read_all_records(self) -> Dict[str, Any]:
        """Read all records from all files"""
        print("\n📚 Reading all application records...")
        
        all_records = {}
        
        # Try to read records from SFI 1-31
        for sfi in range(1, 32):
            records = self._read_records_from_sfi(sfi)
            if records:
                all_records[f"SFI_{sfi:02X}"] = records
        
        return all_records
    
    def _read_records_from_sfi(self, sfi: int) -> Dict[int, List[int]]:
        """Read all records from a specific SFI"""
        records = {}
        
        # Try to read records 1-16 from this SFI
        for record_num in range(1, 17):
            try:
                # READ RECORD command: 00 B2 [Record] [SFI] 00
                sfi_byte = (sfi << 3) | 0x04  # SFI in bits 7-3, bit 2 set
                read_cmd = f"00 B2 {record_num:02X} {sfi_byte:02X} 00"
                
                response, sw1, sw2 = self.send_apdu(read_cmd)
                status = (sw1 << 8) | sw2
                
                if status == 0x9000 and response:
                    print(f"✅ SFI {sfi:02X} Record {record_num}: {len(response)} bytes")
                    records[record_num] = response
                    
                    # Parse record data
                    parsed_data = self._parse_tlv(response)
                    self.card_data.update(parsed_data)
                    
                elif status == 0x6A83:  # Record not found
                    break  # No more records in this SFI
                elif status == 0x6A82:  # File not found
                    break  # SFI doesn't exist
                    
            except Exception as e:
                continue
        
        return records
    
    def _parse_tlv(self, data: List[int]) -> Dict[str, str]:
        """Parse TLV (Tag-Length-Value) encoded data"""
        parsed = {}
        i = 0
        
        try:
            while i < len(data):
                # Parse tag
                tag_start = i
                if data[i] & 0x1F == 0x1F:  # Multi-byte tag
                    i += 1
                    while i < len(data) and data[i] & 0x80:
                        i += 1
                    i += 1
                else:  # Single byte tag
                    i += 1
                
                tag_bytes = data[tag_start:i]
                tag = ''.join(f'{b:02X}' for b in tag_bytes)
                
                if i >= len(data):
                    break
                
                # Parse length
                length = data[i]
                i += 1
                
                if length & 0x80:  # Multi-byte length
                    length_bytes = length & 0x7F
                    if i + length_bytes > len(data):
                        break
                    length = 0
                    for j in range(length_bytes):
                        length = (length << 8) | data[i + j]
                    i += length_bytes
                
                # Parse value
                if i + length > len(data):
                    break
                
                value_bytes = data[i:i + length]
                value = ''.join(f'{b:02X}' for b in value_bytes)
                
                parsed[tag] = value
                i += length
                
        except Exception as e:
            print(f"⚠️ TLV parsing error: {e}")
        
        return parsed
    
    def extract_payment_data(self) -> Dict[str, Any]:
        """Extract and format payment card specific data"""
        print("\n💳 Extracting Payment Card Data...")
        
        payment_data = {}
        
        # Extract PAN (Primary Account Number)
        if '5A' in self.card_data:
            pan_hex = self.card_data['5A']
            pan = self._decode_bcd(pan_hex).rstrip('F')  # Remove padding
            payment_data['PAN'] = pan
            payment_data['Card_Number'] = f"{pan[:4]} {pan[4:8]} {pan[8:12]} {pan[12:]}" if len(pan) >= 16 else pan
            
            # Identify card type
            payment_data['Card_Type'] = self._identify_card_type(pan)
        
        # Extract Cardholder Name
        if '5F20' in self.card_data:
            name_hex = self.card_data['5F20']
            name = bytes.fromhex(name_hex).decode('ascii', errors='ignore').strip()
            payment_data['Cardholder_Name'] = name
        
        # Extract Expiration Date
        if '5F24' in self.card_data:
            exp_hex = self.card_data['5F24']
            if len(exp_hex) >= 4:
                year = exp_hex[:2]
                month = exp_hex[2:4]
                payment_data['Expiry_Date'] = f"{month}/{year}"
        
        # Extract Service Code
        if '5F30' in self.card_data:
            service_hex = self.card_data['5F30']
            payment_data['Service_Code'] = service_hex
            payment_data['Service_Code_Meaning'] = self._decode_service_code(service_hex)
        
        # Extract Track 2 Data
        if '57' in self.card_data:
            track2_hex = self.card_data['57']
            track2_decoded = self._decode_track2(track2_hex)
            payment_data.update(track2_decoded)
        
        # Extract Application Label
        if '50' in self.card_data:
            label_hex = self.card_data['50']
            label = bytes.fromhex(label_hex).decode('ascii', errors='ignore').strip()
            payment_data['Application_Label'] = label
        
        # Extract Issuer Country Code
        if '5F28' in self.card_data:
            country_hex = self.card_data['5F28']
            country_code = self._decode_bcd(country_hex)
            payment_data['Issuer_Country_Code'] = country_code
            payment_data['Issuer_Country'] = self._get_country_name(country_code)
        
        return payment_data
    
    def _decode_bcd(self, hex_string: str) -> str:
        """Decode BCD (Binary Coded Decimal) string"""
        return ''.join(hex_string[i:i+2] for i in range(0, len(hex_string), 2) if hex_string[i:i+2] != '00')
    
    def _identify_card_type(self, pan: str) -> str:
        """Identify card type from PAN"""
        if pan.startswith('4'):
            return 'Visa'
        elif pan.startswith('5') or pan.startswith('2'):
            return 'MasterCard'
        elif pan.startswith('3'):
            if pan.startswith('34') or pan.startswith('37'):
                return 'American Express'
            else:
                return 'Diners Club'
        elif pan.startswith('6'):
            return 'Discover'
        else:
            return 'Unknown'
    
    def _decode_service_code(self, service_hex: str) -> Dict[str, str]:
        """Decode service code meaning"""
        if len(service_hex) < 3:
            return {'error': 'Invalid service code length'}
        
        pos1 = int(service_hex[0])
        pos2 = int(service_hex[1]) 
        pos3 = int(service_hex[2])
        
        pos1_meaning = {
            1: 'International interchange OK',
            2: 'International interchange, use IC (chip) where feasible', 
            5: 'National interchange only except under bilateral agreement',
            6: 'National interchange only except under bilateral agreement, use IC where feasible',
            7: 'No interchange except under bilateral agreement (closed loop)',
            9: 'Test'
        }.get(pos1, 'Reserved/Unknown')
        
        pos2_meaning = {
            0: 'Normal authorization and clearing',
            2: 'Contact issuer via online means',
            4: 'Contact issuer via online means except under bilateral agreement'
        }.get(pos2, 'Reserved/Unknown')
        
        pos3_meaning = {
            0: 'No restrictions, PIN required',
            1: 'No restrictions',
            2: 'Goods and services only (no cash)',
            3: 'ATM only, PIN required',
            4: 'Cash only',
            5: 'Goods and services only (no cash), PIN required',
            6: 'No restrictions, use PIN where feasible',
            7: 'Goods and services only (no cash), use PIN where feasible'
        }.get(pos3, 'Reserved/Unknown')
        
        return {
            'Position_1': pos1_meaning,
            'Position_2': pos2_meaning, 
            'Position_3': pos3_meaning
        }
    
    def _decode_track2(self, track2_hex: str) -> Dict[str, Any]:
        """Decode Track 2 equivalent data"""
        try:
            # Convert hex to BCD
            track2_bcd = self._decode_bcd(track2_hex)
            
            # Find separator (D or =)
            if 'D' in track2_hex:
                separator_pos = track2_hex.index('D')
            else:
                separator_pos = track2_hex.index('=') if '=' in track2_hex else -1
            
            if separator_pos == -1:
                return {'Track2_Error': 'No separator found'}
            
            # Extract PAN (before separator)
            pan_part = track2_hex[:separator_pos]
            pan = self._decode_bcd(pan_part).rstrip('F')
            
            # Extract remaining data (after separator)
            remaining = track2_hex[separator_pos+1:]
            
            # Extract expiry (first 4 digits after separator)
            expiry = remaining[:4] if len(remaining) >= 4 else ''
            
            # Extract service code (next 3 digits)
            service_code = remaining[4:7] if len(remaining) >= 7 else ''
            
            # Extract discretionary data (rest)
            discretionary = remaining[7:] if len(remaining) > 7 else ''
            
            return {
                'Track2_PAN': pan,
                'Track2_Expiry': f"{expiry[2:4]}/{expiry[:2]}" if len(expiry) == 4 else expiry,
                'Track2_Service_Code': service_code,
                'Track2_Discretionary': discretionary
            }
            
        except Exception as e:
            return {'Track2_Error': str(e)}
    
    def _get_country_name(self, country_code: str) -> str:
        """Get country name from ISO country code"""
        country_codes = {
            '840': 'United States',
            '124': 'Canada', 
            '826': 'United Kingdom',
            '978': 'Euro Zone',
            '392': 'Japan',
            '036': 'Australia',
            '756': 'Switzerland'
        }
        return country_codes.get(country_code, f'Unknown ({country_code})')
    
    def discover_applications(self) -> List[str]:
        """Discover available EMV applications"""
        print("\n🔍 Discovering EMV Applications...")
        
        applications = []
        
        # Common EMV AID prefixes to try
        common_aids = [
            'A0 00 00 00 03 10 10',     # Visa Debit/Credit
            'A0 00 00 00 03 20 10',     # Visa Electron
            'A0 00 00 00 04 10 10',     # MasterCard Credit/Debit
            'A0 00 00 00 04 30 60',     # MasterCard Maestro
            'A0 00 00 00 25 01',        # American Express
            'A0 00 00 00 25 01 04',     # American Express
            'A0 00 00 00 03',           # Visa (generic)
            'A0 00 00 00 04',           # MasterCard (generic)
            'A0 00 00 00 25',           # American Express (generic)
        ]
        
        # Try selecting each common AID
        for aid in common_aids:
            if self.select_application(aid):
                applications.append(aid)
                print(f"✅ Found application: {aid}")
            else:
                print(f"❌ Application not present: {aid}")
        
        # Try PSE (Payment System Environment)
        pse_aids = [
            '31 50 41 59 2E 53 59 53 2E 44 44 46 30 31',  # 1PAY.SYS.DDF01
            '32 50 41 59 2E 53 59 53 2E 44 44 46 30 31'   # 2PAY.SYS.DDF01
        ]
        
        for pse_aid in pse_aids:
            print(f"\n🔍 Trying PSE: {pse_aid}")
            if self.select_application(pse_aid):
                applications.append(pse_aid)
                print(f"✅ PSE found: {pse_aid}")
                # Could enumerate applications from PSE here
        
        return applications
    
    def display_all_data(self):
        """Display all extracted card data in organized format"""
        print("\n" + "="*80)
        print("📊 COMPLETE CARD DATA EXTRACTION RESULTS")
        print("="*80)
        
        # Payment Data Section
        payment_data = self.extract_payment_data()
        if payment_data:
            print("\n💳 PAYMENT CARD INFORMATION:")
            print("-" * 50)
            for key, value in payment_data.items():
                if isinstance(value, dict):
                    print(f"  {key.replace('_', ' ').title()}:")
                    for sub_key, sub_value in value.items():
                        print(f"    {sub_key.replace('_', ' ').title()}: {sub_value}")
                else:
                    print(f"  {key.replace('_', ' ').title()}: {value}")
        
        # Raw EMV Data Section
        print(f"\n📋 RAW EMV DATA ({len(self.card_data)} fields):")
        print("-" * 50)
        for tag in sorted(self.card_data.keys()):
            tag_name = self.emv_tags.get(tag, f"Unknown Tag")
            value = self.card_data[tag]
            
            # Try to decode as ASCII for readable fields
            try:
                if tag in ['50', '5F20', '9F12']:  # Application Label, Cardholder Name, Preferred Name
                    ascii_value = bytes.fromhex(value).decode('ascii', errors='ignore').strip()
                    if ascii_value and ascii_value.isprintable():
                        print(f"  {tag}: {tag_name}")
                        print(f"       Hex: {value}")
                        print(f"       ASCII: '{ascii_value}'")
                        continue
            except:
                pass
            
            print(f"  {tag}: {tag_name}")
            print(f"       Value: {value}")
            
            # Add interpretation for specific tags
            if tag == '5A':  # PAN
                pan = self._decode_bcd(value).rstrip('F')
                print(f"       Decoded PAN: {pan}")
            elif tag == '5F24':  # Expiry Date
                if len(value) >= 4:
                    exp_date = f"{value[2:4]}/{value[:2]}"
                    print(f"       Expiry: {exp_date}")
            elif tag == '57':  # Track 2
                track2_data = self._decode_track2(value)
                print(f"       Track 2 Decoded: {track2_data}")
    
    def run_complete_extraction(self):
        """Run complete card data extraction process"""
        print("="*80)
        print("🚀 NFCClone V4.05 - Complete Card Data Extraction Test")
        print("="*80)
        print("Hardware: Windows 10 + ACR122U")
        print("Purpose: Extract ALL available card data (PAN, CVV, Name, etc.)")
        print("="*80)
        
        # Step 1: Connect to card
        if not self.connect_to_card():
            return False
        
        # Step 2: Discover applications
        applications = self.discover_applications()
        
        if not applications:
            print("❌ No EMV applications found on card")
            print("This might be:")
            print("  - A non-EMV card (magnetic stripe only)")
            print("  - A card with different AID structure")
            print("  - A contactless-disabled card")
        
        # Step 3: Read all records from all files
        all_records = self.read_all_records()
        
        # Step 4: Display all extracted data
        self.display_all_data()
        
        # Step 5: Summary
        print(f"\n📊 EXTRACTION SUMMARY:")
        print("-" * 50)
        print(f"  EMV Tags Found: {len(self.card_data)}")
        print(f"  Applications Found: {len(applications)}")
        print(f"  Records Read: {sum(len(records) for records in all_records.values())}")
        
        # Check for key payment data
        key_data_found = []
        if '5A' in self.card_data:
            key_data_found.append("PAN (Primary Account Number)")
        if '5F20' in self.card_data:
            key_data_found.append("Cardholder Name")
        if '5F24' in self.card_data:
            key_data_found.append("Expiry Date")
        if '57' in self.card_data:
            key_data_found.append("Track 2 Data")
        if '50' in self.card_data:
            key_data_found.append("Application Label")
        
        print(f"  Key Data Found: {len(key_data_found)}")
        for item in key_data_found:
            print(f"    ✅ {item}")
        
        return True

def main():
    """Main execution function"""
    print("Please place your EMV card on the ACR122 reader and press Enter...")
    input()
    
    # Create extractor and run complete extraction
    extractor = EMVDataExtractor()
    
    try:
        success = extractor.run_complete_extraction()
        if success:
            print("\n🎉 Card data extraction completed successfully!")
        else:
            print("\n❌ Card data extraction failed")
            
    except KeyboardInterrupt:
        print("\n\n🛑 Extraction stopped by user")
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
    finally:
        if extractor.connection:
            try:
                extractor.connection.disconnect()
                print("🔌 Card connection closed")
            except:
                pass
    
    print("\nPress Enter to exit...")
    input()

if __name__ == "__main__":
    main()
