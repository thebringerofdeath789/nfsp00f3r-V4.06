#!/usr/bin/env python3
# =====================================================================
# File: hardware_test_acr122.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-15
#
# Description:
#   Hardware validation script for Windows 10 + ACR122U deployment.
#   Tests PCSC reader detection, card scanning, and integration with
#   NFCClone automation system.
#
# Hardware Requirements:
#   - Windows 10 64-bit
#   - Python 3.9
#   - ACR122U USB NFC Reader
#   - Smart Card service running
# =====================================================================

import os
import sys
import time
import logging
from typing import List, Optional, Dict, Any

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from smartcard.System import readers
    from smartcard.CardConnection import CardConnection
    from smartcard.CardMonitoring import CardMonitor, CardObserver
    from smartcard.util import toHexString, toBytes
    from smartcard.Exceptions import CardConnectionException, NoCardException
    print("✅ Smartcard library imported successfully")
except ImportError as e:
    print(f"❌ Error importing smartcard library: {e}")
    print("Please install pyscard: pip install pyscard")
    sys.exit(1)
except Exception as e:
    print(f"❌ Unexpected error importing smartcard: {e}")
    sys.exit(1)

class ACR122HardwareTest:
    """Hardware validation for ACR122U on Windows 10"""
    
    def __init__(self):
        self.available_readers = []
        self.acr122_reader = None
        self.connection = None
        self.test_results = {}
        
    def detect_acr122(self) -> bool:
        """Detect and validate ACR122 reader"""
        print("🔍 Detecting PCSC readers...")
        
        try:
            self.available_readers = readers()
            print(f"📱 Found {len(self.available_readers)} PCSC readers:")
            
            for i, reader in enumerate(self.available_readers):
                reader_name = str(reader)
                print(f"  {i+1}. {reader_name}")
                
                if "ACR122" in reader_name:
                    self.acr122_reader = reader
                    print(f"  ✅ ACR122 detected: {reader_name}")
                    
            if self.acr122_reader is None:
                print("❌ No ACR122 reader found!")
                print("Please check:")
                print("  - ACR122U is connected via USB")
                print("  - Drivers are installed")
                print("  - Smart Card service is running")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ Error detecting readers: {e}")
            return False
    
    def test_reader_connection(self) -> bool:
        """Test basic reader connectivity"""
        print("\n🔧 Testing reader connection...")
        
        try:
            self.connection = self.acr122_reader.createConnection()
            print("✅ Connection created successfully")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def test_card_detection(self) -> bool:
        """Test card detection capabilities"""
        print("\n📱 Testing card detection...")
        print("Please place a card on the ACR122 reader...")
        
        max_attempts = 10
        attempt = 0
        
        while attempt < max_attempts:
            try:
                self.connection.connect()
                atr = self.connection.getATR()
                atr_hex = toHexString(atr)
                
                print(f"✅ Card detected!")
                print(f"  ATR: {atr_hex}")
                print(f"  ATR Length: {len(atr)} bytes")
                
                # Basic card type detection
                if atr_hex.startswith("3B 8F 80 01 80 4F 0C A0 00 00 03 06"):
                    print("  💳 Detected: EMV Payment Card")
                elif atr_hex.startswith("3B"):
                    print("  💳 Detected: ISO 14443 Type A card")
                else:
                    print("  💳 Detected: Unknown card type")
                
                self.connection.disconnect()
                return True
                
            except NoCardException:
                attempt += 1
                print(f"  Waiting for card... ({attempt}/{max_attempts})")
                time.sleep(2)
                continue
                
            except CardConnectionException as e:
                if "No smart card inserted" in str(e):
                    attempt += 1
                    print(f"  Waiting for card... ({attempt}/{max_attempts})")
                    time.sleep(2)
                    continue
                else:
                    print(f"❌ Card error: {e}")
                    return False
                    
            except Exception as e:
                print(f"❌ Unexpected error: {e}")
                return False
        
        print("❌ No card detected after waiting 20 seconds")
        print("Please ensure:")
        print("  - Card is placed correctly on reader")
        print("  - Card is supported (ISO 14443 Type A/B)")
        print("  - Reader LED indicates card presence")
        return False
    
    def test_apdu_communication(self) -> bool:
        """Test basic APDU communication"""
        print("\n💬 Testing APDU communication...")
        
        try:
            # Send SELECT command (basic APDU)
            select_cmd = [0x00, 0xA4, 0x04, 0x00, 0x00]  # SELECT command
            
            self.connection.connect()
            response, sw1, sw2 = self.connection.transmit(select_cmd)
            
            status = (sw1 << 8) | sw2
            print(f"✅ APDU sent successfully")
            print(f"  Command: {toHexString(select_cmd)}")
            print(f"  Response: {toHexString(response)} {sw1:02X}{sw2:02X}")
            print(f"  Status: 0x{status:04X}")
            
            if status == 0x9000:
                print("  ✅ Command executed successfully")
            elif status == 0x6A82:
                print("  ℹ️  File not found (expected for generic SELECT)")
            else:
                print(f"  ⚠️  Unusual status code: 0x{status:04X}")
            
            self.connection.disconnect()
            return True
            
        except Exception as e:
            print(f"❌ APDU communication failed: {e}")
            return False
    
    def test_nfcclone_integration(self) -> bool:
        """Test integration with NFCClone system"""
        print("\n🔗 Testing NFCClone integration...")
        
        try:
            # Test import of NFCClone components
            try:
                from cardreader_pcsc import PCSCCardReader
                print("✅ PCSCCardReader import successful")
            except ImportError as e:
                print(f"❌ PCSCCardReader import failed: {e}")
                return False
            
            # Test reader initialization
            try:
                pcsc_reader = PCSCCardReader()
                available = len(pcsc_reader._readers)
                print(f"✅ NFCClone PCSC integration working")
                print(f"  Available readers: {available}")
                
                for i, reader in enumerate(pcsc_reader._readers):
                    reader_name = str(reader)
                    if "ACR122" in reader_name:
                        print(f"  ✅ ACR122 detected in NFCClone: {reader_name}")
                        
            except Exception as e:
                print(f"❌ NFCClone PCSC integration failed: {e}")
                return False
                
            return True
            
        except Exception as e:
            print(f"❌ NFCClone integration test failed: {e}")
            return False
    
    def run_hardware_validation(self) -> Dict[str, bool]:
        """Run complete hardware validation suite"""
        print("=" * 60)
        print("🚀 NFCClone V4.05 - ACR122 Hardware Validation")
        print("=" * 60)
        print(f"Platform: Windows 10 64-bit")
        print(f"Python: {sys.version}")
        print(f"Date: {time.strftime('%Y-%m-%d %H:%M:%S')}")
        print("=" * 60)
        
        tests = [
            ("Reader Detection", self.detect_acr122),
            ("Reader Connection", self.test_reader_connection),
            ("Card Detection", self.test_card_detection),
            ("APDU Communication", self.test_apdu_communication),
            ("NFCClone Integration", self.test_nfcclone_integration),
        ]
        
        results = {}
        
        for test_name, test_func in tests:
            try:
                result = test_func()
                results[test_name] = result
                if not result:
                    print(f"\n❌ {test_name} failed - stopping validation")
                    break
            except Exception as e:
                print(f"\n❌ {test_name} crashed: {e}")
                results[test_name] = False
                break
        
        # Print summary
        print("\n" + "=" * 60)
        print("📊 Hardware Validation Results")
        print("=" * 60)
        
        passed = 0
        total = len(results)
        
        for test_name, result in results.items():
            status = "✅ PASS" if result else "❌ FAIL"
            print(f"  {test_name:<25} {status}")
            if result:
                passed += 1
        
        print("=" * 60)
        print(f"Summary: {passed}/{total} tests passed")
        
        if passed == total:
            print("🎉 All hardware validation tests PASSED!")
            print("✅ System ready for NFCClone automation testing")
            print("\nNext steps:")
            print("  1. Run: python automation_simple.py")
            print("  2. Select demo mode to test complete pipeline")
            print("  3. Test with real payment cards")
        else:
            print("❌ Hardware validation incomplete")
            print("Please resolve failing tests before proceeding")
        
        return results

def main():
    """Main hardware test execution"""
    test = ACR122HardwareTest()
    results = test.run_hardware_validation()
    
    # Exit with appropriate code
    if all(results.values()):
        sys.exit(0)  # Success
    else:
        sys.exit(1)  # Failure

if __name__ == "__main__":
    main()
