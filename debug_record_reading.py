#!/usr/bin/env python3

import os, sys
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from cardreader_pcsc import CardReaderPCSC
from emvcard import EMVCard
from enhanced_parser import EnhancedEMVParser
from tlv import TLVParser
from logger import Logger

def debug_record_reading():
    """Debug what records are being read and how TLV parsing is working"""
    
    # Initialize components
    reader = CardReaderPCSC()
    logger = Logger()
    
    try:
        # Connect to reader
        if not reader.connect():
            print("Failed to connect to card reader")
            return
            
        print("Card reader connected successfully")
        
        # Create EMV card instance
        emv_card = EMVCard(reader, logger=logger)
        
        # Read PSE and AID selection (basic init)
        try:
            emv_card.read_pse()
            print(f"AIDs found: {emv_card.info.get('AIDs', [])}")
        except Exception as e:
            print(f"PSE read failed: {e}")
        
        # Try GPO approach first
        print("\n=== GPO Approach ===")
        try:
            gpo_resp = emv_card.get_processing_options()
            if gpo_resp:
                print(f"GPO Response: {gpo_resp.hex()}")
                if len(gpo_resp) >= 2:
                    sw1, sw2 = gpo_resp[-2:]
                    print(f"GPO SW: {sw1:02x}{sw2:02x}")
                    if sw1 == 0x90 and sw2 == 0x00:
                        print("GPO successful!")
                        # Try to extract AFL
                        afl = emv_card._extract_afl_from_gpo(gpo_resp[:-2])
                        if afl:
                            print(f"AFL extracted: {afl.hex()}")
                            # Read records by AFL
                            afl_records = emv_card.read_records_by_afl(afl)
                            print(f"AFL records count: {len(afl_records)}")
                            for i, rec in enumerate(afl_records):
                                print(f"  Record {i+1}: {rec[:32].hex()}..." if len(rec) > 32 else f"  Record {i+1}: {rec.hex()}")
                        else:
                            print("No AFL found in GPO response")
                    else:
                        print(f"GPO failed with status: {sw1:02x}{sw2:02x}")
            else:
                print("No GPO response received")
        except Exception as e:
            print(f"GPO failed: {e}")
        
        # Try brute force SFI approach
        print("\n=== Brute Force SFI Approach ===")
        sfi_records = emv_card.read_sfi_records()
        print(f"SFI records count: {len(sfi_records)}")
        
        # Show first few bytes of each record
        for i, rec in enumerate(sfi_records[:5]):  # Show first 5 records max
            print(f"  SFI Record {i+1}: {rec[:32].hex()}..." if len(rec) > 32 else f"  SFI Record {i+1}: {rec.hex()}")
        
        # Test TLV parsing on the records
        print("\n=== TLV Parsing Test ===")
        tlv_parser = TLVParser()
        total_nodes = 0
        
        for i, rec in enumerate(sfi_records):
            try:
                nodes = tlv_parser.parse(rec)
                node_count = len(nodes)
                total_nodes += node_count
                if node_count > 0:
                    print(f"  Record {i+1}: {node_count} TLV nodes")
                    for node in nodes[:3]:  # Show first 3 nodes
                        print(f"    Tag {node.tag}: {node.value[:16].hex()}..." if len(node.value) > 16 else f"    Tag {node.tag}: {node.value.hex()}")
            except Exception as e:
                print(f"  Record {i+1}: TLV parse error: {e}")
        
        print(f"\nTotal TLV nodes found: {total_nodes}")
        
        # Test enhanced parser on records
        print("\n=== Enhanced Parser Test ===")
        enhanced_parser = EnhancedEMVParser()
        
        for i, rec in enumerate(sfi_records[:3]):  # Test first 3 records
            try:
                result = enhanced_parser.parse_and_extract_payment_data(rec)
                if result and any(result.values()):
                    print(f"  Record {i+1} enhanced parsing:")
                    for key, value in result.items():
                        if value:
                            print(f"    {key}: {value}")
            except Exception as e:
                print(f"  Record {i+1}: Enhanced parser error: {e}")
        
    except Exception as e:
        print(f"Error during card operations: {e}")
        import traceback
        traceback.print_exc()
    finally:
        reader.disconnect()

if __name__ == "__main__":
    debug_record_reading()
