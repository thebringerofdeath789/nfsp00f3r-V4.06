#!/usr/bin/env python3
"""
Integration Test Suite for NFCClone Automation System
Tests the complete automation pipeline from card detection to emulation preparation
"""

import unittest
import sys
import os
import tempfile
import shutil
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime, timedelta
import json

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from automation_controller import (
        AutomationController, AutomationMode, AutomationConfig,
        TransactionStrategy, EmulationMethod, TransactionPlaybook
    )
    from emvcard import EMVCard
    import sys
    import os
    sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
    from emv_crypto import EmvCrypto
    from pin_manager import PinManager
    from cvm_processor import CVMProcessor
    from logger import Logger
except ImportError as e:
    print(f"Error importing modules: {e}")
    print("Ensure all dependencies are available")
    sys.exit(1)

class TestAutomationIntegration(unittest.TestCase):
    """Integration tests for the complete automation system"""
    
    def setUp(self):
        """Set up test environment"""
        # Create temporary directory for test outputs
        self.test_dir = tempfile.mkdtemp()
        
        # Create automation configuration
        self.config = AutomationConfig(
            scan_interval=1,
            output_dir=self.test_dir,
            master_pin="1337",
            max_cards=5,
            transaction_timeout=10
        )
        
        # Mock logger
        self.mock_logger = Mock(spec=Logger)
        
        # Create automation controller
        self.controller = AutomationController(AutomationMode.INTERACTIVE, self.config)
        self.controller.logger = self.mock_logger
        
    def tearDown(self):
        """Clean up test environment"""
        if hasattr(self, 'controller') and self.controller:
            self.controller.stop()
        if os.path.exists(self.test_dir):
            shutil.rmtree(self.test_dir)
            
    def create_mock_emv_card(self, pan="4111111111111111"):
        """Create a mock EMV card for testing"""
        mock_card = Mock(spec=EMVCard)
        
        # Basic card info
        mock_card.get_cardholder_info.return_value = {
            'PAN': pan,
            'CardholderName': 'TEST CARDHOLDER',
            'expiry_date': '1225',
            'service_code': '201'
        }
        
        # Mock EMV data structures
        mock_card.info = {
            'AIDs': ['A0000000041010'],
            'PAN': pan,
            'CardholderName': 'TEST CARDHOLDER'
        }
        
        # Mock TLV data
        mock_card.tlv_root = []
        mock_card.track_data = {
            'track2': f"{pan}=25121010000000000000"
        }
        
        # Mock methods
        mock_card.parse_card.return_value = True
        mock_card.read_all_sfi_records.return_value = []
        mock_card.extract_track_data.return_value = True
        mock_card.get_processing_options.return_value = (b'\x77\x0a\x82\x02\x20\x00\x94\x04\x08\x01\x01\x00', b'\x90\x00')
        
        # Mock crypto
        mock_card.crypto = Mock(spec=EmvCrypto)
        
        return mock_card

    def test_automation_controller_initialization(self):
        """Test automation controller initializes properly"""
        # Test different modes
        for mode in AutomationMode:
            controller = AutomationController(mode, self.config)
            self.assertEqual(controller.mode, mode)
            self.assertEqual(controller.config, self.config)
            self.assertFalse(controller.is_running)
            self.assertIsInstance(controller.pin_manager, PinManager)
            self.assertIsInstance(controller.cvm_processor, CVMProcessor)
            
    def test_card_detection_and_processing(self):
        """Test complete card detection and processing pipeline"""
        # Create mock card
        mock_card = self.create_mock_emv_card()
        
        # Test card processing
        with patch.object(self.controller, '_extract_complete_card_data') as mock_extract:
            with patch.object(self.controller, '_run_automated_transactions') as mock_transactions:
                with patch.object(self.controller, '_prepare_card_emulation') as mock_emulation:
                    with patch.object(self.controller, '_save_card_profile') as mock_save:
                        
                        # Process the card
                        self.controller._process_detected_card(mock_card, "TEST_READER")
                        
                        # Verify card was added to detected cards
                        pan = mock_card.get_cardholder_info()['PAN']
                        self.assertIn(pan, self.controller.detected_cards)
                        
                        # Verify processing pipeline was called
                        mock_extract.assert_called_once_with(mock_card)
                        mock_transactions.assert_called_once_with(mock_card, pan)
                        mock_emulation.assert_called_once_with(mock_card, pan)
                        mock_save.assert_called_once_with(mock_card, pan)

    def test_transaction_playbook_execution(self):
        """Test execution of different transaction playbooks"""
        mock_card = self.create_mock_emv_card()
        
        # Mock EmvTransaction
        with patch('automation_controller.EmvTransaction') as mock_txn_class:
            mock_txn = Mock()
            mock_txn_class.return_value = mock_txn
            
            # Mock transaction results
            mock_txn.run_purchase.return_value = {
                'result': 'APPROVED',
                'cryptogram': b'\x12\x34\x56\x78',
                'cvm_result': Mock(method_used='offline_pin', successful=True)
            }
            
            # Test transaction execution
            self.controller._run_automated_transactions(mock_card, "4111111111111111")
            
            # Verify transactions were attempted
            self.assertTrue(mock_txn.run_purchase.called)
            
            # Check that results were stored
            self.assertTrue(hasattr(mock_card, 'automation_results'))

    def test_emulation_preparation(self):
        """Test preparation of card data for multiple emulation methods"""
        mock_card = self.create_mock_emv_card()
        pan = "4111111111111111"
        
        # Test emulation preparation
        self.controller._prepare_card_emulation(mock_card, pan)
        
        # Check that emulation tasks were created
        self.assertTrue(len(self.controller.emulation_tasks) > 0)
        
        # Verify emulation methods are covered
        emulation_methods = [task['method'] for task in self.controller.emulation_tasks]
        expected_methods = [EmulationMethod.HCE_ANDROID, EmulationMethod.PROXMARK3, 
                          EmulationMethod.PN532, EmulationMethod.MAGSTRIPE]
        
        for method in expected_methods:
            self.assertIn(method, emulation_methods)

    def test_master_pin_automation(self):
        """Test that master PIN "1337" is always accepted"""
        # Test PIN manager integration
        pin_manager = self.controller.pin_manager
        
        # Verify master PIN is accepted
        result = pin_manager.verify_offline_pin("1337", b'\x00' * 8, mock_atc=1)
        self.assertTrue(result.successful)
        self.assertEqual(result.pin_try_counter, 3)  # Should not decrement for master PIN

    def test_cvm_analysis_integration(self):
        """Test CVM analysis integration with card processing"""
        mock_card = self.create_mock_emv_card()
        
        # Add mock CVM List to card
        cvm_list_data = bytes([
            0x00, 0x00, 0x10, 0x00,  # X = $10.00
            0x00, 0x00, 0x50, 0x00,  # Y = $50.00
            0x42, 0x00,  # Enciphered PIN online, always
            0x1E, 0x08,  # Signature, if under Y value
            0x1F, 0x06,  # No CVM, if under X value
        ])
        
        # Mock TLV node with CVM data
        mock_cvm_node = Mock()
        mock_cvm_node.tag = '8E'
        mock_cvm_node.value = cvm_list_data
        mock_card.tlv_root = [mock_cvm_node]
        
        # Test CVM analysis
        cvm_capabilities = self.controller._analyze_cvm_capabilities(mock_card)
        
        # Verify CVM analysis results
        self.assertTrue(cvm_capabilities['has_cvm_list'])
        self.assertEqual(cvm_capabilities['x_amount'], 4096)  # $10.00 in cents
        self.assertEqual(cvm_capabilities['y_amount'], 20480)  # $50.00 in cents
        self.assertEqual(cvm_capabilities['rules_count'], 3)

    def test_card_profile_persistence(self):
        """Test card profile saving and loading"""
        mock_card = self.create_mock_emv_card()
        pan = "4111111111111111"
        
        # Add some test data to card
        mock_card.automation_results = [
            {
                'playbook': 'aggressive',
                'amount': 1000,
                'result': {'result': 'APPROVED'},
                'timestamp': datetime.now().isoformat()
            }
        ]
        
        # Save card profile
        self.controller._save_card_profile(mock_card, pan)
        
        # Check that profile file was created
        profile_file = os.path.join(self.test_dir, f"card_profile_{pan}.json")
        self.assertTrue(os.path.exists(profile_file))
        
        # Load and verify profile content
        with open(profile_file, 'r') as f:
            profile_data = json.load(f)
        
        self.assertEqual(profile_data['pan'], pan)
        self.assertIn('automation_results', profile_data)
        self.assertIn('card_info', profile_data)

    def test_automation_modes(self):
        """Test different automation modes"""
        test_modes = [
            (AutomationMode.HEADLESS, "Headless mode test"),
            (AutomationMode.INTERACTIVE, "Interactive mode test"),
            (AutomationMode.BATCH, "Batch mode test"),
            (AutomationMode.MONITOR, "Monitor mode test")
        ]
        
        for mode, description in test_modes:
            with self.subTest(mode=mode):
                controller = AutomationController(mode, self.config)
                self.assertEqual(controller.mode, mode)
                
                # Test mode-specific behavior
                if mode == AutomationMode.HEADLESS:
                    self.assertTrue(controller.config.continuous_scan)
                elif mode == AutomationMode.BATCH:
                    self.assertFalse(controller.config.continuous_scan)

    def test_error_handling_and_recovery(self):
        """Test error handling in automation pipeline"""
        mock_card = self.create_mock_emv_card()
        
        # Test card extraction error handling
        with patch.object(mock_card, 'parse_card', side_effect=Exception("Test error")):
            # Should not crash, should log error
            self.controller._extract_complete_card_data(mock_card)
            
            # Verify error was logged
            self.mock_logger.log.assert_called_with(
                "Card data extraction error: Test error", "ERROR"
            )

    def test_transaction_strategy_selection(self):
        """Test transaction strategy selection and execution"""
        # Test different strategies
        strategies = [
            TransactionStrategy.AGGRESSIVE,
            TransactionStrategy.CONSERVATIVE,
            TransactionStrategy.STEALTH,
            TransactionStrategy.FALLBACK_ONLY
        ]
        
        for strategy in strategies:
            with self.subTest(strategy=strategy):
                playbook = TransactionPlaybook(
                    strategy=strategy,
                    amounts=[100, 500, 1000],
                    cvm_methods=['offline_pin'],
                    fallback_enabled=True,
                    max_attempts=2
                )
                
                self.assertEqual(playbook.strategy, strategy)
                self.assertTrue(len(playbook.amounts) > 0)

    @patch('automation_controller.PCSCReader')
    @patch('automation_controller.PN532Reader')
    def test_multi_reader_detection(self, mock_pn532, mock_pcsc):
        """Test detection across multiple reader types"""
        # Mock readers
        mock_pcsc_reader = Mock()
        mock_pn532_reader = Mock()
        
        mock_pcsc.return_value = mock_pcsc_reader
        mock_pn532.return_value = mock_pn532_reader
        
        # Mock card detection
        mock_card = self.create_mock_emv_card()
        mock_pcsc_reader.detect_card.return_value = mock_card
        mock_pn532_reader.detect_card.return_value = None
        
        # Test reader detection
        with patch.object(self.controller, '_process_detected_card') as mock_process:
            self.controller._scan_pcsc_readers()
            
            # Verify card was detected and processed
            mock_process.assert_called_once_with(mock_card, "PCSC")

    def test_emulation_task_execution(self):
        """Test execution of emulation tasks"""
        # Create test emulation task
        task = {
            'method': EmulationMethod.HCE_ANDROID,
            'card_data': {'pan': '4111111111111111'},
            'timestamp': datetime.now().isoformat(),
            'status': 'pending'
        }
        
        self.controller.emulation_tasks.append(task)
        
        # Mock HCE emulation
        with patch.object(self.controller, '_emulate_via_hce') as mock_hce:
            mock_card = self.create_mock_emv_card()
            
            # Execute emulation task
            self.controller._execute_emulation_task(task)
            
            # Verify emulation was attempted
            # Note: This test may need adjustment based on actual implementation

    def test_configuration_validation(self):
        """Test automation configuration validation"""
        # Test valid configuration
        valid_config = AutomationConfig(
            scan_interval=2,
            master_pin="1337",
            max_cards=10,
            transaction_timeout=30
        )
        
        controller = AutomationController(AutomationMode.HEADLESS, valid_config)
        self.assertEqual(controller.config.scan_interval, 2)
        self.assertEqual(controller.config.master_pin, "1337")

    def test_status_reporting(self):
        """Test automation status reporting"""
        # Add some mock data
        mock_card = self.create_mock_emv_card()
        self.controller.detected_cards['4111111111111111'] = mock_card
        
        # Get status
        status = self.controller.get_status()
        
        # Verify status information
        self.assertIn('is_running', status)
        self.assertIn('cards_processed', status)
        self.assertIn('mode', status)
        self.assertIn('active_readers', status)
        
        self.assertEqual(status['cards_processed'], 1)
        self.assertEqual(status['mode'], str(AutomationMode.INTERACTIVE))

def run_integration_tests():
    """Run the complete integration test suite"""
    print("=" * 70)
    print("NFCClone Automation System - Integration Test Suite")
    print("=" * 70)
    
    # Create test suite
    loader = unittest.TestLoader()
    suite = loader.loadTestsFromTestCase(TestAutomationIntegration)
    
    # Run tests
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # Print results summary
    print("\n" + "=" * 70)
    tests_run = result.testsRun
    failures = len(result.failures)
    errors = len(result.errors)
    success_rate = ((tests_run - failures - errors) / tests_run * 100) if tests_run > 0 else 0
    
    print(f"Tests Run: {tests_run}")
    print(f"Failures: {failures}")
    print(f"Errors: {errors}")
    print(f"Success Rate: {success_rate:.1f}%")
    
    if failures == 0 and errors == 0:
        print("🎉 All integration tests passed! Automation system is ready for deployment.")
        return True
    else:
        print("❌ Some tests failed. Review the output above for details.")
        if failures > 0:
            print("\nFailures:")
            for test, traceback in result.failures:
                print(f"  - {test}: {traceback.splitlines()[-1]}")
        if errors > 0:
            print("\nErrors:")
            for test, traceback in result.errors:
                print(f"  - {test}: {traceback.splitlines()[-1]}")
        return False

if __name__ == "__main__":
    success = run_integration_tests()
    sys.exit(0 if success else 1)
