#!/usr/bin/env python3
# Live EMV read and parse using PC/SC and EMVCard

from cardreader_pcsc import PCSCCardReader


def main():
    reader = PCSCCardReader()
    print("Enumerated readers:", reader.list_readers())
    emv = reader.read_card()
    if not emv:
        print("No card read. Make sure the card is on the reader and try again.")
        return

    aids = emv.info.get("AIDs", [])
    if aids:
        print("AIDs:", aids)

    info = emv.get_cardholder_info()
    print("\n--- Cardholder Info ---")
    print("PAN:", info.get("PAN") or info.get("Track2_Parsed", {}).get("pan"))
    print("Name:", info.get("Name"))
    print("Expiry:", info.get("Expiry") or info.get("Track2_Parsed", {}).get("expiry_date"))
    print("Service Code:", info.get("ServiceCode") or info.get("Track2_Parsed", {}).get("service_code"))
    
    print(f"\n--- Debug: All Info Keys ---")
    for key, value in info.items():
        if key not in ['enhanced_parsed_data', 'Track2_Parsed']:
            print(f"{key}: {value}")
        elif key == 'Track2_Parsed' and value:
            print(f"{key}: {value}")
    print("--- End Debug ---")

    print("\n--- Track Data ---")
    # Check for generated Track 1 and formatted Track 2 from enhanced parser
    enhanced_data = info.get("enhanced_parsed_data", {})
    
    print(f"Debug - Enhanced data keys: {list(enhanced_data.keys()) if enhanced_data else 'None'}")
    if enhanced_data:
        print(f"Debug - PAN: '{enhanced_data.get('pan')}'")
        print(f"Debug - Name: '{enhanced_data.get('cardholder_name')}'") 
        print(f"Debug - Expiry: '{enhanced_data.get('expiry_date')}'")
        print(f"Debug - Service: '{enhanced_data.get('service_code')}'")
        print(f"Debug - Track1 generated: {enhanced_data.get('track1_generated')}")
        print(f"Debug - Track2 formatted: {enhanced_data.get('track2_formatted')}")
    
    track1_generated = enhanced_data.get("track1_generated", "")
    track2_formatted = enhanced_data.get("track2_formatted", "")
    
    print("Track1:", track1_generated or emv.track_data.get("Track1", ""))
    print("Track2 (hex):", track2_formatted or emv.track_data.get("Track2", emv.track_data.get("track2", "")))
    
    # Also show Track 2 equivalent data details if available
    track2_equiv = enhanced_data.get("track2_equivalent_data")
    if track2_equiv:
        print("\n--- Track 2 Details ---")
        print(f"PAN: {track2_equiv.get('pan')}")
        print(f"Expiry: {track2_equiv.get('expiry_date')}")
        print(f"Service Code: {track2_equiv.get('service_code')}")
        print(f"Discretionary Data: {track2_equiv.get('discretionary_data')}")
        print(f"Full Track: {track2_equiv.get('full_track')}")
    
    # Debug: Show parsed TLV tags from enhanced parser
    parsed_tags = enhanced_data.get("parsed_tags", {})
    if parsed_tags:
        print(f"\n--- Parsed TLV Tags ({len(parsed_tags)}) ---")
        for tag, info_data in parsed_tags.items():
            desc = info_data.get('desc', 'Unknown')
            value = info_data.get('value', '')
            print(f"{tag}: {desc}")
            print(f"   Value: {value}")
            if len(value) > 80:
                print(f"   (truncated, full length: {len(value)})")
    else:
        print("\n--- No Enhanced TLV Tags Found ---")

    # Optional: print count of TLV nodes parsed
    tlv_nodes = emv.tlv_root
    print(f"\nParsed TLV nodes: {len(tlv_nodes)}")
    if len(tlv_nodes) == 0:
        # Try to locate GPO in APDU log
        gpo_entries = [e for e in emv.apdu_log if e['request'].startswith('80a80000')]
        if gpo_entries:
            gpo = gpo_entries[-1]
            print("GPO ->", gpo['request'])
            print("GPO <-", gpo['response'])
        print("No TLVs parsed; printing last 10 APDUs for diagnostics:")
        for entry in emv.apdu_log[-10:]:
            print(f"  -> {entry['request']}")
            print(f"  <- {entry['response']}")

if __name__ == "__main__":
    main()
