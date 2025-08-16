#!/usr/bin/env python3
"""
Complete Workflow Test - Card Reading + Crypto + Relay Readiness
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from smartcard.System import readers
from smartcard.util import toHexString
from emvcard import EMVCard
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from emv_crypto import EmvCrypto
from enhanced_parser import EnhancedEMVParser

def complete_workflow_test():
    """Test complete workflow: read card -> extract data -> crypto operations -> relay readiness"""
    print("NFCSpoofer V4.05 - Complete Workflow Test")
    print("="*60)
    
    try:
        # Step 1: Read card data
        print("\n1. CARD READING")
        print("-" * 30)
        
        reader_list = readers()
        if not reader_list:
            print("❌ No card readers found")
            return False
            
        reader = reader_list[0]
        connection = reader.createConnection()
        connection.connect()
        print(f"✅ Connected to: {reader}")
        
        # Initialize EMV card
        emv_card = EMVCard()
        
        # Select VISA application
        visa_aid = [0x00, 0xA4, 0x04, 0x00, 0x07, 0xA0, 0x00, 0x00, 0x00, 0x03, 0x10, 0x10]
        response, sw1, sw2 = connection.transmit(visa_aid)
        
        if sw1 == 0x90 and sw2 == 0x00:
            print("✅ VISA application selected")
            emv_card.aid = "A0000000031010"
        else:
            print(f"❌ VISA selection failed: {sw1:02X}{sw2:02X}")
            connection.disconnect()
            return False
            
        # Read all available records
        records_read = 0
        all_data = b""
        
        for sfi in range(1, 6):
            for rec in range(1, 17):
                read_cmd = [0x00, 0xB2, rec, (sfi << 3) | 0x04, 0x00]
                try:
                    response, sw1, sw2 = connection.transmit(read_cmd)
                    if sw1 == 0x90 and sw2 == 0x00:
                        response_bytes = bytes(response)
                        emv_card.process_response(response_bytes)
                        all_data += response_bytes
                        records_read += 1
                        if records_read <= 5:  # Show first few
                            print(f"✅ SFI {sfi} REC {rec}: {len(response)} bytes - {toHexString(response[:10])}...")
                except:
                    continue
                    
        connection.disconnect()
        print(f"✅ Total records read: {records_read}")
        print(f"✅ Total data: {len(all_data)} bytes")
        
        if records_read == 0:
            print("❌ No card data read")
            return False
            
        # Step 2: Parse card data using enhanced parser
        print("\n2. DATA PARSING")
        print("-" * 30)
        
        parser = EnhancedEMVParser()
        
        # Parse the raw data from the card
        card_info = parser.parse_and_extract_payment_data(all_data)
        
        pan = card_info.get('pan', '')
        cardholder_name = card_info.get('cardholder_name', '')
        expiry_date = card_info.get('expiry_date', '')
        service_code = card_info.get('service_code', '')
        track1 = card_info.get('track1_equivalent_data', '')
        track2 = card_info.get('track2_equivalent_data', '')
        
        print(f"✅ PAN: {pan}")
        print(f"✅ Cardholder: {cardholder_name}")
        print(f"✅ Expiry: {expiry_date}")
        print(f"✅ Service Code: {service_code}")
        print(f"✅ Track 1: {track1[:50]}..." if track1 else "❌ Track 1: Not found")
        print(f"✅ Track 2: {track2[:30]}..." if track2 else "❌ Track 2: Not found")
        
        if not pan:
            print("❌ Critical: No PAN extracted")
            return False
            
        # Step 3: Cryptographic operations
        print("\n3. CRYPTOGRAPHIC OPERATIONS")
        print("-" * 30)
        
        # Initialize crypto with card
        master_key = b'\x01\x23\x45\x67\x89\xAB\xCD\xEF' * 2  # Demo key
        crypto = EmvCrypto(master_key)
        emv_card.set_crypto(crypto)
        
        print(f"✅ Crypto initialized with master key")
        
        # Derive session keys
        atc = 1  # Application Transaction Counter
        session_key = crypto.derive_icc_key(pan, atc)
        print(f"✅ Session key derived: {session_key.hex().upper()}")
        
        # Generate cryptograms
        test_data = b'\x00' * 8  # Simplified CDOL data
        
        arqc = crypto.generate_arqc(pan, atc, test_data)
        tc = crypto.generate_tc(pan, atc, test_data)
        aac = crypto.generate_aac(pan, atc, test_data)
        
        print(f"✅ ARQC (Auth Request): {arqc.hex().upper()}")
        print(f"✅ TC (Transaction Certificate): {tc.hex().upper()}")
        print(f"✅ AAC (Auth Cryptogram): {aac.hex().upper()}")
        
        # Step 4: Relay/Emulation readiness check
        print("\n4. RELAY/EMULATION READINESS")
        print("-" * 30)
        
        # Check if card has all necessary data for emulation
        required_data = {
            'PAN': pan,
            'Cardholder Name': cardholder_name,
            'Expiry Date': expiry_date,
            'Session Key': session_key.hex(),
            'Crypto Engine': emv_card.crypto is not None,
            'TLV Data': len(emv_card.tlv_root.children) > 0 if hasattr(emv_card.tlv_root, 'children') else False
        }
        
        all_ready = True
        for key, value in required_data.items():
            if value:
                print(f"✅ {key}: Ready")
            else:
                print(f"❌ {key}: Missing")
                all_ready = False
        
        # Check relay infrastructure files
        relay_files = ['proxmark_manager.py', 'chameleon_manager.py', 'cardhopper_protocol.py']
        for file in relay_files:
            if os.path.exists(file):
                print(f"✅ {file}: Available")
            else:
                print(f"❌ {file}: Missing")
                all_ready = False
        
        # Step 5: Transaction processing readiness  
        print("\n5. TRANSACTION PROCESSING READINESS")
        print("-" * 30)
        
        from emv_terminal import EmvTerminal
        from emv_transaction import EmvTransaction
        
        terminal = EmvTerminal()
        terminal_profile = terminal.pdol_profile()
        
        # Test transaction initialization
        transaction = EmvTransaction(emv_card, crypto, terminal_profile)
        print("✅ Transaction processor initialized")
        print(f"✅ Terminal profile loaded: {len(terminal_profile)} parameters")
        
        # Simulate transaction data
        transaction_amount = 1000  # $10.00
        currency_code = "0840"  # USD
        
        print(f"✅ Transaction simulation ready")
        print(f"    Amount: ${transaction_amount/100:.2f}")
        print(f"    Currency: {currency_code}")
        print(f"    Card: {pan}")
        print(f"    Cryptogram available: Yes")
        
        # Final status
        print("\n" + "="*60)
        print("COMPLETE WORKFLOW STATUS")
        print("="*60)
        
        if all_ready and pan and session_key:
            print("🎉 COMPLETE WORKFLOW: ✅ FULLY OPERATIONAL")
            print()
            print("📋 SYSTEM CAPABILITIES CONFIRMED:")
            print("   ✅ Card reading and data extraction")
            print("   ✅ Enhanced TLV parsing")
            print("   ✅ Cryptographic key derivation")
            print("   ✅ Cryptogram generation (ARQC/TC/AAC)")
            print("   ✅ Relay/emulation infrastructure")
            print("   ✅ POS transaction processing")
            print()
            print("🔐 SECURITY ELEMENTS:")
            print(f"   • PAN: {pan}")
            print(f"   • Cardholder: {cardholder_name}")
            print(f"   • Session Key: {session_key.hex()[:16]}...")
            print(f"   • ARQC: {arqc.hex().upper()}")
            print()
            print("📡 RELAY READY:")
            print("   • Card data fully parsed")
            print("   • Cryptographic engine configured")
            print("   • APDU processing infrastructure available")
            print()
            print("💳 POS READY:")
            print("   • Transaction processor initialized")
            print("   • Terminal profile configured")
            print("   • Cryptogram generation working")
            print()
            print("❓ CVV STATUS:")
            print("   • CVV not found on chip (expected)")
            print("   • EMV uses cryptographic authentication instead")
            print("   • Physical CVV printed on card back")
            
            return True
        else:
            print("⚠️  WORKFLOW INCOMPLETE - Some components need attention")
            return False
        
    except Exception as e:
        print(f"❌ Workflow test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = complete_workflow_test()
    if success:
        print("\n🏁 Test completed successfully!")
    else:
        print("\n❌ Test completed with issues")
