#!/usr/bin/env python3
"""
🔐 NFCSpoofer V4.05 - PIN Configuration Manager
Centralized PIN management for current card on reader

CURRENT CARD PIN CONFIGURATION:
- Card PIN: 6998 (actual PIN from card on reader)
- Previously used master PIN: 1337 (still available as fallback)

This module provides centralized PIN management for key derivation
and transaction processing.
"""

class PINConfiguration:
    """Centralized PIN configuration management"""
    
    # Current card PIN (from actual card on reader)
    CURRENT_CARD_PIN = "6998"
    
    # Fallback master PIN (for compatibility)
    MASTER_PIN = "1337"
    
    # PIN validation patterns
    COMMON_PINS = [
        "1234", "0000", "1111", "2222", "3333", "4444", "5555",
        "6666", "7777", "8888", "9999", "1337", "6998"
    ]
    
    @classmethod
    def get_current_pin(cls) -> str:
        """Get the current card PIN"""
        return cls.CURRENT_CARD_PIN
    
    @classmethod  
    def get_master_pin(cls) -> str:
        """Get the master PIN (fallback)"""
        return cls.MASTER_PIN
    
    @classmethod
    def get_all_pins(cls) -> list:
        """Get all PINs to try (current first, then fallbacks)"""
        return [cls.CURRENT_CARD_PIN, cls.MASTER_PIN] + cls.COMMON_PINS
    
    @classmethod
    def format_pin_block(cls, pin: str, format_type: int = 0) -> bytes:
        """Format PIN into PIN block format"""
        pin_length = len(pin)
        
        if format_type == 0:
            # ISO-0 PIN block format
            padded_pin = f"0{pin_length}{pin.ljust(14, 'F')}"
        elif format_type == 1:
            # ISO-1 PIN block format
            padded_pin = f"1{pin_length}{pin.ljust(14, '0')}"
        elif format_type == 2:
            # ISO-2 PIN block format  
            padded_pin = f"2{pin_length}{pin.ljust(14, 'F')}"
        elif format_type == 3:
            # ISO-3 PIN block format
            padded_pin = f"3{pin_length}{pin.ljust(14, 'A')}"
        else:
            # Default to ISO-0
            padded_pin = f"0{pin_length}{pin.ljust(14, 'F')}"
        
        return bytes.fromhex(padded_pin)
    
    @classmethod
    def validate_pin(cls, pin: str) -> bool:
        """Validate PIN format and constraints"""
        if not pin.isdigit():
            return False
        
        if len(pin) < 4 or len(pin) > 12:
            return False
        
        return True
    
    @classmethod
    def update_current_pin(cls, new_pin: str) -> bool:
        """Update the current card PIN"""
        if cls.validate_pin(new_pin):
            cls.CURRENT_CARD_PIN = new_pin
            return True
        return False


def get_pin_for_analysis() -> str:
    """Get the PIN to use for key derivation analysis"""
    return PINConfiguration.get_current_pin()


def get_pin_for_transaction() -> str:
    """Get the PIN to use for transactions"""
    return PINConfiguration.get_current_pin()


def get_fallback_pins() -> list:
    """Get list of fallback PINs to try"""
    return PINConfiguration.get_all_pins()


if __name__ == "__main__":
    print("🔐 NFCSpoofer V4.05 - PIN Configuration")
    print("=" * 50)
    
    config = PINConfiguration()
    
    print(f"Current card PIN: {config.get_current_pin()}")
    print(f"Master PIN (fallback): {config.get_master_pin()}")
    print(f"All PINs available: {config.get_all_pins()}")
    
    # Test PIN formatting
    current_pin = config.get_current_pin()
    print(f"\nPIN Block Formats for PIN {current_pin}:")
    
    for fmt in range(4):
        block = config.format_pin_block(current_pin, fmt)
        print(f"Format {fmt}: {block.hex().upper()}")
    
    # Validation test
    test_pins = ["6998", "1337", "123", "12345678901234"]
    print(f"\nPIN Validation Tests:")
    for test_pin in test_pins:
        valid = config.validate_pin(test_pin)
        status = "✅ Valid" if valid else "❌ Invalid"
        print(f"PIN {test_pin}: {status}")
