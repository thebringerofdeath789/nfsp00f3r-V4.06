# =====================================================================
# File: emvcard.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   EMVCard encapsulates all logic for TLV/APDU parsing, cryptogram
#   generation, cardholder info extraction, track decode, profile
#   export/import, transaction history, and PIN/offline verification.
#
# Classes:
#   - EMVCard
#   - TLVTree (utility)
# =====================================================================

import binascii
import json
from datetime import datetime

from tlv import TLVParser
from enhanced_parser import EnhancedEMVParser
from tag_dict import get_tag_info
from magstripe import MagstripeEmulator
from pdol_builder import parse_dol as parse_pdol_list, build_env, build_gpo_apdu

class EMVCard:
    """
    Handles all EMV card data and operations: APDU session, TLV parse,
    cardholder info extraction, track decode, cryptogram generation,
    and profile serialization/deserialization.
    """
    def __init__(self, connection=None, logger=None, terminal_profile=None):
        self.conn = connection  # Smartcard or nfcpy connection
        self.logger = logger
        self.terminal_profile = terminal_profile
        self.tlv_parser = TLVParser()
        # Use enhanced parser without external logger to avoid attribute mismatches
        self.enhanced_parser = EnhancedEMVParser(logger=self.logger)
        self.magstripe = MagstripeEmulator()
        self.crypto = None
        self.pin_manager = None
        self.apdu_logger = None
        self.apdu_log = []
        self.info = {}
        self.tlv_root = []
        self.track_data = {}
        self.transactions = []
        self.keys = {}
        self._processing_log = []
        if self.conn:
            self._init_card()

    def _init_card(self):
        """
        Initialize card state by selecting the application and reading all records.
        """
        self.parse_card()

    def parse_card(self):
        """
        Selects PPSE, discovers AIDs, selects main application, reads and parses all records.
        """
        try:
            self.apdu_log = []
            aids = self.get_applications_from_ppse()
            # Fallback: try common payment AIDs directly if PPSE yields none
            if not aids:
                common_aids = [
                    "A0000000031010",  # Visa Credit/Debit
                    "A0000000041010",  # MasterCard
                    "A00000002501",    # Amex
                    "A0000001523010",  # Discover
                    "A0000000651010",  # JCB
                    "A0000000043060",  # Maestro
                    "A0000000032010",  # Visa Electron
                ]
                for aid_hex in common_aids:
                    try:
                        resp = self.select_application(aid_hex)
                        if resp:
                            aids.append(aid_hex)
                            break
                    except Exception:
                        continue
            if not aids:
                raise Exception("No AIDs found on card.")
            # Prefer A0-prefixed EMV AIDs over PPSE names, and store list
            pref = [a for a in aids if a.upper().startswith("A0")]
            chosen = pref[0] if pref else aids[0]
            self.info['AIDs'] = aids
            self.select_application(chosen)
            # Try to get AFL via GPO and read only the listed records
            records = []
            try:
                gpo_resp = self.get_processing_options()
                if gpo_resp and len(gpo_resp) > 2 and gpo_resp[-2:] == b"\x90\x00":
                    afl = self._extract_afl_from_gpo(gpo_resp[:-2])
                    if afl:
                        records = self.read_records_by_afl(afl)
                        if self.logger:
                            self.logger.log(f"[EMVCard] Read {len(records)} records via AFL")
            except Exception as e:
                if self.logger:
                    self.logger.log(f"[EMVCard] GPO/AFL path failed: {e}", "WARN")
            # Fallback: brute-force SFI/record scan if AFL path yielded nothing
            if not records:
                records = self.read_sfi_records()
                if self.logger:
                    self.logger.log(f"[EMVCard] AFL not available; brute-force read returned {len(records)} records", "WARN")
            self.tlv_root = []
            for rec in records:
                nodes = self.tlv_parser.parse(rec)
                self.tlv_root.extend(nodes)
                # Enhanced extraction per record (non-invasive merge)
                try:
                    enhanced = self.enhanced_parser.parse_and_extract_payment_data(rec)
                    if enhanced:
                        # Merge into self.info if values are present
                        if enhanced.get('pan') and not self.info.get('PAN'):
                            self.info['PAN'] = enhanced['pan']
                        if enhanced.get('cardholder_name') and not self.info.get('Name'):
                            self.info['Name'] = enhanced['cardholder_name']
                        if enhanced.get('expiry_date') and not self.info.get('Expiry'):
                            self.info['Expiry'] = enhanced['expiry_date']
                        if enhanced.get('service_code') and not self.info.get('ServiceCode'):
                            self.info['ServiceCode'] = enhanced['service_code']
                        if enhanced.get('cvv') and not self.info.get('CVV'):
                            self.info['CVV'] = enhanced['cvv']
                        # Keep track2 fields available under info but do not change track_data type
                        if enhanced.get('track2_equivalent_data') and not self.info.get('Track2_Parsed'):
                            self.info['Track2_Parsed'] = enhanced['track2_equivalent_data']
                        
                        # Store the complete enhanced parsing results for access by the UI
                        self.info['enhanced_parsed_data'] = enhanced
                        
                        # Fallback: If enhanced parser didn't extract data but we have it from legacy parsing,
                        # populate enhanced data with legacy values and generate tracks
                        if self.logger:
                            self.logger.log(f"[EMVCard] Fallback data - PAN: {self.info.get('PAN')}, Name: {self.info.get('Name')}, Expiry: {self.info.get('Expiry')}, ServiceCode: {self.info.get('ServiceCode')}", "INFO")
                        
                        if not enhanced.get('pan') and self.info.get('PAN'):
                            enhanced['pan'] = self.info['PAN']
                        if not enhanced.get('cardholder_name') and self.info.get('Name'):
                            enhanced['cardholder_name'] = self.info['Name']
                        if not enhanced.get('expiry_date') and self.info.get('Expiry'):
                            enhanced['expiry_date'] = self.info['Expiry']
                        if (not enhanced.get('service_code') or enhanced.get('service_code') is None) and self.info.get('ServiceCode'):
                            enhanced['service_code'] = self.info['ServiceCode']
                        
                        # Generate tracks with the available data (using both enhanced and legacy data)
                        pan_val = enhanced.get('pan') or self.info.get('PAN')
                        name_val = enhanced.get('cardholder_name') or self.info.get('Name') 
                        expiry_val = enhanced.get('expiry_date') or self.info.get('Expiry')
                        service_val = enhanced.get('service_code') or self.info.get('ServiceCode') or (self.info.get('Track2_Parsed', {}).get('service_code'))
                        
                        if pan_val and name_val and expiry_val and service_val:
                            # Generate Track 1
                            enhanced['track1_generated'] = self._generate_track1_fallback(
                                pan_val, name_val, expiry_val, service_val
                            )
                            
                            # Generate Track 2 from Track2_Parsed if available, else generate
                            if self.info.get('Track2_Parsed', {}).get('full_track'):
                                enhanced['track2_formatted'] = self.info['Track2_Parsed']['full_track']
                            else:
                                enhanced['track2_formatted'] = self._generate_track2_fallback(
                                    pan_val, expiry_val, service_val
                                )
                            
                        # Update the stored enhanced data
                        self.info['enhanced_parsed_data'] = enhanced
                except Exception:
                    pass
            # TLV parsing already done in the loop above, just extract info from parsed nodes
            self._extract_info_from_tlv(self.tlv_root)
            self._extract_tracks(self.tlv_root)
            self._extract_transactions(self.tlv_root)
            if self.logger:
                self.logger.log(f"[EMVCard] Card parsed. PAN: {self.info.get('PAN', 'unknown')}")
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] parse_card error: {e}", "ERROR")

    def _generate_track1_fallback(self, pan: str, name: str, expiry: str, service_code: str) -> str:
        """
        Generate Track 1 from parsed EMV data - fallback method for EMVCard.
        """
        try:
            # Format name (remove slashes, limit to 26 chars, pad with spaces)
            formatted_name = name.replace('/', ' ').strip()[:26].ljust(26)
            
            # Handle expiry format (convert MMYY to YYMM if needed)
            if len(expiry) == 4:
                if int(expiry[:2]) > 12:  # Likely YYMM format already
                    yymm = expiry
                else:  # Likely MMYY format
                    yymm = expiry[2:] + expiry[:2]
            else:
                yymm = expiry[-4:]  # Take last 4 digits
            
            # Generate Track 1
            track1 = f"%B{pan}^{formatted_name}^{yymm}{service_code}000000000?"
            return track1
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] Could not generate Track 1: {e}", "WARN")
            return f"%B{pan}^{name}^{expiry}{service_code}000000000?"

    def _generate_track2_fallback(self, pan: str, expiry: str, service_code: str) -> str:
        """
        Generate Track 2 from parsed EMV data - fallback method for EMVCard.
        """
        try:
            # Handle expiry format (convert MMYY to YYMM if needed)
            if len(expiry) == 4:
                if int(expiry[:2]) > 12:  # Likely YYMM format already
                    yymm = expiry
                else:  # Likely MMYY format
                    yymm = expiry[2:] + expiry[:2]
            else:
                yymm = expiry[-4:]  # Take last 4 digits
            
            # Generate Track 2: PAN=YYMM+ServiceCode+DiscretionaryData
            discretionary = "000000000"  # Placeholder discretionary data
            track2 = f"{pan}={yymm}{service_code}{discretionary}"
            return track2
            
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] Could not generate Track 2: {e}", "WARN")
            return f"{pan}={expiry}{service_code}000000000"

    def get_applications_from_ppse(self):
        """
        Selects PPSE and returns a list of available AIDs found.
        """
        apdu = bytes.fromhex("00A404000E325041592E5359532E4444463031")
        resp = self.send_apdu(apdu)
        aids = []
        if resp and len(resp) > 2:
            nodes = self.tlv_parser.parse(resp[:-2])
            def recurse(nodes):
                for node in nodes:
                    # Collect only explicit AIDs (tag 4F) from the PPSE directory
                    if node.tag == "4F":
                        aids.append(node.value.hex().upper())
                    if node.children:
                        recurse(node.children)
            recurse(nodes)
        return aids

    def select_application(self, aid_hex):
        """
        Selects the EMV application by AID (hex string).
        """
        aid_bytes = bytes.fromhex(aid_hex)
        apdu = b'\x00\xA4\x04\x00' + bytes([len(aid_bytes)]) + aid_bytes
        resp = self.send_apdu(apdu)
        if not resp or len(resp) < 2 or resp[-2:] != b'\x90\x00':
            raise Exception("Failed to select application")
        # Track the selected application AID for subsequent operations
        self.info['SelectedAID'] = aid_hex.upper()
        return resp

    def send_apdu(self, apdu: bytes):
        """
        Sends an APDU to the card and returns the response.
        Supports both PCSC and nfcpy connections. Logs each request and response.
        """
        try:
            if not self.conn:
                raise Exception("No card connection available.")
            if hasattr(self.conn, 'transmit'):
                # PCSC style
                if isinstance(apdu, bytes):
                    apdu_list = list(apdu)
                else:
                    apdu_list = [b if isinstance(b, int) else int(b, 16) for b in apdu]
                resp, sw1, sw2 = self.conn.transmit(apdu_list)
                full_resp = bytes(resp + [sw1, sw2])
            elif hasattr(self.conn, 'exchange'):
                # nfcpy style
                full_resp = self.conn.exchange(apdu)
            else:
                raise Exception("Unknown connection interface for APDU.")
            self.add_apdu_entry(apdu, full_resp)
            return full_resp
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] send_apdu error: {e}", "ERROR")
            return b""

    def _extract_afl_from_gpo(self, gpo_data: bytes) -> bytes:
        """
        Extract AFL (tag 94) from a GPO response. Supports both '77' template TLV and '80' response format.
        Returns raw AFL bytes or b'' if not found.
        """
        try:
            if not gpo_data:
                return b''
            # Case 1: Template 0x77 with nested TLVs
            if gpo_data and gpo_data[0] == 0x77:
                nodes = self.tlv_parser.parse(gpo_data)
                def find_94(ns):
                    for n in ns:
                        if n.tag == "94":
                            return n.value
                        if n.children:
                            v = find_94(n.children)
                            if v:
                                return v
                    return None
                v = find_94(nodes)
                return v or b''
            # Case 2: Response Message Template Format 1 (0x80): AIP(2) + AFL(var)
            if gpo_data and gpo_data[0] == 0x80:
                # length byte may be at [1] per BER-TLV definite short-form, but some readers return only the value
                # Handle both: if second byte looks like a length that matches remainder, skip it
                if len(gpo_data) >= 2 and gpo_data[1] == (len(gpo_data) - 2):
                    value = gpo_data[2:]
                else:
                    # assume gpo_data is the value already
                    value = gpo_data[1:]
                if len(value) >= 2:
                    # skip AIP (2 bytes)
                    return value[2:]
            # Fallback: try TLV parse directly for 94
            nodes = self.tlv_parser.parse(gpo_data)
            for n in nodes:
                if n.tag == "94":
                    return n.value
            return b''
        except Exception:
            return b''
    def _parse_transaction_log(self, value):
        """
        Parses a standard EMV transaction log entry (log format varies by card/issuer).
        Typical format: [YYMMDD][Amount, Authorised (6)][Currency Code (2)][Type (1)][Country Code (2)][Status (1)][Reference (2)]
        Returns a dict with all decoded fields plus any raw leftover bytes.
        """
        try:
            fields = {}
            idx = 0
            # Date (YYMMDD) - 3 bytes
            if len(value) >= idx+3:
                date_bytes = value[idx:idx+3]
                fields['date'] = f"20{date_bytes[0]:02x}-{date_bytes[1]:02x}-{date_bytes[2]:02x}"
                idx += 3
            # Amount, Authorised - 6 bytes
            if len(value) >= idx+6:
                amt_bytes = value[idx:idx+6]
                fields['amount'] = int.from_bytes(amt_bytes, 'big')
                idx += 6
            # Currency code - 2 bytes
            if len(value) >= idx+2:
                cur_bytes = value[idx:idx+2]
                fields['currency'] = f"{cur_bytes[0]:02x}{cur_bytes[1]:02x}"
                idx += 2
            # Transaction Type - 1 byte
            if len(value) > idx:
                fields['type'] = value[idx]
                idx += 1
            # Country code - 2 bytes
            if len(value) >= idx+2:
                ctry_bytes = value[idx:idx+2]
                fields['country'] = f"{ctry_bytes[0]:02x}{ctry_bytes[1]:02x}"
                idx += 2
            # Status - 1 byte
            if len(value) > idx:
                fields['status'] = value[idx]
                idx += 1
            # Reference - 2 bytes
            if len(value) >= idx+2:
                ref_bytes = value[idx:idx+2]
                fields['reference'] = binascii.hexlify(ref_bytes).decode()
                idx += 2
            # Anything left
            if len(value) > idx:
                fields['raw'] = binascii.hexlify(value[idx:]).decode()
            return fields
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] Transaction log decode error: {e}", "WARN")
            return None
    def get_processing_options(self):
        """
        Issues a real GET PROCESSING OPTIONS APDU with dynamic PDOL parsing and construction.
        Reads the PDOL from the FCI Template, builds the correct PDOL data field, and sends a valid command.
        """
        # Use the selected AID if available
        # Prefer the explicitly selected AID, fall back to first A0-prefixed AID
        aid = self.info.get('SelectedAID')
        if not aid:
            a_list = self.info.get('AIDs', [])
            pref = [a for a in a_list if isinstance(a, str) and a.upper().startswith('A0')]
            aid = (pref[0] if pref else (a_list[0] if a_list else None))
        if not aid:
            raise Exception("No AID available for GPO.")

        # SELECT app
        aid_bytes = bytes.fromhex(aid)
        apdu_select = b'\x00\xA4\x04\x00' + bytes([len(aid_bytes)]) + aid_bytes
        resp_select = self.send_apdu(apdu_select)
        if not resp_select or len(resp_select) < 2 or resp_select[-2:] != b'\x90\x00':
            raise Exception("Failed to select app for GPO.")

        # Parse FCI template for PDOL
        pdol_bytes = b''
        pdol_tlv = self.tlv_parser.parse(resp_select[:-2])

        def find_pdol(nodes):
            for node in nodes:
                if node.tag == "9F38":
                    return node.value
                if node.children:
                    res = find_pdol(node.children)
                    if res:
                        return res
            return None

        pdol_bytes = find_pdol(pdol_tlv)

        if pdol_bytes:
            pdol_list = parse_pdol_list(pdol_bytes)
            # build environment from terminal profile if available on self
            term_prof = getattr(self, "terminal_profile", {})
            # If terminal is an EmvTerminal instance, derive a pdol profile dict
            try:
                if hasattr(term_prof, 'pdol_profile'):
                    term_prof = term_prof.pdol_profile()
            except Exception:
                pass
            # use zero amount by default here; higher level flows can override
            env = build_env(term_prof, amount_cents=0, tx_type=0x00)
            apdu = build_gpo_apdu(pdol_list, env)
        else:
            # No PDOL, send GPO with 83 00
            apdu = b'\x80\xA8\x00\x00\x02\x83\x00'
        resp = self.send_apdu(apdu)
        return resp

    def read_sfi_records(self):
        """
        Reads all records for SFI 1-31, record 1-16 (EMV standard).
        Returns a list of valid record responses.
        """
        records = []
        for sfi in range(1, 32):
            for rec_num in range(1, 17):
                p2 = (sfi << 3) | 4
                apdu = bytes([0x00, 0xB2, rec_num, p2, 0x00])
                resp = self.send_apdu(apdu)
                # Handle SW1=0x6C (wrong length) by retrying with SW2 as Le
                if resp and len(resp) >= 2 and resp[-2] == 0x6C:
                    fixed_le = resp[-1]
                    apdu = apdu[:-1] + bytes([fixed_le])
                    resp = self.send_apdu(apdu)
                # Accept success and also warnings with data (62xx/63xx)
                if resp and len(resp) > 2:
                    sw1, sw2 = resp[-2], resp[-1]
                    if (sw1 == 0x90 and sw2 == 0x00) or (sw1 in (0x62, 0x63)):
                        if len(resp) > 2:
                            records.append(resp[:-2])
        return records

    def read_records_by_afl(self, afl: bytes):
        """
        Read application records guided by AFL (Application File Locator) bytes.
        AFL is a sequence of 4-byte entries: [SFI|first|last|offline_count].
        Returns list of record payloads (without SW).
        """
        records = []
        try:
            if not afl:
                return records
            offset = 0
            while offset + 4 <= len(afl):
                sfi = afl[offset] >> 3
                first_record = afl[offset + 1]
                last_record = afl[offset + 2]
                # offline_auth_count = afl[offset + 3]  # not used here
                offset += 4
                for rec in range(first_record, last_record + 1):
                    p2 = (sfi << 3) | 4
                    apdu = bytes([0x00, 0xB2, rec, p2, 0x00])
                    resp = self.send_apdu(apdu)
                    # Handle SW1=0x6C fixup
                    if resp and len(resp) >= 2 and resp[-2] == 0x6C:
                        fixed_le = resp[-1]
                        apdu = apdu[:-1] + bytes([fixed_le])
                        resp = self.send_apdu(apdu)
                    if resp and len(resp) > 2:
                        sw1, sw2 = resp[-2], resp[-1]
                        if (sw1 == 0x90 and sw2 == 0x00) or (sw1 in (0x62, 0x63)):
                            records.append(resp[:-2])
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] read_records_by_afl error: {e}", "WARN")
        return records

    def parse_tlv_records(self, records):
        """
        Given a list of TLV byte records, parses and stores them.
        """
        self.tlv_root = []
        for rec in records:
            nodes = self.tlv_parser.parse(rec)
            self.tlv_root.extend(nodes)

    def _extract_info_from_tlv(self, nodes):
        """
        Recursively extracts cardholder info fields from parsed TLV nodes.
        """
        for node in nodes:
            info = get_tag_info(node.tag)
            if info:
                desc = info["desc"].lower()
                if desc.startswith("application primary account number"):
                    self.info["PAN"] = node.value.hex()
                if desc.startswith("cardholder name"):
                    try:
                        self.info["Name"] = node.value.decode("ascii").strip()
                    except Exception as e:
                        if self.logger:
                            self.logger.log(f"[EMVCard] Failed to decode cardholder name: {e}", "WARN")
                if desc.startswith("application expiration date"):
                    self.info["Expiry"] = node.value.hex()
                if desc.startswith("application pan sequence number"):
                    self.info["SEQ"] = node.value.hex()
            if node.children:
                self._extract_info_from_tlv(node.children)

    def _extract_tracks(self, nodes):
        """
        Recursively extracts and decodes Track 1 and Track 2 data from TLV nodes.
        """
        for node in nodes:
            if node.tag == "56":  # Track 1
                track1 = node.value.decode(errors="ignore")
                self.track_data["Track1"] = track1
                track1_fields = self.magstripe.parse_track1(track1)
                if track1_fields:
                    self.info.update(track1_fields)
            elif node.tag == "57":  # Track 2
                track2 = node.value.hex()
                # store with both legacy and lowercase keys for compatibility
                self.track_data["Track2"] = track2
                self.track_data["track2"] = track2
                try:
                    track2_ascii = bytes.fromhex(track2).decode(errors="ignore")
                    track2_fields = self.magstripe.parse_track2(track2_ascii)
                    if track2_fields:
                        self.info.update(track2_fields)
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"[EMVCard] Error decoding Track 2: {e}", "WARN")
            if node.children:
                self._extract_tracks(node.children)

    def _extract_transactions(self, nodes):
        """
        Recursively extracts transaction logs (if present) from TLV nodes.
        """
        for node in nodes:
            info = get_tag_info(node.tag)
            if info and info["desc"].lower().startswith("transaction log"):
                try:
                    transaction = self._parse_transaction_log(node.value)
                    if transaction:
                        self.transactions.append(transaction)
                except Exception as e:
                    if self.logger:
                        self.logger.log(f"[EMVCard] Failed to parse transaction log: {e}", "WARN")
            if node.children:
                self._extract_transactions(node.children)

    def _parse_transaction_log(self, value):
        """
        Parses a standard EMV transaction log entry (log format varies by card/issuer).
        Typical format: [YYMMDD][Amount, Authorised (6)][Currency Code (2)][Type (1)][Country Code (2)][Status (1)][Reference (2)]
        Returns a dict with all decoded fields plus any raw leftover bytes.
        """
        try:
            fields = {}
            idx = 0
            if len(value) >= idx+3:
                date_bytes = value[idx:idx+3]
                fields['date'] = f"20{date_bytes[0]:02x}-{date_bytes[1]:02x}-{date_bytes[2]:02x}"
                idx += 3
            if len(value) >= idx+6:
                amt_bytes = value[idx:idx+6]
                fields['amount'] = int.from_bytes(amt_bytes, 'big')
                idx += 6
            if len(value) >= idx+2:
                cur_bytes = value[idx:idx+2]
                fields['currency'] = f"{cur_bytes[0]:02x}{cur_bytes[1]:02x}"
                idx += 2
            if len(value) > idx:
                fields['type'] = value[idx]
                idx += 1
            if len(value) >= idx+2:
                ctry_bytes = value[idx:idx+2]
                fields['country'] = f"{ctry_bytes[0]:02x}{ctry_bytes[1]:02x}"
                idx += 2
            if len(value) > idx:
                fields['status'] = value[idx]
                idx += 1
            if len(value) >= idx+2:
                ref_bytes = value[idx:idx+2]
                fields['reference'] = binascii.hexlify(ref_bytes).decode()
                idx += 2
            if len(value) > idx:
                fields['raw'] = binascii.hexlify(value[idx:]).decode()
            return fields
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] Transaction log decode error: {e}", "WARN")
            return None

    def get_cardholder_info(self):
        """
        Returns a dict of parsed cardholder and card info fields.
        """
        return self.info.copy()

    def get_tlv_tree(self):
        """
        Returns the parsed TLV tree for advanced use.
        """
        return self.tlv_root
    def export_profile(self):
        """
        Exports the card profile as a JSON string with all critical fields.
        """
        profile = {
            "info": self.info,
            "track_data": self.track_data,
            "transactions": self.transactions,
            "apdu_log": self.apdu_log,
            "keys": self.keys,
        }
        return json.dumps(profile, indent=2, sort_keys=True)

    def import_profile_json(self, json_str):
        """
        Imports card profile from a JSON string.
        """
        try:
            profile = json.loads(json_str)
            self.info = profile.get("info", {})
            self.track_data = profile.get("track_data", {})
            self.transactions = profile.get("transactions", [])
            self.apdu_log = profile.get("apdu_log", [])
            self.keys = profile.get("keys", {})
            # Allow re-parse if needed for compatibility with older exports
            if not self.tlv_root and "tlv_records" in profile:
                self.parse_tlv_records(profile["tlv_records"])
            return True
        except Exception as e:
            if self.logger:
                self.logger.log(f"[EMVCard] Error importing profile: {e}", "ERROR")
            return False

    def reparse(self):
        """
        Re-parses TLV and updates all extracted fields from the current TLV root.
        """
        self.info = {}
        self.track_data = {}
        self.transactions = []
        if self.tlv_root:
            self._extract_info_from_tlv(self.tlv_root)
            self._extract_tracks(self.tlv_root)
            self._extract_transactions(self.tlv_root)

    def generate_ac(self, ac_type="ARQC", unpredictable_number=None):
        """
        Generates an Application Cryptogram (AC) using current card state and keys.
        ac_type: "ARQC", "AAC", or "TC"
        unpredictable_number: If None, uses default/random
        """
        if not self.crypto:
            raise Exception("No cryptogram engine set (call set_crypto)")
        if not self.info.get("PAN"):
            raise Exception("No PAN loaded")
        if not self.keys:
            raise Exception("No keys loaded for AC generation")
        pdol_tags = self.info.get("PDOL_TAGS", [])
        # Gather input data for AC
        data = {
            "pan": self.info["PAN"],
            "amount": self.info.get("Amount", 1),
            "currency": self.info.get("Currency", "0840"),
            "terminal_country": self.info.get("TerminalCountry", "0840"),
            "unpredictable_number": unpredictable_number or b"\x01\x02\x03\x04",
            "transaction_type": self.info.get("TransactionType", b"\x00"),
        }
        return self.crypto.generate_ac(ac_type, data, self.keys)

    def verify_offline_pin(self, pin):
        """
        Verifies an offline PIN using the pin_manager, if set.
        """
        if not self.pin_manager:
            raise Exception("No PIN manager set")
        return self.pin_manager.verify(pin, self.info)

    def get_processing_log(self):
        """
        Returns the processing log, if maintained.
        """
        return self._processing_log.copy()

    def add_apdu_entry(self, apdu, response):
        """
        Adds an entry to the APDU log, and invokes the logger if present.
        """
        entry = {
            "timestamp": datetime.now().isoformat(),
            "request": binascii.hexlify(apdu).decode() if isinstance(apdu, (bytes, bytearray)) else str(apdu),
            "response": binascii.hexlify(response).decode() if isinstance(response, (bytes, bytearray)) else str(response)
        }
        self.apdu_log.append(entry)
        if self.apdu_logger:
            self.apdu_logger(entry)

    def update_keys(self, new_keys: dict):
        """
        Updates the key dictionary for cryptogram generation and offline verification.
        """
        self.keys.update(new_keys)

    def set_apdu_logger(self, logger_fn):
        """
        Sets a function to receive APDU log entries (for UI or persistent log).
        """
        self.apdu_logger = logger_fn

    def set_crypto(self, crypto_engine):
        """
        Assigns an EMV crypto engine object for AC generation.
        """
        self.crypto = crypto_engine

    def set_magstripe(self, magstripe_engine):
        """
        Assigns a magstripe parsing/emulation engine.
        """
        self.magstripe = magstripe_engine

    def set_pin_manager(self, pin_manager):
        """
        Assigns a PIN manager for offline/online PIN checks.
        """
        self.pin_manager = pin_manager

class TLVTree:
    """
    Simple TLV tree utility for exporting/inspecting nested TLV results.
    """
    def __init__(self, root_nodes):
        self.root_nodes = root_nodes

    def to_dict(self):
        """
        Recursively converts TLV nodes to a dict for JSON export.
        """
        def node_to_dict(node):
            d = {
                "tag": node.tag,
                "value": binascii.hexlify(node.value).decode(),
                "desc": getattr(node, "desc", ""),
                "children": [node_to_dict(child) for child in getattr(node, "children", [])]
            }
            return d
        return [node_to_dict(n) for n in self.root_nodes]
    def get_track(self, number=1):
        """
        Returns Track 1 or Track 2 data as a string, if available.
        """
        if number == 1:
            return self.track_data.get("Track1", "")
        elif number == 2:
            return self.track_data.get("Track2", "")
        return ""

    def has_tlv_tag(self, tag):
        """
        Returns True if the parsed TLV tree contains the given tag.
        """
        def recursive_find(nodes):
            for node in nodes:
                if node.tag == tag:
                    return True
                if node.children:
                    if recursive_find(node.children):
                        return True
            return False
        return recursive_find(self.tlv_root)

    def get_tlv_value(self, tag):
        """
        Returns the value for the first occurrence of a given tag in the TLV tree.
        """
        def recursive_search(nodes):
            for node in nodes:
                if node.tag == tag:
                    return node.value
                if node.children:
                    val = recursive_search(node.children)
                    if val is not None:
                        return val
            return None
        return recursive_search(self.tlv_root)

    def get_application_label(self):
        """
        Returns the human-readable application label (if present).
        """
        val = self.get_tlv_value("50")
        if val:
            try:
                return val.decode('ascii').strip()
            except Exception:
                return val.hex()
        return ""

    def summary(self):
        """
        Returns a brief dict summary for display (cardholder, PAN, expiry, AIDs, label).
        """
        return {
            "PAN": self.info.get("PAN", ""),
            "Name": self.info.get("Name", ""),
            "Expiry": self.info.get("Expiry", ""),
            "Label": self.get_application_label(),
            "AIDs": self.info.get("AIDs", [])
        }

    def is_valid(self):
        """
        Returns True if the card has a valid PAN and at least one track or TLV.
        """
        return bool(self.info.get("PAN")) and (self.track_data or self.tlv_root)

    def __repr__(self):
        return f"<EMVCard PAN={self.info.get('PAN', '')} Name={self.info.get('Name', '')}>"

    def __str__(self):
        s = f"EMVCard:\n"
        for k, v in self.info.items():
            s += f"  {k}: {v}\n"
        for k, v in self.track_data.items():
            s += f"  {k}: {v}\n"
        if self.transactions:
            s += f"  Transactions: {len(self.transactions)}\n"
        return s

    def to_dict(self):
        """
        Exports all data as a dict for further serialization.
        """
        return {
            "info": self.info,
            "track_data": self.track_data,
            "transactions": self.transactions,
            "apdu_log": self.apdu_log,
            "keys": self.keys
        }
    def clone(self):
        """
        Returns a deep copy of this EMVCard instance.
        """
        import copy
        return copy.deepcopy(self)

    def reset(self):
        """
        Resets all parsed data, tracks, transactions, logs, and info.
        """
        self.info = {}
        self.track_data = {}
        self.transactions = []
        self.apdu_log = []
        self.tlv_root = []
        self.keys = {}
        self._processing_log = []

    @staticmethod
    def from_profile(profile_json, logger=None):
        """
        Creates an EMVCard instance from exported profile JSON.
        """
        card = EMVCard(connection=None, logger=logger)
        card.import_profile_json(profile_json)
        return card

# =====================================================================
# END OF FILE: emvcard.py
# =====================================================================
