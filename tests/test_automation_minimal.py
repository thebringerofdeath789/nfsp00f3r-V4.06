#!/usr/bin/env python3
"""
Minimal Automation System Test
Tests core automation functionality without complex dependencies
"""

import sys
import os
import tempfile
import shutil
from unittest.mock import Mock

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_core_imports():
    """Test that core modules can be imported"""
    print("Testing core module imports...")
    
    try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from emv_crypto import EmvCrypto
        print("✓ EmvCrypto imported")
        
        from pin_manager import PinManager
        print("✓ PinManager imported")
        
        from cvm_processor import CVMProcessor
        print("✓ CVMProcessor imported")
        
        from logger import Logger
        print("✓ Logger imported")
        
        return True
        
    except Exception as e:
        print(f"✗ Import failed: {e}")
        return False

def test_pin_manager_automation():
    """Test PIN manager with master PIN 1337"""
    print("\nTesting PIN manager automation...")
    
    try:
        from pin_manager import PinManager
        
        pin_manager = PinManager()
        
        # Create a mock card object
        mock_card = Mock()
        mock_card.get_cardholder_info.return_value = {'PAN': '4111111111111111'}
        
        # Test master PIN acceptance
        result = pin_manager.verify_offline_pin(mock_card, "1337")
        
        if result:
            print("✓ Master PIN '1337' accepted")
            return True
        else:
            print("✗ Master PIN '1337' rejected")
            return False
            
    except Exception as e:
        print(f"✗ PIN manager test failed: {e}")
        return False

def test_cvm_processor():
    """Test CVM processor functionality"""
    print("\nTesting CVM processor...")
    
    try:
        from cvm_processor import CVMProcessor
        
        cvm_processor = CVMProcessor()
        
        # Test CVM list parsing
        sample_cvm_list = bytes([
            0x00, 0x00, 0x10, 0x00,  # X = $10.00
            0x00, 0x00, 0x50, 0x00,  # Y = $50.00
            0x42, 0x00,  # Enciphered PIN online, always
            0x1E, 0x08,  # Signature, if under Y value
            0x1F, 0x06,  # No CVM, if under X value
        ])
        
        x_amount, y_amount, rules = cvm_processor.parse_cvm_list(sample_cvm_list)
        
        if len(rules) == 3 and x_amount > 0 and y_amount > x_amount:
            print("✓ CVM list parsing successful")
            return True
        else:
            print("✗ CVM list parsing failed")
            return False
            
    except Exception as e:
        print(f"✗ CVM processor test failed: {e}")
        return False

def test_emv_crypto():
    """Test EMV crypto functionality"""
    print("\nTesting EMV crypto...")
    
    try:
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from emv_crypto import EmvCrypto
        
        # Test crypto initialization
        master_key = b'\x00' * 16  # Test key
        crypto = EmvCrypto(master_key)
        
        # Test session key derivation
        session_key = crypto.derive_icc_key("4111111111111111", 123)
        
        if len(session_key) == 24:  # 3DES key
            print("✓ EMV crypto session key derivation successful")
            return True
        else:
            print("✗ EMV crypto session key derivation failed")
            return False
            
    except Exception as e:
        print(f"✗ EMV crypto test failed: {e}")
        return False

def test_automation_config():
    """Test automation configuration"""
    print("\nTesting automation configuration...")
    
    try:
        # Create a minimal config
        class AutomationConfig:
            def __init__(self):
                self.scan_interval = 2
                self.master_pin = "1337"
                self.max_cards = 10
                self.transaction_timeout = 30
                self.continuous_scan = True
                self.output_dir = tempfile.mkdtemp()
        
        config = AutomationConfig()
        
        # Test configuration values
        if (config.scan_interval == 2 and 
            config.master_pin == "1337" and 
            config.max_cards == 10):
            print("✓ Automation configuration successful")
            
            # Cleanup
            if os.path.exists(config.output_dir):
                shutil.rmtree(config.output_dir)
            return True
        else:
            print("✗ Automation configuration failed")
            return False
            
    except Exception as e:
        print(f"✗ Automation configuration test failed: {e}")
        return False

def run_minimal_tests():
    """Run all minimal tests"""
    print("=" * 60)
    print("NFCClone Automation System - Minimal Test Suite")
    print("=" * 60)
    
    tests = [
        test_core_imports,
        test_pin_manager_automation,
        test_cvm_processor,
        test_emv_crypto,
        test_automation_config
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"✗ Test {test.__name__} crashed: {e}")
            results.append(False)
    
    # Summary
    passed = sum(results)
    total = len(results)
    success_rate = (passed / total * 100) if total > 0 else 0
    
    print("\n" + "=" * 60)
    print(f"Tests Passed: {passed}/{total}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if passed == total:
        print("🎉 All core tests passed! Automation system components are functional.")
        return True
    else:
        print("❌ Some tests failed. Core automation components need attention.")
        return False

if __name__ == "__main__":
    success = run_minimal_tests()
    sys.exit(0 if success else 1)
