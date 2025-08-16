#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from smartcard.System import readers
from emvcard import EMVCard

def test_direct_read():
    reader_list = readers()
    if not reader_list:
        print('No readers available')
        return

    r = reader_list[0]
    conn = r.createConnection()
    conn.connect()
    emv_card = EMVCard(conn)

    # Try to select an AID first (needed for record reading to work)
    try:
        # Select Visa AID
        aid = 'A0000000031010'
        aid_bytes = bytes.fromhex(aid)
        apdu_select = b'\x00\xA4\x04\x00' + bytes([len(aid_bytes)]) + aid_bytes
        resp_select = emv_card.send_apdu(apdu_select)
        print(f'SELECT AID response: {resp_select.hex()}')
        if resp_select and len(resp_select) >= 2 and resp_select[-2:] == b'\x90\x00':
            print('AID selection successful')
        else:
            print('AID selection failed')
    except Exception as e:
        print(f'AID selection error: {e}')

    # Now test read_sfi_records
    print('\nTesting read_sfi_records...')
    records = emv_card.read_sfi_records()
    print(f'Records found: {len(records)}')

    for i, rec in enumerate(records):
        print(f'  Record {i+1}: {rec.hex()[:64]}...' if len(rec.hex()) > 64 else f'  Record {i+1}: {rec.hex()}')

    conn.disconnect()
    print('Done.')

if __name__ == "__main__":
    test_direct_read()
