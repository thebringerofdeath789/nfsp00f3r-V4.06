#!/usr/bin/env python3
"""
NFCClone Automation Startup Script
Simple startup script for automated EMV/NFC card cloning and emulation
Designed for Raspberry Pi and desktop deployment
"""

import sys
import os
import logging
from pathlib import Path
import time
import argparse
from datetime import datetime

# Add project root to Python path
project_root = Path(__file__).parent.absolute()
sys.path.insert(0, str(project_root))

try:
    from automation_controller import AutomationController, AutomationMode, AutomationConfig
    from logger import setup_logger
except ImportError as e:
    print(f"Error importing required modules: {e}")
    print("Ensure all dependencies are installed and you're in the correct directory")
    sys.exit(1)

def setup_automation_logging(log_level="INFO", log_file=None):
    """Set up logging for automation system"""
    if not log_file:
        log_file = f"automation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    log_path = project_root / "logs" / log_file
    log_path.parent.mkdir(exist_ok=True)
    
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(log_path),
            logging.StreamHandler(sys.stdout)
        ]
    )
    
    logger = logging.getLogger("automation_startup")
    logger.info(f"Automation logging initialized: {log_path}")
    return logger

def display_banner():
    """Display startup banner"""
    banner = """
    ╔══════════════════════════════════════════════════════════════╗
    ║                   NFCClone Automation System                 ║
    ║              Automated EMV/NFC Card Processing               ║
    ║                        Version 4.05                         ║
    ╚══════════════════════════════════════════════════════════════╝
    
    Features:
    • Automatic card detection (PCSC, PN532, Proxmark3)
    • Complete EMV data extraction
    • Multi-method emulation preparation
    • Offline PIN "1337" master key
    • Headless operation support
    """
    print(banner)

def check_hardware():
    """Basic hardware connectivity check"""
    print("Checking hardware connectivity...")
    
    try:
        # Check if we can import readers
        from cardreader_pcsc import PCSCReader
        from cardreader_pn532 import PN532Reader
        print("✓ Reader modules loaded")
    except ImportError as e:
        print(f"⚠ Reader import warning: {e}")
    
    # Additional hardware checks can be added here
    print("Hardware check completed")

def main():
    """Main startup function"""
    parser = argparse.ArgumentParser(
        description="NFCClone Automation System Startup",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    
    parser.add_argument(
        '--mode', 
        choices=['headless', 'interactive', 'batch', 'monitor'],
        default='headless',
        help='Automation mode (default: headless)'
    )
    
    parser.add_argument(
        '--log-level',
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Logging level (default: INFO)'
    )
    
    parser.add_argument(
        '--log-file',
        help='Custom log file name'
    )
    
    parser.add_argument(
        '--scan-interval',
        type=int,
        default=2,
        help='Card scanning interval in seconds (default: 2)'
    )
    
    parser.add_argument(
        '--no-banner',
        action='store_true',
        help='Skip startup banner'
    )
    
    parser.add_argument(
        '--config-file',
        help='Path to automation configuration file'
    )
    
    args = parser.parse_args()
    
    # Display banner unless suppressed
    if not args.no_banner:
        display_banner()
    
    # Set up logging
    logger = setup_automation_logging(args.log_level, args.log_file)
    
    try:
        # Check hardware
        check_hardware()
        
        # Create automation configuration
        config = AutomationConfig()
        if args.config_file and os.path.exists(args.config_file):
            logger.info(f"Loading configuration from: {args.config_file}")
            # TODO: Implement config file loading
        
        config.scan_interval = args.scan_interval
        
        # Initialize automation controller
        logger.info("Initializing automation controller...")
        mode = AutomationMode[args.mode.upper()]
        controller = AutomationController(mode, config)
        
        # Start automation
        logger.info(f"Starting automation in {args.mode} mode...")
        logger.info(f"Scan interval: {args.scan_interval} seconds")
        logger.info(f"Master PIN: 1337 (always accepted)")
        logger.info("Press Ctrl+C to stop")
        
        if mode == AutomationMode.HEADLESS:
            # Run headless automation
            controller.start()
            try:
                while controller.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
            finally:
                controller.stop()
        
        elif mode == AutomationMode.INTERACTIVE:
            # Interactive mode with user input
            controller.start()
            try:
                while controller.is_running:
                    cmd = input("\nCommands: [s]top, [p]ause, [r]esume, [st]atus, [h]elp\n> ").strip().lower()
                    
                    if cmd in ['s', 'stop']:
                        break
                    elif cmd in ['p', 'pause']:
                        controller.pause()
                        print("Automation paused")
                    elif cmd in ['r', 'resume']:
                        controller.resume()
                        print("Automation resumed")
                    elif cmd in ['st', 'status']:
                        print(f"Status: {'Running' if controller.is_running else 'Stopped'}")
                        print(f"Cards processed: {getattr(controller, 'cards_processed', 0)}")
                    elif cmd in ['h', 'help']:
                        print("Available commands:")
                        print("  s, stop - Stop automation")
                        print("  p, pause - Pause automation")
                        print("  r, resume - Resume automation")
                        print("  st, status - Show status")
                        print("  h, help - Show this help")
                    else:
                        print("Unknown command. Type 'h' for help.")
            
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
            finally:
                controller.stop()
        
        elif mode == AutomationMode.BATCH:
            # Batch processing mode
            logger.info("Batch mode - processing until no more cards found")
            controller.start()
            try:
                controller.wait_for_completion()
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
            finally:
                controller.stop()
        
        elif mode == AutomationMode.MONITOR:
            # Monitor mode - logging only
            logger.info("Monitor mode - logging card activity only")
            controller.start()
            try:
                while controller.is_running:
                    time.sleep(1)
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
            finally:
                controller.stop()
        
        logger.info("Automation system shutdown complete")
        
    except Exception as e:
        logger.error(f"Automation startup failed: {e}")
        logger.exception("Full error details:")
        return 1
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
