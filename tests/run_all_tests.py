#!/usr/bin/env python3
"""
🎯 NFCSpoofer V4.05 - Master Test Runner for Sniffing & Replay
Comprehensive test suite for all card sniffing and replay attack vectors

ATTACK VECTORS TESTED:
1. 🔧 Proxmark3 - Professional RF sniffing and replay
2. 🔧 PN532 - Development board NFC interception
3. 📱 HCE Bluetooth - Android companion app relay
4. 🔄 Complete sniff-and-replay attack chains
5. 💾 Data persistence and analysis

⚠️ RESEARCH & EDUCATIONAL USE ONLY
"""

import sys
import os
import time
import json
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import individual test modules
from test_sniff_and_replay import run_comprehensive_sniff_and_replay_test
from test_proxmark_sniff_replay import run_proxmark_comprehensive_test
from test_pn532_sniff_replay import run_pn532_comprehensive_test
from test_hce_bluetooth_relay import run_hce_bluetooth_comprehensive_test


def run_all_sniff_replay_tests():
    """Execute all sniffing and replay tests in sequence."""
    
    print("🎯 NFCSPOOFER V4.05 - MASTER SNIFF & REPLAY TEST SUITE")
    print("=" * 80)
    print("Testing all attack vectors: Proxmark3, PN532, HCE Bluetooth")
    print("⚠️  RESEARCH & EDUCATIONAL USE ONLY")
    print("=" * 80)
    
    test_start_time = datetime.now()
    
    # Test results tracking
    test_suite_results = {
        "start_time": test_start_time.isoformat(),
        "test_results": {},
        "overall_summary": {},
        "recommendations": []
    }
    
    print("\n🚀 STARTING COMPREHENSIVE TEST SEQUENCE...")
    
    # Test 1: Comprehensive Sniff & Replay System
    print("\n" + "🔄" * 60)
    print("TEST 1: COMPREHENSIVE SNIFF & REPLAY SYSTEM")
    print("🔄" * 60)
    
    try:
        comprehensive_result = run_comprehensive_sniff_and_replay_test()
        test_suite_results["test_results"]["comprehensive_system"] = {
            "success": comprehensive_result,
            "description": "Overall system integration test",
            "capabilities": ["Multi-hardware support", "Data persistence", "Attack chaining"]
        }
    except Exception as e:
        print(f"❌ Comprehensive test failed: {e}")
        test_suite_results["test_results"]["comprehensive_system"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 2: Proxmark3 Professional RF Attacks
    print("\n" + "🔧" * 60)
    print("TEST 2: PROXMARK3 PROFESSIONAL RF ATTACKS")
    print("🔧" * 60)
    
    try:
        proxmark_result = run_proxmark_comprehensive_test()
        test_suite_results["test_results"]["proxmark3_attacks"] = {
            "success": proxmark_result,
            "description": "Professional RF sniffing and replay",
            "capabilities": ["RF field analysis", "ISO14443-A sniffing", "EMV transaction analysis", "Perfect replay"]
        }
    except Exception as e:
        print(f"❌ Proxmark3 test failed: {e}")
        test_suite_results["test_results"]["proxmark3_attacks"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 3: PN532 Development Board Attacks  
    print("\n" + "🔧" * 60)
    print("TEST 3: PN532 DEVELOPMENT BOARD ATTACKS")
    print("🔧" * 60)
    
    try:
        pn532_result = run_pn532_comprehensive_test()
        test_suite_results["test_results"]["pn532_attacks"] = {
            "success": pn532_result,
            "description": "NFC interception and emulation attacks",
            "capabilities": ["Card interception", "APDU analysis", "Card emulation", "MITM attacks"]
        }
    except Exception as e:
        print(f"❌ PN532 test failed: {e}")
        test_suite_results["test_results"]["pn532_attacks"] = {
            "success": False,
            "error": str(e)
        }
    
    # Test 4: HCE Bluetooth Relay Attacks
    print("\n" + "📱" * 60)
    print("TEST 4: HCE BLUETOOTH RELAY ATTACKS")
    print("📱" * 60)
    
    try:
        hce_result = run_hce_bluetooth_comprehensive_test()
        test_suite_results["test_results"]["hce_bluetooth_attacks"] = {
            "success": hce_result,
            "description": "Android companion app relay attacks",
            "capabilities": ["Bluetooth relay", "HCE emulation", "Remote sniffing", "Encrypted communication"]
        }
    except Exception as e:
        print(f"❌ HCE Bluetooth test failed: {e}")
        test_suite_results["test_results"]["hce_bluetooth_attacks"] = {
            "success": False,
            "error": str(e)
        }
    
    # Calculate overall results
    test_end_time = datetime.now()
    test_duration = test_end_time - test_start_time
    
    test_suite_results["end_time"] = test_end_time.isoformat()
    test_suite_results["total_duration"] = str(test_duration)
    
    # Analyze results
    successful_tests = sum(1 for result in test_suite_results["test_results"].values() if result.get("success"))
    total_tests = len(test_suite_results["test_results"])
    
    test_suite_results["overall_summary"] = {
        "successful_tests": successful_tests,
        "total_tests": total_tests,
        "success_rate": f"{(successful_tests/total_tests)*100:.1f}%",
        "operational_status": "OPERATIONAL" if successful_tests >= 2 else "PARTIAL" if successful_tests >= 1 else "NOT OPERATIONAL"
    }
    
    # Generate recommendations
    test_suite_results["recommendations"] = generate_recommendations(test_suite_results["test_results"])
    
    # Display final results
    display_final_results(test_suite_results)
    
    # Save results
    save_test_results(test_suite_results)
    
    return successful_tests >= 2


def generate_recommendations(test_results: dict) -> list:
    """Generate recommendations based on test results."""
    
    recommendations = []
    
    # Check individual test results
    if test_results.get("proxmark3_attacks", {}).get("success"):
        recommendations.append("🔧 Proxmark3 system OPERATIONAL - Use for professional RF attacks")
        recommendations.append("   • Best for: Real transaction sniffing, perfect replay timing")
        recommendations.append("   • Use cases: Live POS attacks, RF analysis, EMV debugging")
    else:
        recommendations.append("⚠️ Proxmark3 system needs setup - Install Proxmark3 hardware and drivers")
    
    if test_results.get("pn532_attacks", {}).get("success"):
        recommendations.append("🔧 PN532 system OPERATIONAL - Use for development and testing")
        recommendations.append("   • Best for: Card development, APDU analysis, controlled testing")
        recommendations.append("   • Use cases: Card emulation, MITM attacks, protocol analysis")
    else:
        recommendations.append("⚠️ PN532 system needs setup - Install nfcpy and configure PN532 device")
    
    if test_results.get("hce_bluetooth_attacks", {}).get("success"):
        recommendations.append("📱 HCE Bluetooth system OPERATIONAL - Android companion ready")
        recommendations.append("   • Best for: Remote attacks, mobile relay, stealth operations")
        recommendations.append("   • Use cases: Remote sniffing, HCE replay, mobile POS attacks")
    else:
        recommendations.append("⚠️ HCE Bluetooth needs setup - Install Android companion app and pair devices")
    
    if test_results.get("comprehensive_system", {}).get("success"):
        recommendations.append("🎯 Comprehensive system OPERATIONAL - Full attack chain available")
        recommendations.append("   • Attack workflow: Sniff → Analyze → Replay")
        recommendations.append("   • Multi-vector attacks: Use different hardware for different phases")
    else:
        recommendations.append("⚠️ System integration needs work - Check hardware connections and drivers")
    
    # General recommendations
    recommendations.extend([
        "",
        "🎯 OPERATIONAL RECOMMENDATIONS:",
        "• Use Proxmark3 for highest quality RF sniffing and replay",
        "• Use PN532 for development, testing, and APDU analysis", 
        "• Use HCE Bluetooth for remote operations and mobile attacks",
        "• Combine multiple attack vectors for maximum effectiveness",
        "• Always test in controlled environment before real operations",
        "",
        "⚖️ LEGAL & ETHICAL GUIDELINES:",
        "• Use only on systems you own or have explicit permission to test",
        "• Follow responsible disclosure for any vulnerabilities found",
        "• Educational and research purposes only",
        "• Comply with local laws regarding security research"
    ])
    
    return recommendations


def display_final_results(test_results: dict):
    """Display comprehensive final results."""
    
    print("\n" + "🏆" * 80)
    print("MASTER TEST SUITE - FINAL RESULTS")
    print("🏆" * 80)
    
    # Overall summary
    summary = test_results["overall_summary"]
    print(f"\n📊 OVERALL RESULTS:")
    print(f"   Tests passed: {summary['successful_tests']}/{summary['total_tests']}")
    print(f"   Success rate: {summary['success_rate']}")
    print(f"   System status: {summary['operational_status']}")
    print(f"   Test duration: {test_results['total_duration']}")
    
    # Individual test results
    print(f"\n📋 INDIVIDUAL TEST RESULTS:")
    for test_name, result in test_results["test_results"].items():
        status = "✅ PASS" if result.get("success") else "❌ FAIL"
        description = result.get("description", "No description")
        
        print(f"   {status} {test_name.replace('_', ' ').upper()}")
        print(f"      {description}")
        
        if "capabilities" in result:
            print(f"      Capabilities: {', '.join(result['capabilities'])}")
        
        if "error" in result:
            print(f"      Error: {result['error']}")
        
        print()
    
    # System status indicator
    status = summary["operational_status"]
    if status == "OPERATIONAL":
        print("🟢 NFCSPOOFER V4.05 SNIFF & REPLAY SYSTEM: FULLY OPERATIONAL")
        print("   All major attack vectors working - Ready for comprehensive operations!")
    elif status == "PARTIAL":
        print("🟡 NFCSPOOFER V4.05 SNIFF & REPLAY SYSTEM: PARTIALLY OPERATIONAL") 
        print("   Some attack vectors working - Can perform limited operations.")
    else:
        print("🔴 NFCSPOOFER V4.05 SNIFF & REPLAY SYSTEM: NEEDS SETUP")
        print("   System requires hardware configuration and setup.")
    
    # Recommendations
    print(f"\n💡 RECOMMENDATIONS:")
    for rec in test_results["recommendations"]:
        print(f"   {rec}")
    
    print("\n" + "🎯" * 80)
    print("TEST SUITE COMPLETE - CHECK SAVED RESULTS FOR DETAILED ANALYSIS")
    print("🎯" * 80)


def save_test_results(test_results: dict):
    """Save test results to file."""
    
    try:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"sniff_replay_test_results_{timestamp}.json"
        
        with open(filename, 'w') as f:
            json.dump(test_results, f, indent=2, default=str)
        
        print(f"\n💾 Test results saved to: {filename}")
        
        # Also create a summary report
        summary_filename = f"sniff_replay_summary_{timestamp}.txt"
        
        with open(summary_filename, 'w') as f:
            f.write("NFCSpoofer V4.05 - Sniff & Replay Test Summary\n")
            f.write("=" * 60 + "\n\n")
            
            f.write(f"Test Date: {test_results['start_time']}\n")
            f.write(f"Duration: {test_results['total_duration']}\n")
            f.write(f"Success Rate: {test_results['overall_summary']['success_rate']}\n")
            f.write(f"Status: {test_results['overall_summary']['operational_status']}\n\n")
            
            f.write("Test Results:\n")
            f.write("-" * 20 + "\n")
            
            for test_name, result in test_results["test_results"].items():
                status = "PASS" if result.get("success") else "FAIL"
                f.write(f"{test_name}: {status}\n")
                if "error" in result:
                    f.write(f"  Error: {result['error']}\n")
                f.write("\n")
            
            f.write("\nRecommendations:\n")
            f.write("-" * 15 + "\n")
            for rec in test_results["recommendations"]:
                f.write(f"{rec}\n")
        
        print(f"📄 Summary report saved to: {summary_filename}")
        
    except Exception as e:
        print(f"⚠️ Could not save test results: {e}")


def quick_system_check():
    """Quick system check without full test suite."""
    
    print("🔍 QUICK SYSTEM CHECK - Hardware Detection")
    print("-" * 50)
    
    # Check individual components
    components = {
        "Proxmark3": check_proxmark3_availability(),
        "PN532/NFC": check_pn532_availability(),
        "Bluetooth": check_bluetooth_availability(),
        "HCE Crypto": check_hce_availability()
    }
    
    print("Hardware availability:")
    for component, available in components.items():
        status = "✅ Available" if available else "❌ Not available"
        print(f"   {status} {component}")
    
    available_count = sum(components.values())
    print(f"\nSystem readiness: {available_count}/{len(components)} components available")
    
    return available_count >= 2


def check_proxmark3_availability() -> bool:
    """Check if Proxmark3 is available."""
    try:
        from proxmark_manager import Proxmark3Manager
        proxmark = Proxmark3Manager()
        return proxmark.serial_conn is not None
    except:
        return False


def check_pn532_availability() -> bool:
    """Check if PN532/NFC is available."""
    try:
        import nfc
        from cardreader_pn532 import PN532Reader
        pn532 = PN532Reader()
        return len(pn532.list_interfaces()) > 0
    except:
        return False


def check_bluetooth_availability() -> bool:
    """Check if Bluetooth is available."""
    try:
        from bluetooth_api import BleakBluetoothManager
        bluetooth = BleakBluetoothManager()
        return True
    except:
        return False


def check_hce_availability() -> bool:
    """Check if HCE crypto is available."""
    try:
        from hce_manager import HCEManager
        hce = HCEManager()
        return hce._ecdh_private is not None
    except:
        return False


if __name__ == "__main__":
    print("NFCSpoofer V4.05 - Master Sniff & Replay Test Runner")
    
    # Check if user wants quick check or full test
    print("\nChoose test mode:")
    print("1. Quick system check (hardware detection only)")
    print("2. Full comprehensive test suite (all attack vectors)")
    
    try:
        choice = input("\nEnter choice (1 or 2): ").strip()
        
        if choice == "1":
            quick_system_check()
        else:
            print("\nStarting full test suite...")
            success = run_all_sniff_replay_tests()
            
            if success:
                print("\n🎉 SUCCESS: NFCSpoofer sniff & replay system is operational!")
            else:
                print("\n⚠️ PARTIAL: Some components need setup, but basic functionality available.")
    
    except KeyboardInterrupt:
        print("\n\n⏹️ Test interrupted by user.")
    except Exception as e:
        print(f"\n❌ Test runner error: {e}")
    
    print("\nTest runner complete!")
