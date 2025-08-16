#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from smartcard.System import readers
from emvcard import EMVCard
from tlv import TLVParser

def test_tlv_processing():
    reader_list = readers()
    if not reader_list:
        print('No readers available')
        return

    r = reader_list[0]
    conn = r.createConnection()
    conn.connect()
    emv_card = EMVCard(conn)

    # Select AID first
    aid = 'A0000000031010'
    aid_bytes = bytes.fromhex(aid)
    apdu_select = b'\x00\xA4\x04\x00' + bytes([len(aid_bytes)]) + aid_bytes
    resp_select = emv_card.send_apdu(apdu_select)
    success_bytes = b"\x90\x00"
    print(f'AID selected: {resp_select[-2:] == success_bytes}')

    # Read records
    records = emv_card.read_sfi_records()
    print(f'Records found: {len(records)}')

    # Test TLV processing manually (same as parse_card does)
    tlv_parser = TLVParser()
    tlv_root = []
    
    print('\nProcessing records into TLV:')
    for i, rec in enumerate(records):
        print(f'  Record {i+1}: {len(rec)} bytes')
        try:
            nodes = tlv_parser.parse(rec)
            print(f'    TLV nodes: {len(nodes)}')
            tlv_root.extend(nodes)
            for j, node in enumerate(nodes[:2]):  # Show first 2 nodes
                print(f'      Node {j+1}: Tag {node.tag}, Value: {node.value.hex()[:32]}...')
        except Exception as e:
            print(f'    TLV parse error: {e}')
    
    print(f'\nFinal tlv_root: {len(tlv_root)} nodes')
    
    # Compare to emv_card.tlv_root
    print(f'EMV card tlv_root: {len(emv_card.tlv_root)} nodes')
    
    # Now run the full parse_card and see what happens
    print(f'\n=== Running parse_card() ===')
    try:
        emv_card_fresh = EMVCard(conn)  # Fresh instance
        print(f'Fresh EMV tlv_root: {len(emv_card_fresh.tlv_root)} nodes')
        # The constructor calls parse_card() automatically
    except Exception as e:
        print(f'parse_card error: {e}')
        import traceback
        traceback.print_exc()

    conn.disconnect()
    print('Done.')

if __name__ == "__main__":
    test_tlv_processing()
