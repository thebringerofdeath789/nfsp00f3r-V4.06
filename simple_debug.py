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
            
            data, sw1, sw2 = self.connection.transmit(list(apdu))
            return bytes(data + [sw1, sw2])
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
        
        # Test record reading
        print('\n=== Testing Record Reading ===')
        records = emv_card.read_sfi_records()
        print(f'Records found: {len(records)}')
        
        # Show first few bytes of records
        for i, rec in enumerate(records[:5]):
            print(f'  Record {i+1}: {rec[:32].hex()}...' if len(rec) > 32 else f'  Record {i+1}: {rec.hex()}')
        
        # Test TLV parsing
        print('\n=== Testing TLV Parsing ===')
        tlv_parser = TLVParser()
        total_nodes = 0
        
        for i, rec in enumerate(records[:5]):
            try:
                nodes = tlv_parser.parse(rec)
                node_count = len(nodes)
                total_nodes += node_count
                if node_count > 0:
                    print(f'  Record {i+1}: {node_count} nodes')
                    for node in nodes[:2]:  # Show first 2 nodes
                        print(f'    Tag {node.tag}: {node.value[:16].hex()}...' if len(node.value) > 16 else f'    Tag {node.tag}: {node.value.hex()}')
            except Exception as e:
                print(f'  Record {i+1}: TLV error: {e}')
        
        print(f'Total TLV nodes: {total_nodes}')
        
        # Test enhanced parser
        print('\n=== Testing Enhanced Parser ===')
        enhanced_parser = EnhancedEMVParser()
        
        for i, rec in enumerate(records[:3]):
            try:
                result = enhanced_parser.parse_and_extract_payment_data(rec)
                if result and any(result.values()):
                    print(f'  Record {i+1} enhanced data:')
                    for key, value in result.items():
                        if value:
                            print(f'    {key}: {value}')
            except Exception as e:
                print(f'  Record {i+1}: Enhanced error: {e}')
        
        cardservice.connection.disconnect()
        print('\nCard disconnected')
        
    except Exception as e:
        print(f'Error: {e}')
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
