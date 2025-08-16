# =====================================================================
# File: tlv.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-15
#
# Description:
#   Recursive EMV/NFC TLV (Tag-Length-Value) parser and tree builder.
#   Supports BER-TLV definite length encoding, multi-byte tags, and
#   constructed TLVs with nested children.
#
# Classes:
#   - TLVNode
#   - TLVParser
# =====================================================================

from typing import List, Tuple, Optional

class TLVNode:
    def __init__(self, tag: str, length: int, value: bytes, children: Optional[List['TLVNode']] = None):
        self.tag = tag.upper()
        self.length = length
        self.value = value or b''
        self.children = children or []

    def is_constructed(self) -> bool:
        # constructed bit on first tag byte
        b0 = int(self.tag[:2], 16)
        return (b0 & 0x20) == 0x20

    def find(self, tag: str) -> Optional['TLVNode']:
        tag = tag.upper()
        if self.tag == tag:
            return self
        for c in self.children:
            found = c.find(tag)
            if found:
                return found
        return None

    def to_dict(self):
        return {
            "tag": self.tag,
            "len": self.length,
            "value": self.value.hex().upper(),
            "children": [c.to_dict() for c in self.children] if self.children else []
        }

    def pretty(self, indent: int = 0) -> str:
        pad = '  ' * indent
        line = f"{pad}{self.tag}  len={self.length}  val={self.value.hex().upper()}"
        if not self.children:
            return line
        lines = [line]
        for c in self.children:
            lines.append(c.pretty(indent + 1))
        return "\n".join(lines)


class TLVParser:
    def parse(self, data) -> List[TLVNode]:
        """Parse TLV data (bytes, list of ints, or hex string) into TLVNode list."""
        if isinstance(data, str):
            data = bytes.fromhex(data.replace(' ', ''))
        elif isinstance(data, list):
            data = bytes(data)
        nodes, _ = self._parse_all(data, 0)
        return nodes

    def parse_and_extract_payment_data(self, raw_record_data: bytes) -> dict:
        """
        Enhanced payment data extraction: parses raw record data, traverses TLV tree, and extracts key payment info.
        Returns a dictionary with PAN, cardholder name, expiry, service code, track2, etc.
        """
        from tag_dict import get_tag_info
        payment_data = {
            'pan': None,
            'cardholder_name': None,
            'expiry_date': None,
            'service_code': None,
            'track2_equivalent_data': None,
            'track1_generated': None,
            'track2_formatted': None,
            'raw_tlv_tree': None,
            'parsed_tags': {}
        }
        try:
            tlv_tree = self.parse(raw_record_data)
            payment_data['raw_tlv_tree'] = [node.to_dict() for node in tlv_tree]
            for node in tlv_tree:
                self._traverse_and_extract(node, payment_data)
        except Exception as e:
            print(f"Enhanced TLV parsing failed: {e}")
        self._generate_tracks(payment_data)
        return payment_data

    def _traverse_and_extract(self, node, payment_data):
        from tag_dict import get_tag_info
        tag_info = get_tag_info(node.tag)
        tag_desc = tag_info.get('desc', 'Unknown Tag')
        payment_data['parsed_tags'][node.tag] = {
            'desc': tag_desc,
            'value': node.value.hex().upper()
        }
        if node.tag == '5A':
            payment_data['pan'] = node.value.hex().rstrip('Ff')
        elif node.tag == '5F20':
            try:
                payment_data['cardholder_name'] = node.value.decode('utf-8').strip()
            except UnicodeDecodeError:
                payment_data['cardholder_name'] = repr(node.value)
        elif node.tag == '5F24':
            payment_data['expiry_date'] = node.value.hex()
        elif node.tag == '5F30':
            payment_data['service_code'] = node.value.hex()
        elif node.tag == '57':
            track2_hex = node.value.hex()
            payment_data['track2_equivalent_data'] = self._parse_track2(track2_hex)
            if not payment_data['pan'] and payment_data['track2_equivalent_data']:
                payment_data['pan'] = payment_data['track2_equivalent_data'].get('pan')
            if not payment_data['expiry_date'] and payment_data['track2_equivalent_data']:
                payment_data['expiry_date'] = payment_data['track2_equivalent_data'].get('expiry_date')
            if not payment_data.get('service_code') and payment_data['track2_equivalent_data']:
                payment_data['service_code'] = payment_data['track2_equivalent_data'].get('service_code')
            if not payment_data.get('cvv') and payment_data['track2_equivalent_data']:
                cvv = payment_data['track2_equivalent_data'].get('cvv')
                if cvv:
                    payment_data['cvv'] = cvv
        if node.is_constructed() and node.children:
            for child in node.children:
                self._traverse_and_extract(child, payment_data)

    def _parse_track2(self, track2_hex: str):
        try:
            hex_up = track2_hex.upper()
            track2_str = hex_up.replace('D', '=').rstrip('F')
            parts = track2_str.split('=')
            if len(parts) < 2:
                return None
            pan = parts[0]
            expiry_date = parts[1][:4]
            service_code = parts[1][4:7] if len(parts[1]) >= 7 else '000'
            discretionary_data = parts[1][7:] if len(parts[1]) > 7 else ''
            cvv = self._extract_cvv_from_discretionary(discretionary_data)
            result = {
                'pan': pan,
                'expiry_date': expiry_date,
                'service_code': service_code,
                'discretionary_data': discretionary_data,
                'full_track': track2_str
            }
            if cvv:
                result['cvv'] = cvv
            return result
        except Exception as e:
            print(f"Could not parse Track 2 data '{track2_hex}': {e}")
            return None

    def _extract_cvv_from_discretionary(self, discretionary: str):
        if not discretionary or len(discretionary) < 3:
            return None
        try:
            clean_data = discretionary.lstrip('0')
            if len(clean_data) >= 3:
                potential_cvv = clean_data[:3]
                if potential_cvv.isdigit() and potential_cvv != '000':
                    return potential_cvv
            import re
            cvv_pattern = re.findall(r'(\d{3})', discretionary)
            for potential in cvv_pattern:
                if potential != '000' and potential != '999':
                    return potential
        except Exception as e:
            print(f"Error extracting CVV from discretionary '{discretionary}': {e}")
        return None

    def _generate_tracks(self, payment_data):
        if (payment_data.get('pan') and payment_data.get('cardholder_name') and payment_data.get('expiry_date') and payment_data.get('service_code')):
            payment_data['track1_generated'] = self._generate_track1(
                payment_data['pan'],
                payment_data['cardholder_name'],
                payment_data['expiry_date'],
                payment_data['service_code']
            )
        if (payment_data.get('pan') and payment_data.get('expiry_date') and payment_data.get('service_code')):
            pan = payment_data['pan']
            expiry = payment_data['expiry_date']
            service_code = payment_data['service_code']
            if len(expiry) == 6:
                yymm = expiry[2:6]
            elif len(expiry) == 4:
                yymm = expiry
            else:
                yymm = expiry[-4:]
            discretionary = "000000000"
            payment_data['track2_formatted'] = f"{pan}={yymm}{service_code}{discretionary}"
        if payment_data.get('track2_equivalent_data'):
            track2_data = payment_data['track2_equivalent_data']
            payment_data['track2_formatted'] = f"{track2_data['pan']}={track2_data['expiry_date']}{track2_data['service_code']}{track2_data['discretionary_data']}"

    def _generate_track1(self, pan, name, expiry, service_code):
        try:
            formatted_name = name.replace('/', ' ').strip()[:26].ljust(26)
            if len(expiry) == 4:
                if expiry[:2] > '12':
                    yymm = expiry
                else:
                    yymm = expiry[2:] + expiry[:2]
            else:
                yymm = expiry[-4:]
            track1 = f"%B{pan}^{formatted_name}^{yymm}{service_code}000000000?"
            return track1
        except Exception as e:
            print(f"Could not generate Track 1: {e}")
            return f"%B{pan}^{name}^{expiry}{service_code}000000000?"

    def _parse_all(self, data: bytes, idx: int) -> Tuple[List[TLVNode], int]:
        nodes = []
        while idx < len(data):
            node, idx2 = self._parse_one(data, idx)
            if node is None or idx2 == idx:
                break
            nodes.append(node)
            idx = idx2
        return nodes, idx

    def _parse_tag(self, data: bytes, idx: int) -> Tuple[str, int]:
        if idx >= len(data):
            return "", idx
        first = data[idx]
        idx += 1
        tag_bytes = [first]
        # multi-byte tag if 0x1F
        if (first & 0x1F) == 0x1F:
            while idx < len(data):
                tag_bytes.append(data[idx])
                cont = (data[idx] & 0x80) == 0x80
                idx += 1
                if not cont:
                    break
        return ''.join(f"{b:02X}" for b in tag_bytes), idx

    def _parse_length(self, data: bytes, idx: int) -> Tuple[int, int]:
        if idx >= len(data):
            return 0, idx
        first = data[idx]
        idx += 1
        if first < 0x80:
            return first, idx
        count = first & 0x7F
        if idx + count > len(data):
            return 0, idx
        length = 0
        for _ in range(count):
            length = (length << 8) | data[idx]
            idx += 1
        return length, idx

    def _parse_one(self, data: bytes, idx: int) -> Tuple[Optional[TLVNode], int]:
        if idx >= len(data):
            return None, idx
        tag, idx = self._parse_tag(data, idx)
        if not tag:
            return None, idx
        length, idx = self._parse_length(data, idx)
        if idx + length > len(data):
            return None, idx
        value = data[idx:idx+length]
        idx += length
        children: List[TLVNode] = []
        # if constructed, parse children from value
        if int(tag[:2], 16) & 0x20:
            children, _ = self._parse_all(value, 0)
        return TLVNode(tag, length, value, children), idx
