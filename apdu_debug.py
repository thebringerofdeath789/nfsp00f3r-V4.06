#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from emvcard import EMVCard
from enhanced_parser import EnhancedEMVParser
from tlv import TLVParser
from smartcard.System import readers
from smartcard.CardType import AnyCardType  
from smartcard.CardRequest import CardRequest

class SimpleConnection:
    """Simple connection wrapper for EMVCard"""
    def __init__(self, connection):
        self.connection = connection
    
    def send_apdu(self, apdu):
        try:
            if isinstance(apdu, str):
                apdu = bytes.fromhex(apdu)
            elif isinstance(apdu, list):
                apdu = bytes(apdu)
            
            print(f"APDU -> {apdu.hex()}")
            data, sw1, sw2 = self.connection.transmit(list(apdu))
            response = bytes(data + [sw1, sw2])
            print(f"APDU <- {response.hex()}")
            return response
        except Exception as e:
            print(f'APDU error: {e}')
            return None

def main():
    try:
        # Get readers and connect
        reader_list = readers()
        if not reader_list:
            print('No readers available')
            return
        
        print(f'Available readers: {reader_list}')
        
        # Connect to card
        cardtype = AnyCardType()
        cardrequest = CardRequest(timeout=10, cardType=cardtype)
        cardservice = cardrequest.waitforcard()
        cardservice.connection.connect()
        print('Card connected')
        
        # Create EMV card instance
        conn = SimpleConnection(cardservice)
        emv_card = EMVCard(conn)
        
        # First let's try to parse the card normally 
        print('\n=== Parsing Card (Normal Flow) ===')
        try:
            emv_card.parse_card()
            print(f'Card parse completed')
            print(f'AIDs: {emv_card.info.get("AIDs", [])}')
            print(f'TLV nodes in tlv_root: {len(emv_card.tlv_root)}')
            
            # Check if enhanced parser found anything
            enhanced_parser = EnhancedEMVParser()
            
            # Process APDU log with enhanced parser
            print('\n=== Processing APDU Log ===')
            apdu_count = len(emv_card.apdu_log)
            print(f'APDU log entries: {apdu_count}')
            
            for i, apdu_entry in enumerate(emv_card.apdu_log):
                req = apdu_entry.get('request', '')
                resp = apdu_entry.get('response', '')
                print(f'  APDU {i+1}: {req} -> {resp}')
                
                # Try enhanced parsing on response
                if resp and len(resp) > 4:  # Skip status-only responses
                    try:
                        resp_bytes = bytes.fromhex(resp)
                        if len(resp_bytes) > 2:  # Remove SW
                            data = resp_bytes[:-2]
                            if data:
                                result = enhanced_parser.parse_and_extract_payment_data(data)
                                if result and any(result.values()):
                                    print(f'    Enhanced data found:')
                                    for key, value in result.items():
                                        if value:
                                            print(f'      {key}: {value}')
                    except Exception as e:
                        pass  # Skip parsing errors
                
        except Exception as e:
            print(f'Card parse error: {e}')
            import traceback
            traceback.print_exc()
        
        # Test manual record reading with debug
        print('\n=== Manual Record Reading Test ===')
        for sfi in range(1, 5):  # Test first few SFIs
            for rec_num in range(1, 3):  # Test first few records
                p2 = (sfi << 3) | 4
                apdu = bytes([0x00, 0xB2, rec_num, p2, 0x00])
                print(f'Testing SFI {sfi} Record {rec_num}:')
                resp = conn.send_apdu(apdu)
                if resp and len(resp) >= 2:
                    sw1, sw2 = resp[-2:]
                    print(f'  Status: {sw1:02x}{sw2:02x}')
                    if sw1 == 0x90 and sw2 == 0x00 and len(resp) > 2:
                        data = resp[:-2]
                        print(f'  Data: {data.hex()}')
                        # Try enhanced parsing
                        try:
                            result = enhanced_parser.parse_and_extract_payment_data(data)
                            if result and any(result.values()):
                                print(f'  Enhanced parsing found data!')
                                for key, value in result.items():
                                    if value:
                                        print(f'    {key}: {value}')
                        except:
                            pass
                        break  # Found a record, move to next SFI
                    elif sw1 == 0x6A and sw2 == 0x83:
                        print('  Record not found')
                    else:
                        print(f'  Other error: {sw1:02x}{sw2:02x}')
                        break  # No point trying more records in this SFI
        
        cardservice.connection.disconnect()
        print('\nCard disconnected')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
