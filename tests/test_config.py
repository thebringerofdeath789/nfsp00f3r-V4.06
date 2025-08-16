"""
📋 NFCSpoofer V4.05 - Sniff & Replay Test Configuration
Test suite configuration and requirements for card sniffing and replay attacks

⚠️ RESEARCH & EDUCATIONAL USE ONLY - USE RESPONSIBLY
"""

# Test Suite Configuration
TEST_CONFIG = {
    "comprehensive_sniff_replay": {
        "name": "Comprehensive Sniff & Replay System",
        "description": "Master framework coordinating all attack vectors",
        "requirements": ["Hardware drivers", "Card database", "APDU parsers"],
        "capabilities": [
            "Multi-hardware coordination",
            "Data persistence and matching", 
            "Attack chain automation",
            "Transaction analysis"
        ],
        "use_cases": [
            "Complete attack workflow testing",
            "System integration validation",
            "Performance benchmarking"
        ]
    },
    
    "proxmark3_attacks": {
        "name": "Proxmark3 Professional RF Attacks",
        "description": "Professional-grade RF sniffing and replay",
        "requirements": ["Proxmark3 hardware", "Proxmark3 client", "Serial drivers"],
        "capabilities": [
            "RF field analysis and timing",
            "ISO14443-A protocol sniffing",
            "EMV transaction detection", 
            "Perfect timing replay",
            "Cryptographic analysis"
        ],
        "use_cases": [
            "Live POS transaction sniffing",
            "High-fidelity card cloning",
            "RF protocol analysis",
            "Professional penetration testing"
        ],
        "hardware_notes": "Requires genuine Proxmark3 (RDV4.01 or compatible)"
    },
    
    "pn532_attacks": {
        "name": "PN532 Development Board Attacks", 
        "description": "NFC interception and card emulation",
        "requirements": ["PN532 board", "nfcpy library", "USB/UART drivers"],
        "capabilities": [
            "Card presence detection",
            "APDU interception and logging",
            "Card emulation and spoofing",
            "Man-in-the-middle attacks",
            "ISO14443 Type A/B support"
        ],
        "use_cases": [
            "Card development and testing",
            "APDU protocol analysis", 
            "Controlled environment testing",
            "Card emulation research"
        ],
        "hardware_notes": "Works with PN532 breakout boards and modules"
    },
    
    "hce_bluetooth_relay": {
        "name": "HCE Bluetooth Relay Attacks",
        "description": "Android companion app relay system",
        "requirements": ["Android phone", "Companion app", "Bluetooth LE", "HCE support"],
        "capabilities": [
            "Remote card sniffing via Android",
            "HCE (Host Card Emulation)",
            "Encrypted Bluetooth communication",
            "Remote POS attacks",
            "Mobile relay operations"
        ],
        "use_cases": [
            "Remote sniffing operations",
            "Mobile payment testing",
            "Stealth relay attacks",
            "Multi-device coordination"
        ],
        "hardware_notes": "Requires rooted Android phone with HCE capability"
    }
}

# Hardware Requirements Matrix
HARDWARE_REQUIREMENTS = {
    "proxmark3": {
        "device": "Proxmark3 RDV4.01 or compatible",
        "connection": "USB",
        "software": "Proxmark3 client/firmware", 
        "operating_systems": ["Windows", "Linux", "macOS"],
        "cost": "$$$ (Professional)",
        "difficulty": "Advanced",
        "capabilities": "⭐⭐⭐⭐⭐ (Highest)"
    },
    
    "pn532": {
        "device": "PN532 NFC breakout board",
        "connection": "USB/UART/SPI/I2C",
        "software": "nfcpy, libnfc",
        "operating_systems": ["Windows", "Linux", "macOS"], 
        "cost": "$ (Affordable)",
        "difficulty": "Intermediate",
        "capabilities": "⭐⭐⭐ (Good)"
    },
    
    "android_hce": {
        "device": "Android smartphone (rooted)",
        "connection": "Bluetooth LE",
        "software": "Companion app, HCE framework",
        "operating_systems": ["Android 4.4+"],
        "cost": "$ (Phone required)",
        "difficulty": "Intermediate", 
        "capabilities": "⭐⭐⭐⭐ (Very Good)"
    },
    
    "generic_nfc": {
        "device": "ACR122U or similar",
        "connection": "USB", 
        "software": "PCSC drivers",
        "operating_systems": ["Windows", "Linux", "macOS"],
        "cost": "$ (Affordable)",
        "difficulty": "Beginner",
        "capabilities": "⭐⭐ (Basic)"
    }
}

# Attack Vector Comparison
ATTACK_VECTORS = {
    "rf_sniffing": {
        "description": "Passive RF field monitoring",
        "best_hardware": "Proxmark3",
        "stealth_level": "High",
        "success_rate": "Very High",
        "technical_difficulty": "Advanced",
        "legal_risk": "Medium-High"
    },
    
    "card_interception": {
        "description": "Active card-reader MITM",
        "best_hardware": "PN532", 
        "stealth_level": "Medium",
        "success_rate": "High",
        "technical_difficulty": "Intermediate", 
        "legal_risk": "High"
    },
    
    "bluetooth_relay": {
        "description": "Remote relay via mobile device",
        "best_hardware": "Android HCE",
        "stealth_level": "Very High",
        "success_rate": "High", 
        "technical_difficulty": "Intermediate",
        "legal_risk": "Medium"
    },
    
    "card_emulation": {
        "description": "Direct card impersonation",
        "best_hardware": "Proxmark3/HCE",
        "stealth_level": "Medium",
        "success_rate": "Very High",
        "technical_difficulty": "Advanced",
        "legal_risk": "Very High"
    }
}

# Test Environment Setup
TEST_ENVIRONMENT = {
    "controlled_lab": {
        "description": "Isolated test environment",
        "requirements": [
            "Test POS terminal",
            "Test cards (programmable)", 
            "Isolated network",
            "Monitoring equipment"
        ],
        "safety_level": "Maximum",
        "recommended": True
    },
    
    "personal_cards": {
        "description": "Testing on own payment cards",
        "requirements": [
            "Own credit/debit cards only",
            "Backup payment methods",
            "Bank notifications enabled"
        ],
        "safety_level": "High",
        "recommended": True,
        "warnings": ["Only use cards you own", "Monitor for unauthorized transactions"]
    },
    
    "public_testing": {
        "description": "Testing in public environments",
        "requirements": ["Explicit permission", "Legal authorization"],
        "safety_level": "Low",
        "recommended": False,
        "warnings": ["ILLEGAL WITHOUT PERMISSION", "High legal risk", "Ethical concerns"]
    }
}

# Legal and Ethical Guidelines
LEGAL_ETHICAL_GUIDELINES = {
    "research_use": {
        "description": "Academic and security research",
        "requirements": [
            "Educational institution affiliation",
            "Ethical review approval", 
            "Responsible disclosure plan",
            "No unauthorized access"
        ],
        "acceptable": True
    },
    
    "penetration_testing": {
        "description": "Authorized security testing",
        "requirements": [
            "Written authorization",
            "Defined scope and limitations",
            "Professional certification",
            "Client consent"
        ],
        "acceptable": True
    },
    
    "personal_security": {
        "description": "Testing own devices/cards",
        "requirements": [
            "Own devices only", 
            "No third-party data access",
            "Responsible disclosure",
            "No financial fraud"
        ],
        "acceptable": True
    },
    
    "unauthorized_use": {
        "description": "Any unauthorized access or fraud",
        "requirements": [],
        "acceptable": False,
        "warnings": [
            "ILLEGAL IN MOST JURISDICTIONS",
            "CRIMINAL PENALTIES APPLY",
            "ETHICAL VIOLATIONS",
            "DO NOT ENGAGE IN THIS ACTIVITY"
        ]
    }
}

# Quick Start Guide
QUICK_START_STEPS = [
    {
        "step": 1,
        "title": "Hardware Setup", 
        "description": "Connect and configure your chosen hardware",
        "actions": [
            "Install hardware drivers",
            "Connect device via USB/Bluetooth",
            "Verify device detection",
            "Test basic functionality"
        ]
    },
    {
        "step": 2, 
        "title": "Software Dependencies",
        "description": "Install required Python packages and libraries",
        "actions": [
            "pip install -r requirements.txt",
            "Install hardware-specific libraries",
            "Configure system permissions",
            "Test import statements"
        ]
    },
    {
        "step": 3,
        "title": "Quick System Check", 
        "description": "Verify system readiness",
        "actions": [
            "Run: python tests/run_all_tests.py",
            "Choose option 1 (Quick system check)",
            "Review hardware availability",
            "Fix any configuration issues"
        ]
    },
    {
        "step": 4,
        "title": "Full Test Suite",
        "description": "Execute comprehensive tests",
        "actions": [
            "Ensure test environment safety",
            "Run: python tests/run_all_tests.py", 
            "Choose option 2 (Full test suite)",
            "Review results and recommendations"
        ]
    },
    {
        "step": 5,
        "title": "Operational Deployment",
        "description": "Use system for authorized research/testing",
        "actions": [
            "Confirm legal authorization",
            "Set up controlled test environment",
            "Execute specific attack vectors",
            "Document results responsibly"
        ]
    }
]

# Troubleshooting Common Issues
TROUBLESHOOTING = {
    "proxmark3_not_detected": {
        "symptoms": ["Device not found", "Serial connection failed"],
        "solutions": [
            "Check USB cable and connection",
            "Install Proxmark3 drivers", 
            "Verify device shows in Device Manager",
            "Try different USB port",
            "Update Proxmark3 firmware"
        ]
    },
    
    "pn532_connection_failed": {
        "symptoms": ["NFC device not found", "nfcpy import errors"],
        "solutions": [
            "Install nfcpy: pip install nfcpy", 
            "Check USB connection",
            "Verify PN532 board power",
            "Install libusb drivers",
            "Check device permissions on Linux"
        ]
    },
    
    "bluetooth_pairing_failed": {
        "symptoms": ["Android app not connecting", "Bluetooth errors"],
        "solutions": [
            "Enable Bluetooth on both devices",
            "Clear Bluetooth cache on Android",
            "Re-pair devices from scratch", 
            "Check Android app permissions",
            "Ensure HCE is enabled"
        ]
    },
    
    "import_errors": {
        "symptoms": ["Module not found", "Import failed"],
        "solutions": [
            "Install missing packages: pip install -r requirements.txt",
            "Check Python path configuration",
            "Verify virtual environment activation",
            "Install system-specific dependencies"
        ]
    }
}

# Performance Expectations
PERFORMANCE_BENCHMARKS = {
    "proxmark3_rf_sniffing": {
        "setup_time": "5-10 seconds",
        "detection_rate": "95-99%",
        "replay_accuracy": "Near perfect",
        "range": "2-10cm", 
        "power_consumption": "Medium-High"
    },
    
    "pn532_interception": {
        "setup_time": "2-5 seconds", 
        "detection_rate": "90-95%",
        "replay_accuracy": "Very good",
        "range": "1-5cm",
        "power_consumption": "Low-Medium"
    },
    
    "hce_bluetooth_relay": {
        "setup_time": "10-30 seconds (pairing)",
        "detection_rate": "85-95%",
        "replay_accuracy": "Good-Very good", 
        "range": "10-100m (Bluetooth)",
        "power_consumption": "Low (phone-dependent)"
    }
}

if __name__ == "__main__":
    print("📋 NFCSpoofer V4.05 - Test Configuration Reference")
    print("=" * 60)
    
    print("\n🔧 Available Test Suites:")
    for test_id, config in TEST_CONFIG.items():
        print(f"\n   • {config['name']}")
        print(f"     {config['description']}")
        print(f"     Requirements: {', '.join(config['requirements'])}")
    
    print("\n🔧 Hardware Support:")
    for hw_id, specs in HARDWARE_REQUIREMENTS.items():
        print(f"\n   • {hw_id.upper()}: {specs['device']}")
        print(f"     Cost: {specs['cost']} | Difficulty: {specs['difficulty']} | Capabilities: {specs['capabilities']}")
    
    print("\n⚖️ LEGAL NOTICE:")
    print("   This software is for RESEARCH and EDUCATIONAL purposes only.")
    print("   Use only on systems you own or have explicit permission to test.")
    print("   Users are responsible for complying with all applicable laws.")
    
    print("\n🚀 Quick Start: python tests/run_all_tests.py")
    print("=" * 60)
