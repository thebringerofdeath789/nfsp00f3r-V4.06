# =====================================================================
# File: tag_dict.py
# Project: nfsp00f3r V4.05 - EMV/NFC Sniffer, Card Manager & Companion
# Authors: Gregory King & Matthew Braunschweig
# Date: 2025-08-04
#
# Description:
#   Comprehensive mapping of EMV/NFC TLV tags to human-readable
#   descriptions, data types, and reference notes. Used for UI
#   decoding and in the TLV tree display.
#
# Variables:
#   - TAG_DICT (dict)
#   - get_tag_info(tag)
# =====================================================================

TAG_DICT = {
    "5A":  {"desc": "Application Primary Account Number (PAN)", "type": "n"},
    "5F20": {"desc": "Cardholder Name", "type": "an"},
    "5F24": {"desc": "Application Expiration Date", "type": "n"},
    "5F25": {"desc": "Application Effective Date", "type": "n"},
    "5F28": {"desc": "Issuer Country Code", "type": "n"},
    "5F2A": {"desc": "Transaction Currency Code", "type": "n"},
    "5F30": {"desc": "Service Code", "type": "n"},
    "5F34": {"desc": "Application PAN Sequence Number", "type": "n"},
    "5F50": {"desc": "Issuer URL", "type": "an"},
    "5F54": {"desc": "ICC PIN Encipherment Public Key Certificate", "type": "b"},
    "56":   {"desc": "Track 1 Data", "type": "track"},
    "57":   {"desc": "Track 2 Equivalent Data", "type": "track"},
    "61":   {"desc": "Application Template", "type": "tlv"},
    "6F":   {"desc": "FCI Template", "type": "tlv"},
    "70":   {"desc": "Record Template", "type": "tlv"},
    "77":   {"desc": "Response Message Template Format 2", "type": "tlv"},
    "80":   {"desc": "Response Message Template Format 1", "type": "b"},
    "82":   {"desc": "Application Interchange Profile", "type": "b"},
    "84":   {"desc": "Dedicated File (DF) Name / AID", "type": "b"},
    "87":   {"desc": "Application Priority Indicator", "type": "n"},
    "88":   {"desc": "Short File Identifier (SFI)", "type": "n"},
    "8C":   {"desc": "Card Risk Management Data Object List 1 (CDOL1)", "type": "b"},
    "8D":   {"desc": "Card Risk Management Data Object List 2 (CDOL2)", "type": "b"},
    "8E":   {"desc": "Cardholder Verification Method (CVM) List", "type": "b"},
    "8F":   {"desc": "Certification Authority Public Key Index", "type": "n"},
    "90":   {"desc": "Issuer Public Key Certificate", "type": "b"},
    "92":   {"desc": "Issuer Public Key Remainder", "type": "b"},
    "94":   {"desc": "Application File Locator (AFL)", "type": "b"},
    "95":   {"desc": "Terminal Verification Results (TVR)", "type": "b"},
    "97":   {"desc": "Transaction Certificate Data Object List (TDOL)", "type": "b"},
    "9A":   {"desc": "Transaction Date", "type": "n"},
    "9B":   {"desc": "Transaction Status Information", "type": "b"},
    "9C":   {"desc": "Transaction Type", "type": "n"},
    "9F02": {"desc": "Amount, Authorised (Numeric)", "type": "n"},
    "9F03": {"desc": "Amount, Other (Numeric)", "type": "n"},
    "9F06": {"desc": "Application Identifier (AID) - terminal", "type": "b"},
    "9F07": {"desc": "Application Usage Control", "type": "b"},
    "9F10": {"desc": "Issuer Application Data", "type": "b"},
    "9F12": {"desc": "Application Preferred Name", "type": "an"},
    "9F1A": {"desc": "Terminal Country Code", "type": "n"},
    "9F26": {"desc": "Application Cryptogram", "type": "b"},
    "9F27": {"desc": "Cryptogram Information Data", "type": "b"},
    "9F33": {"desc": "Terminal Capabilities", "type": "b"},
    "9F34": {"desc": "Cardholder Verification Method (CVM) Results", "type": "b"},
    "9F36": {"desc": "Application Transaction Counter (ATC)", "type": "n"},
    "9F37": {"desc": "Unpredictable Number", "type": "n"},
    "9F38": {"desc": "Processing Options Data Object List (PDOL)", "type": "b"},
    "9F41": {"desc": "Transaction Sequence Counter", "type": "n"},
    "9F53": {"desc": "Transaction Category Code", "type": "n"},
    "BF0C": {"desc": "FCI Issuer Discretionary Data", "type": "tlv"},
    # ...more as needed
}

def get_tag_info(tag):
    """
    Look up tag in TAG_DICT, returns info dict or None.
    """
    tag_hex = tag.upper()
    return TAG_DICT.get(tag_hex, None)
