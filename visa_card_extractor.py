#!/usr/bin/env python3
# =====================================================================
# File: visa_card_extractor.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-16
#
# Description:
#   Comprehensive Visa card data extraction tool for both Debit and Credit
#   cards. Extracts PAN, cardholder name, expiry date, service codes,
#   track data, CVV methods, and all available EMV application data.
#
# Target Applications:
#   - Visa Debit (A0000000032010)
#   - Visa Credit (A0000000031010)
#   - Visa Electron (A0000000032020)
#   - Visa Plus (A0000000038010)
# =====================================================================

import os
import sys
import time
import binascii
from typing import List, Dict, Optional, Tuple, Any

# Import smartcard libraries
try:
    from smartcard.System import readers
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    print("✅ Smartcard library loaded successfully")
except ImportError as e:
    print(f"❌ Failed to import smartcard library: {e}")
    print("Install with: pip install pyscard")
    sys.exit(1)

class VisaCardExtractor:
    """Comprehensive Visa card data extraction"""
    
    # Visa Application Identifiers
    VISA_AIDS = {
        'A0000000032010': 'Visa Debit',
        'A0000000031010': 'Visa Credit', 
        'A0000000032020': 'Visa Electron',
        'A0000000038010': 'Visa Plus',
        'A0000000033010': 'Visa Interlink',
        'A0000000980840': 'Visa Common Debit'
    }
    
    # EMV Data Object List (DOL) tags
    EMV_TAGS = {
        # Application Data
        '4F': 'Application Identifier (AID)',
        '50': 'Application Label',
        '87': 'Application Priority Indicator',
        '9F38': 'Processing Options Data Object List (PDOL)',
        
        # Cardholder Data  
        '5A': 'Application Primary Account Number (PAN)',
        '5F20': 'Cardholder Name',
        '5F24': 'Application Expiration Date',
        '5F25': 'Application Effective Date',
        '5F30': 'Service Code',
        '5F34': 'Application Primary Account Number (PAN) Sequence Number',
        
        # Track Data
        '57': 'Track 2 Equivalent Data',
        '9F1F': 'Track 1 Discretionary Data',
        '9F20': 'Track 2 Discretionary Data',
        
        # Card Verification
        '8C': 'Card Risk Management Data Object List 1 (CDOL1)',
        '8D': 'Card Risk Management Data Object List 2 (CDOL2)', 
        '8E': 'Cardholder Verification Method (CVM) List',
        '8F': 'Certification Authority Public Key Index',
        '90': 'Issuer Public Key Certificate',
        '9F32': 'Issuer Public Key Exponent',
        '9F46': 'ICC Public Key Certificate',
        '9F47': 'ICC Public Key Exponent',
        '9F48': 'ICC Public Key Remainder',
        
        # Application Control
        '82': 'Application Interchange Profile (AIP)',
        '94': 'Application File Locator (AFL)',
        '9F07': 'Application Usage Control',
        '9F08': 'Application Version Number',
        '9F42': 'Application Currency Code',
        '9F44': 'Application Currency Exponent',
        
        # Transaction Data
        '9F02': 'Amount, Authorized',
        '9F03': 'Amount, Other',
        '9F1A': 'Terminal Country Code',
        '9F33': 'Terminal Capabilities',
        '9F35': 'Terminal Type',
        '9F40': 'Additional Terminal Capabilities',
        
        # Cryptographic Data
        '9F26': 'Application Cryptogram',
        '9F27': 'Cryptogram Information Data',
        '9F36': 'Application Transaction Counter (ATC)',
        '9F13': 'Last Online Application Transaction Counter (ATC) Register',
        
        # Record Data
        '70': 'EMV Data Template',
        '77': 'Response Message Template Format 2',
        '80': 'Response Message Template Format 1',
    }
    
    def __init__(self):
        self.connection = None
        self.card_data = {}
        self.applications = []
        self.selected_app = None
        
    def connect_to_card(self) -> bool:
        """Connect to the first available card"""
        try:
            available_readers = readers()
            if not available_readers:
                print("❌ No card readers found")
                return False
            
            # Use first available reader (ACR122)
            reader = available_readers[0]
            print(f"🔍 Using reader: {reader}")
            
            self.connection = reader.createConnection()
            self.connection.connect()
            
            # Get ATR
            atr = self.connection.getATR()
            atr_hex = toHexString(atr)
            print(f"📱 Card ATR: {atr_hex}")
            
            return True
            
        except Exception as e:
            print(f"❌ Failed to connect to card: {e}")
            return False
    
    def send_apdu(self, apdu: List[int]) -> Tuple[List[int], int, int]:
        """Send APDU command and return response"""
        try:
            response, sw1, sw2 = self.connection.transmit(apdu)
            return response, sw1, sw2
        except Exception as e:
            print(f"❌ APDU transmission failed: {e}")
            return [], 0x6F, 0x00
    
    def parse_fci_template(self, response_data: List[int]) -> Dict[str, Any]:
        """Parse File Control Information (FCI) Template"""
        parsed_data = {}
        
        try:
            data = bytes(response_data)
            
            # Look for FCI Template (6F)
            if data.startswith(b'\x6F'):
                length = data[1]
                fci_data = data[2:2+length]
                
                # Parse TLV data within FCI
                parsed_data.update(self.parse_tlv_data(fci_data))
            
        except Exception as e:
            print(f"⚠️ FCI parsing error: {e}")
        
        return parsed_data
    
    def parse_tlv_data(self, data: bytes) -> Dict[str, Any]:
        """Parse TLV (Tag-Length-Value) encoded data"""
        parsed = {}
        offset = 0
        
        while offset < len(data):
            try:
                # Parse tag
                if offset >= len(data):
                    break
                    
                tag_byte = data[offset]
                offset += 1
                
                # Multi-byte tag handling
                if tag_byte & 0x1F == 0x1F:
                    tag = tag_byte.to_bytes(1, 'big')
                    while offset < len(data) and data[offset-1] & 0x80:
                        tag += data[offset].to_bytes(1, 'big')
                        offset += 1
                else:
                    tag = tag_byte.to_bytes(1, 'big')
                
                tag_hex = tag.hex().upper()
                
                # Parse length
                if offset >= len(data):
                    break
                    
                length_byte = data[offset]
                offset += 1
                
                if length_byte & 0x80 == 0:
                    # Short form
                    length = length_byte
                else:
                    # Long form
                    length_bytes = length_byte & 0x7F
                    if offset + length_bytes > len(data):
                        break
                    length = 0
                    for i in range(length_bytes):
                        length = (length << 8) + data[offset + i]
                    offset += length_bytes
                
                # Parse value
                if offset + length > len(data):
                    break
                    
                value = data[offset:offset + length]
                offset += length
                
                # Store parsed data
                tag_name = self.EMV_TAGS.get(tag_hex, f'Unknown Tag {tag_hex}')
                parsed[tag_hex] = {
                    'name': tag_name,
                    'value': value,
                    'hex': value.hex().upper(),
                    'ascii': self.safe_ascii_decode(value)
                }
                
            except Exception as e:
                print(f"⚠️ TLV parsing error at offset {offset}: {e}")
                break
        
        return parsed
    
    def safe_ascii_decode(self, data: bytes) -> str:
        """Safely decode bytes to ASCII, replacing non-printable characters"""
        try:
            # Try ASCII first
            result = data.decode('ascii', errors='ignore')
            # Filter out non-printable characters
            return ''.join(c if c.isprintable() or c.isspace() else '?' for c in result)
        except:
            return f"<binary data: {len(data)} bytes>"
    
    def discover_applications(self) -> List[Dict[str, Any]]:
        """Discover all payment applications on the card"""
        print("\n🔍 Discovering Payment Applications...")
        applications = []
        
        # Try to select Payment System Environment (PSE)
        pse_aids = [
            "1PAY.SYS.DDF01",  # Contact PSE
            "2PAY.SYS.DDF01"   # Contactless PSE
        ]
        
        for pse_aid in pse_aids:
            print(f"  🔍 Trying PSE: {pse_aid}")
            
            # Convert AID to bytes
            aid_bytes = pse_aid.encode('ascii')
            
            # SELECT command
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"    ✅ PSE found: {pse_aid}")
                
                # Parse PSE response
                pse_data = self.parse_fci_template(response)
                
                # Try to read PSE directory
                apps = self.read_pse_directory()
                applications.extend(apps)
            else:
                print(f"    ❌ PSE not found: {sw1:02X}{sw2:02X}")
        
        # Try direct AID selection for Visa applications
        print("  🔍 Trying direct Visa AID selection...")
        for aid_hex, app_name in self.VISA_AIDS.items():
            aid_bytes = bytes.fromhex(aid_hex)
            
            # SELECT command
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"    ✅ Found {app_name}: {aid_hex}")
                
                # Parse application data
                app_data = self.parse_fci_template(response)
                
                applications.append({
                    'aid': aid_hex,
                    'name': app_name,
                    'selection_response': response,
                    'fci_data': app_data,
                    'status': 'available'
                })
            else:
                print(f"    ❌ {app_name} not available: {sw1:02X}{sw2:02X}")
        
        self.applications = applications
        return applications
    
    def read_pse_directory(self) -> List[Dict[str, Any]]:
        """Read PSE directory to find applications"""
        applications = []
        
        try:
            # Read PSE record
            read_cmd = [0x00, 0xB2, 0x01, 0x0C, 0x00]  # READ RECORD
            response, sw1, sw2 = self.send_apdu(read_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                # Parse PSE record for application entries
                pse_data = self.parse_tlv_data(bytes(response))
                
                # Look for application templates (61)
                for tag, data in pse_data.items():
                    if tag == '61':  # Application Template
                        app_template = self.parse_tlv_data(data['value'])
                        
                        app_info = {}
                        for app_tag, app_data in app_template.items():
                            if app_tag == '4F':  # AID
                                app_info['aid'] = app_data['hex']
                            elif app_tag == '50':  # Application Label
                                app_info['name'] = app_data['ascii']
                        
                        if 'aid' in app_info:
                            applications.append(app_info)
            
        except Exception as e:
            print(f"⚠️ PSE directory reading error: {e}")
        
        return applications
    
    def select_application(self, aid_hex: str) -> bool:
        """Select a specific application by AID"""
        try:
            aid_bytes = bytes.fromhex(aid_hex)
            
            # SELECT command
            select_cmd = [0x00, 0xA4, 0x04, 0x00, len(aid_bytes)] + list(aid_bytes)
            response, sw1, sw2 = self.send_apdu(select_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print(f"✅ Selected application: {aid_hex}")
                
                # Parse and store FCI data
                self.selected_app = aid_hex
                app_data = self.parse_fci_template(response)
                self.card_data[aid_hex] = app_data
                
                return True
            else:
                print(f"❌ Failed to select application {aid_hex}: {sw1:02X}{sw2:02X}")
                return False
                
        except Exception as e:
            print(f"❌ Application selection error: {e}")
            return False
    
    def get_processing_options(self) -> Dict[str, Any]:
        """Get Processing Options (GPO) to retrieve AFL and AIP"""
        try:
            print("  📋 Getting Processing Options (GPO)...")
            
            # Minimal PDOL data (usually just zeros)
            pdol_data = b'\x83\x00'  # Basic PDOL
            
            # GET PROCESSING OPTIONS command
            gpo_cmd = [0x80, 0xA8, 0x00, 0x00, len(pdol_data)] + list(pdol_data)
            response, sw1, sw2 = self.send_apdu(gpo_cmd)
            
            if sw1 == 0x90 and sw2 == 0x00:
                print("    ✅ GPO successful")
                
                # Parse GPO response
                gpo_data = self.parse_tlv_data(bytes(response))
                
                return gpo_data
            else:
                print(f"    ❌ GPO failed: {sw1:02X}{sw2:02X}")
                return {}
                
        except Exception as e:
            print(f"❌ GPO error: {e}")
            return {}
    
    def read_application_records(self, afl_data: bytes) -> Dict[str, Any]:
        """Read all application records using AFL (Application File Locator)"""
        records = {}
        
        try:
            print("  📖 Reading Application Records...")
            
            # AFL format: [SFI|record_range|offline_records|auth_records]
            offset = 0
            record_num = 1
            
            while offset + 4 <= len(afl_data):
                sfi = afl_data[offset] >> 3  # Short File Identifier
                first_record = afl_data[offset + 1]
                last_record = afl_data[offset + 2]
                offline_auth_records = afl_data[offset + 3]
                
                print(f"    📄 Reading SFI {sfi}, Records {first_record}-{last_record}")
                
                # Read each record in the range
                for record in range(first_record, last_record + 1):
                    read_cmd = [0x00, 0xB2, record, (sfi << 3) | 0x04, 0x00]
                    response, sw1, sw2 = self.send_apdu(read_cmd)
                    
                    if sw1 == 0x90 and sw2 == 0x00:
                        print(f"      ✅ Record {record}: {len(response)} bytes")
                        
                        # Parse record data
                        record_data = self.parse_tlv_data(bytes(response))
                        records[f'SFI{sfi}_REC{record}'] = record_data
                    else:
                        print(f"      ❌ Record {record} failed: {sw1:02X}{sw2:02X}")
                
                offset += 4
            
        except Exception as e:
            print(f"❌ Record reading error: {e}")
        
        return records
    
    def extract_card_data(self, aid_hex: str) -> Dict[str, Any]:
        """Extract complete card data from selected application"""
        print(f"\n💳 Extracting data from {self.VISA_AIDS.get(aid_hex, 'Unknown')} ({aid_hex})")
        
        extracted_data = {
            'application': {
                'aid': aid_hex,
                'name': self.VISA_AIDS.get(aid_hex, 'Unknown Application')
            }
        }
        
        # Select application
        if not self.select_application(aid_hex):
            return extracted_data
        
        # Get FCI data
        if aid_hex in self.card_data:
            extracted_data['fci'] = self.card_data[aid_hex]
        
        # Get Processing Options
        gpo_data = self.get_processing_options()
        if gpo_data:
            extracted_data['gpo'] = gpo_data
            
            # Look for AFL in GPO response
            afl = None
            for tag, data in gpo_data.items():
                if tag == '94':  # AFL tag
                    afl = data['value']
                    break
            
            # Read application records if AFL found
            if afl:
                records = self.read_application_records(afl)
                extracted_data['records'] = records
        
        return extracted_data
    
    def format_card_data_display(self, card_data: Dict[str, Any]) -> str:
        """Format extracted card data for display"""
        output = []
        
        app_name = card_data.get('application', {}).get('name', 'Unknown')
        app_aid = card_data.get('application', {}).get('aid', 'Unknown')
        
        output.append("=" * 80)
        output.append(f"💳 {app_name} ({app_aid})")
        output.append("=" * 80)
        
        # Key payment data extraction
        pan = None
        cardholder_name = None
        expiry_date = None
        service_code = None
        track2_data = None
        
        # Search through all data sections
        for section_name in ['fci', 'gpo', 'records']:
            if section_name not in card_data:
                continue
                
            section_data = card_data[section_name]
            
            if section_name == 'records':
                # Search through all records
                for record_name, record_data in section_data.items():
                    pan, cardholder_name, expiry_date, service_code, track2_data = self.extract_payment_data(
                        record_data, pan, cardholder_name, expiry_date, service_code, track2_data
                    )
            else:
                # Search through section data
                pan, cardholder_name, expiry_date, service_code, track2_data = self.extract_payment_data(
                    section_data, pan, cardholder_name, expiry_date, service_code, track2_data
                )
        
        # Display key payment information
        output.append("\n🔑 KEY PAYMENT INFORMATION:")
        output.append(f"  💳 PAN (Primary Account Number): {pan or 'Not found'}")
        output.append(f"  👤 Cardholder Name: {cardholder_name or 'Not found'}")
        output.append(f"  📅 Expiry Date: {expiry_date or 'Not found'}")
        output.append(f"  🔧 Service Code: {service_code or 'Not found'}")
        output.append(f"  🎵 Track 2 Data: {track2_data or 'Not found'}")
        
        # Display all extracted data sections
        for section_name, section_data in card_data.items():
            if section_name == 'application':
                continue
                
            output.append(f"\n📋 {section_name.upper()} DATA:")
            
            if section_name == 'records':
                for record_name, record_data in section_data.items():
                    output.append(f"\n  📄 {record_name}:")
                    for tag, data in record_data.items():
                        output.append(f"    {tag}: {data['name']}")
                        output.append(f"         Value: {data['hex']}")
                        if data['ascii'] and data['ascii'].strip():
                            output.append(f"         ASCII: {data['ascii']}")
            else:
                for tag, data in section_data.items():
                    output.append(f"  {tag}: {data['name']}")
                    output.append(f"       Value: {data['hex']}")
                    if data['ascii'] and data['ascii'].strip():
                        output.append(f"       ASCII: {data['ascii']}")
        
        return "\n".join(output)
    
    def extract_payment_data(self, data_dict: Dict[str, Any], pan=None, name=None, expiry=None, service=None, track2=None) -> Tuple:
        """Extract key payment data from EMV data dictionary"""
        
        for tag, data in data_dict.items():
            if tag == '5A' and not pan:  # PAN
                pan_hex = data['hex']
                # Remove padding (F characters at end)
                pan_clean = pan_hex.rstrip('F')
                if len(pan_clean) % 2 == 1:
                    pan_clean = pan_clean[:-1]  # Remove last digit if odd length
                
                # Convert to readable PAN
                try:
                    pan_digits = ''.join([pan_clean[i:i+2] for i in range(0, len(pan_clean), 2)])
                    pan_digits = pan_digits.replace('', '')
                    # Convert hex pairs to decimal
                    pan = ''.join([str(int(pan_clean[i:i+2], 16)) if pan_clean[i:i+2] != 'FF' else '' for i in range(0, len(pan_clean), 2)])
                    pan = ''.join([c for c in pan if c.isdigit()])
                except:
                    pan = pan_hex
            
            elif tag == '5F20' and not name:  # Cardholder Name
                name = data['ascii'].strip()
            
            elif tag == '5F24' and not expiry:  # Expiry Date (YYMMDD)
                expiry_hex = data['hex']
                if len(expiry_hex) >= 6:
                    year = expiry_hex[:2]
                    month = expiry_hex[2:4]
                    expiry = f"{month}/{year}"
            
            elif tag == '5F30' and not service:  # Service Code
                service = data['hex']
            
            elif tag == '57' and not track2:  # Track 2 Equivalent Data
                track2_hex = data['hex']
                # Parse Track 2 data
                try:
                    # Track 2 contains PAN + separator (D) + expiry + service code + discretionary data
                    track2_ascii = ''.join([str(int(track2_hex[i:i+2], 16)) if track2_hex[i:i+2] not in ['FF', '00'] else 'D' if track2_hex[i:i+2] == 'D0' else '' for i in range(0, len(track2_hex), 2)])
                    track2 = track2_hex  # Keep hex for now
                except:
                    track2 = track2_hex
        
        return pan, name, expiry, service, track2
    
    def disconnect(self):
        """Disconnect from card"""
        if self.connection:
            try:
                self.connection.disconnect()
                print("📱 Disconnected from card")
            except:
                pass

def main():
    """Main extraction process"""
    print("=" * 80)
    print("🚀 NFCClone V4.05 - Visa Card Data Extractor")
    print("=" * 80)
    print("Target: Visa Debit & Credit Applications")
    print("Hardware: Windows 10 + ACR122U")
    print("=" * 80)
    
    extractor = VisaCardExtractor()
    
    try:
        # Connect to card
        if not extractor.connect_to_card():
            return 1
        
        # Discover applications
        applications = extractor.discover_applications()
        
        if not applications:
            print("❌ No Visa applications found on card")
            return 1
        
        print(f"\n✅ Found {len(applications)} Visa application(s)")
        
        # Extract data from each found application
        for app in applications:
            app_data = extractor.extract_card_data(app['aid'])
            
            # Display formatted results
            formatted_output = extractor.format_card_data_display(app_data)
            print(formatted_output)
            
            print("\n" + "=" * 80)
        
        print("🎉 Card data extraction completed successfully!")
        
    except KeyboardInterrupt:
        print("\n\n🛑 Extraction stopped by user")
    except Exception as e:
        print(f"\n❌ Extraction error: {e}")
        return 1
    finally:
        extractor.disconnect()
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
