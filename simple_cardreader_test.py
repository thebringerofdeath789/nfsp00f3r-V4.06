#!/usr/bin/env python3

# Simple version of cardreader_pcsc without PyQt5 dependencies
from smartcard.System import readers
from smartcard.Exceptions import NoCardException
from emvcard import EMVCard


class SimplePCSCCardReader:
    """Simplified PC/SC card reader without PyQt5 dependencies"""
    
    def __init__(self, logger=None):
        self.logger = logger
        self._readers = []

    def list_readers(self):
        """Return list of available reader names"""
        try:
            return [str(r) for r in readers()]
        except:
            return []

    def read_card(self):
        """
        Attempts to connect to the first available reader and return an EMVCard.
        Returns EMVCard instance or None on failure.
        """
        reader_list = readers()
        if not reader_list:
            if self.logger:
                self.logger.log("[PCSC] No readers available")
            return None
            
        try:
            r = reader_list[0]
            conn = r.createConnection()
            conn.connect()
            emv_card = EMVCard(conn)
            if self.logger:
                self.logger.log(f"[PCSC] Read card on {r}")
            return emv_card
        except Exception as e:
            if self.logger:
                self.logger.log(f"[PCSC] Error reading card: {e}", "ERROR")
            return None


def main():
    """Test the simple reader"""
    reader = SimplePCSCCardReader()
    print("Enumerated readers:", reader.list_readers())
    
    emv = reader.read_card()
    if not emv:
        print("No card read. Make sure the card is on the reader and try again.")
        return

    print(f"Card connected, APDU log entries: {len(emv.apdu_log)}")
    print(f"AIDs found: {emv.info.get('AIDs', [])}")
    print(f"TLV nodes in tlv_root: {len(emv.tlv_root)}")

    # Show APDU log details
    print(f"\n=== APDU Log ({len(emv.apdu_log)} entries) ===")
    for i, entry in enumerate(emv.apdu_log):
        req = entry.get('request', '')
        resp = entry.get('response', '')
        print(f"  {i+1}: {req} -> {resp}")
        
        # If this is a successful response with data, let's see what's in it
        if resp and len(resp) > 4 and resp.endswith('9000'):
            data_part = resp[:-4]  # Remove 9000 status
            if data_part:
                print(f"      Data: {data_part} ({len(data_part)//2} bytes)")

    # Check cardholder info
    info = emv.get_cardholder_info()
    print(f"\n=== Cardholder Info ===")
    print(f"PAN: {info.get('PAN')}")
    print(f"Name: {info.get('Name')}")
    print(f"Expiry: {info.get('Expiry')}")
    print(f"ServiceCode: {info.get('ServiceCode')}")
    
    # Check enhanced data
    enhanced_data = info.get("enhanced_parsed_data", {})
    if enhanced_data:
        print(f"\n=== Enhanced Parser Data ===")
        for key, value in enhanced_data.items():
            if value:
                print(f"{key}: {value}")


if __name__ == "__main__":
    main()
