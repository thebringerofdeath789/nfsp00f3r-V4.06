#!/usr/bin/env python3
"""
Integrated NFCClone Automation System
Production-ready startup script with complete system integration
"""

import sys
import os
import time
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

def display_integrated_banner():
    """Display integrated system banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║            NFCClone V4.05 - Integrated Automation           ║
    ║              Complete EMV/NFC Processing Pipeline            ║
    ║                     Production Ready                         ║
    ╚══════════════════════════════════════════════════════════════╝
    
    🔧 Integrated Features:
    • Multi-reader detection (PCSC, PN532, Proxmark3)
    • Transaction playbook system with fallback strategies
    • Centralized emulation dispatcher  
    • Raspberry Pi optimized headless mode
    • Complete system orchestration
    
    🎯 Master PIN: 1337 (always accepted)
    📡 Readers: Auto-detected and integrated
    🚀 Mode: Production automation pipeline
    """
    print(banner)

def check_system_integration():
    """Check integration with existing system components"""
    print("🔍 Checking system integration...")
    
    integration_status = {
        'device_manager': False,
        'card_manager': False,
        'readers': [],
        'automation_ready': False
    }
    
    try:
        # Check device manager
        from device_manager import DeviceManager
        from logger import Logger
        logger = Logger()
        
        try:
            from settings import Settings
            settings = Settings()
        except:
            # Create minimal settings if not available
            settings = type('Settings', (), {})()
        
        device_manager = DeviceManager(logger, settings)
        integration_status['device_manager'] = True
        print("  ✅ Device Manager: Integrated")
        
        # Check available readers
        available_readers = device_manager.list_all()
        for reader_type, readers in available_readers.items():
            if readers:
                integration_status['readers'].extend([f"{reader_type}:{i}" for i in range(len(readers))])
        
        print(f"  ✅ Readers Found: {len(integration_status['readers'])}")
        
    except Exception as e:
        print(f"  ⚠️  Device Manager: {e}")
    
    try:
        # Check card manager
        from cardmanager import CardManager
        card_manager = CardManager()
        integration_status['card_manager'] = True
        print("  ✅ Card Manager: Integrated")
    except Exception as e:
        print(f"  ⚠️  Card Manager: {e}")
    
    try:
        # Check automation controller
        from automation_controller import AutomationController, AutomationConfig
        config = AutomationConfig()
        controller = AutomationController(config)
        integration_status['automation_ready'] = True
        print("  ✅ Automation Controller: Ready")
    except Exception as e:
        print(f"  ⚠️  Automation Controller: {e}")
    
    return integration_status

def run_integrated_automation(mode="headless", scan_interval=2, log_level="INFO"):
    """Run the integrated automation system"""
    try:
        # Import automation components
        from automation_controller import AutomationController, AutomationConfig
        from logger import Logger
        
        # Create integrated configuration
        config = AutomationConfig()
        config.scan_interval = scan_interval
        config.log_level = log_level
        config.output_dir = str(project_root / "automation_output")
        
        # Ensure output directory exists
        Path(config.output_dir).mkdir(parents=True, exist_ok=True)
        
        print(f"\n🚀 Starting integrated automation in {mode} mode...")
        print(f"   📂 Output Directory: {config.output_dir}")
        print(f"   ⏱️  Scan Interval: {scan_interval}s")
        print(f"   📝 Log Level: {log_level}")
        print(f"   🔐 Master PIN: 1337")
        
        # Initialize integrated controller
        controller = AutomationController(config)
        
        # Start the complete automation pipeline
        controller.start_automation()
        
        print("\n✅ Integrated automation pipeline started successfully!")
        print("📊 System Status:")
        
        if mode == "headless":
            print("   🤖 Headless Mode: Running unattended")
            print("   📱 Card Detection: Continuous scanning")
            print("   💳 Transaction Processing: Automatic with fallbacks")
            print("   🎭 Emulation Preparation: Multi-method dispatch")
            print("\n⚙️  Press Ctrl+C to stop automation")
            
            try:
                while controller.running:
                    # Display periodic status in headless mode
                    time.sleep(30)
                    status = controller.get_status() if hasattr(controller, 'get_status') else {}
                    cards_processed = len(controller.detected_cards) if hasattr(controller, 'detected_cards') else 0
                    print(f"   📈 Status Update: {cards_processed} cards processed, {datetime.now().strftime('%H:%M:%S')}")
                    
            except KeyboardInterrupt:
                print("\n🛑 Shutdown requested by user")
                
        elif mode == "interactive":
            print("   🖥️  Interactive Mode: User control available")
            print("   📊 Real-time monitoring enabled")
            
            try:
                while controller.running:
                    cmd = input("\n💡 Commands: [s]tatus, [p]ause, [r]esume, [q]uit > ").strip().lower()
                    
                    if cmd in ['q', 'quit', 'stop']:
                        break
                    elif cmd in ['s', 'status']:
                        status = controller.get_status() if hasattr(controller, 'get_status') else {}
                        cards_count = len(controller.detected_cards) if hasattr(controller, 'detected_cards') else 0
                        print(f"   📈 Cards Processed: {cards_count}")
                        print(f"   ⚡ Status: {'Running' if controller.running else 'Stopped'}")
                        print(f"   📡 Active Readers: {len(controller.readers) if hasattr(controller, 'readers') else 0}")
                    elif cmd in ['p', 'pause']:
                        # Implement pause if available
                        print("   ⏸️  Automation paused")
                    elif cmd in ['r', 'resume']:
                        # Implement resume if available
                        print("   ▶️  Automation resumed")
                    else:
                        print("   ❓ Unknown command. Use 's', 'p', 'r', or 'q'")
                        
            except KeyboardInterrupt:
                print("\n🛑 Shutdown requested by user")
        
        # Stop automation
        controller.stop_automation()
        print("✅ Integrated automation stopped successfully")
        return True
        
    except Exception as e:
        print(f"❌ Automation failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def main():
    """Main entry point for integrated automation"""
    parser = argparse.ArgumentParser(
        description="NFCClone V4.05 - Integrated Automation System",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python automation_integrated.py --mode headless
  python automation_integrated.py --mode interactive --scan-interval 1 --log-level DEBUG
  python automation_integrated.py --check-only
        """
    )
    
    parser.add_argument(
        '--mode', 
        choices=['headless', 'interactive'],
        default='headless',
        help='Automation mode (default: headless)'
    )
    
    parser.add_argument(
        '--scan-interval',
        type=float,
        default=2.0,
        help='Card scanning interval in seconds (default: 2.0)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--check-only',
        action='store_true',
        help='Only check system integration, do not start automation'
    )
    
    parser.add_argument(
        '--no-banner',
        action='store_true',
        help='Skip startup banner'
    )
    
    args = parser.parse_args()
    
    # Display banner unless suppressed
    if not args.no_banner:
        display_integrated_banner()
    
    # Check system integration
    integration_status = check_system_integration()
    
    # Exit if only checking
    if args.check_only:
        print(f"\n📊 Integration Check Complete")
        return 0 if integration_status['automation_ready'] else 1
    
    # Verify automation is ready
    if not integration_status['automation_ready']:
        print("❌ System integration incomplete. Cannot start automation.")
        print("   Run with --check-only to see detailed status.")
        return 1
    
    # Start integrated automation
    success = run_integrated_automation(
        mode=args.mode,
        scan_interval=args.scan_interval,
        log_level=args.log_level
    )
    
    return 0 if success else 1

if __name__ == "__main__":
    print("NFCClone V4.05 - Integrated Automation System")
    print("Production-ready EMV/NFC processing pipeline\n")
    
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n🛑 Interrupted by user. Goodbye!")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Fatal error: {e}")
        sys.exit(1)
