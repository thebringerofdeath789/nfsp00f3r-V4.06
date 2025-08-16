#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from smartcard.System import readers
from emvcard import EMVCard

def test_parse_card_debug():
    """Debug the parse_card method to see why tlv_root is empty"""
    
    reader_list = readers()
    if not reader_list:
        print('No readers available')
        return

    r = reader_list[0]
    conn = r.createConnection()
    conn.connect()
    
    # Create EMV card but don't let it auto-parse
    print('=== Creating EMVCard instance ===')
    emv_card = EMVCard(conn)
    
    # At this point, parse_card() has already been called by the constructor
    print(f'After constructor - tlv_root: {len(emv_card.tlv_root)} nodes')
    print(f'After constructor - AIDs: {emv_card.info.get("AIDs", [])}')
    print(f'After constructor - PAN: {emv_card.info.get("PAN")}')
    
    # Let's manually trace through parse_card logic
    print(f'\n=== Manual parse_card trace ===')
    
    # Reset info and parse again
    emv_card.info = {}
    emv_card.tlv_root = []
    
    try:
        # Try PSE
        print('Attempting PSE read...')
        emv_card.read_pse()
        aids = emv_card.info.get('AIDs', [])
        print(f'PSE AIDs: {aids}')
    except Exception as e:
        print(f'PSE failed: {e}')
        aids = []
    
    # AID fallback if needed
    if not aids:
        print('Trying common AIDs fallback...')
        common_aids = [
            "A0000000031010",  # Visa Credit/Debit
            "A0000000041010",  # MasterCard
        ]
        for aid_hex in common_aids:
            try:
                resp = emv_card.select_application(aid_hex)
                if resp:
                    aids.append(aid_hex)
                    print(f'AID {aid_hex} selected successfully')
                    break
            except Exception as e:
                print(f'AID {aid_hex} failed: {e}')
                continue
    
    if not aids:
        print('No AIDs available')
        conn.disconnect()
        return
        
    emv_card.info['AIDs'] = aids
    chosen = aids[0]
    emv_card.select_application(chosen)
    print(f'Selected AID: {chosen}')
    
    # Try GPO path
    print('\\nTrying GPO path...')
    records = []
    try:
        gpo_resp = emv_card.get_processing_options()
        print(f'GPO response: {gpo_resp.hex() if gpo_resp else "None"}')
        if gpo_resp and len(gpo_resp) > 2 and gpo_resp[-2:] == b"\\x90\\x00":
            afl = emv_card._extract_afl_from_gpo(gpo_resp[:-2])
            if afl:
                print(f'AFL: {afl.hex()}')
                records = emv_card.read_records_by_afl(afl)
                print(f'AFL records: {len(records)}')
            else:
                print('No AFL extracted')
        else:
            print('GPO failed or returned error')
    except Exception as e:
        print(f'GPO exception: {e}')
    
    # Fallback to SFI
    if not records:
        print('\\nFalling back to SFI records...')
        records = emv_card.read_sfi_records()
        print(f'SFI records: {len(records)}')
    
    # Process TLV
    print('\\nProcessing TLV...')
    emv_card.tlv_root = []
    for i, rec in enumerate(records):
        print(f'  Processing record {i+1}: {len(rec)} bytes')
        try:
            nodes = emv_card.tlv_parser.parse(rec)
            print(f'    Parsed: {len(nodes)} nodes')
            emv_card.tlv_root.extend(nodes)
            print(f'    tlv_root now has: {len(emv_card.tlv_root)} total nodes')
        except Exception as e:
            print(f'    TLV parse error: {e}')
    
    print(f'\\nFinal tlv_root: {len(emv_card.tlv_root)} nodes')
    
    conn.disconnect()
    print('Done.')

if __name__ == "__main__":
    test_parse_card_debug()
