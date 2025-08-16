# NFSP00F3R V4.06 - Advanced EMV/NFC Card Management Suite

## Overview

NFSP00F3R V4.06 is a comprehensive, multi-platform EMV/NFC card management and analysis suite designed for security researchers, penetration testers, and advanced card enthusiasts. It provides deep capabilities for reading, parsing, analyzing, and manipulating payment card data from both physical and virtual sources, including advanced PIN extraction, cryptographic key derivation, and attack vector assessment.

## Key Features

- **Deep EMV/NFC Card Parsing:** Advanced TLV traversal and extraction logic, supporting non-standard and nested EMV record structures.
- **PIN Extraction Engine:** Automated extraction of PINs with confidence scoring, leveraging multiple heuristics and cryptographic analysis.
- **Cryptographic Key Derivation:** Real-time derivation and validation of card keys, including support for custom key generation and service code modification.
- **Multi-Card Management:** Unified interface for managing multiple cards, switching, inserting, removing, and preventing duplicates.
- **Attack Vector Assessment:** Built-in tools for analyzing card security, service code implications, and magstripe vulnerabilities.
- **Bluetooth & PC/SC Reader Integration:** Supports a wide range of card readers, including Bluetooth, PC/SC, and custom relay protocols.
- **JSON Import/Export:** Seamless import/export of card profiles and analysis results for interoperability and backup.
- **Companion Android App:** Real-time relay and management of card data between desktop and mobile devices.
- **Modern UI:** PyQt5-based interface with advanced visualization, quick info panels, and transaction analysis.

## What Sets NFSP00F3R Apart

- **Comprehensive Card Data Extraction:** Goes beyond standard EMV tools by extracting and reconstructing all critical payment data, including discretionary fields and synthetic tracks.
- **Service Code Modification & CVV Generation:** Unique ability to modify service codes and generate valid CVVs/discretionary data for advanced testing and emulation.
- **Integrated Attack Analysis:** Built-in modules for assessing card attack readiness, magspoof capabilities, and cryptographic weaknesses.
- **Extensible Architecture:** Modular design allows for easy integration of new card types, readers, and analysis engines.
- **Open Source Collaboration:** Integrates and builds upon the best ideas from the EMV/NFC research community, with full credit to upstream projects.

## Authors

- **Gregory King**
- **Matthew Braunschweig**

## Usage

- **Main UI:** Run `python main.py` or `python advanced_card_manager_ui.py` for the full-featured desktop interface.
- **Raspberry Pi Server:** Use `python3 pi_console.py` for a simple menu or `python3 pi_server.py` for a one-shot read. Data is stored in `data/cards/*.json`.
- **Companion Protocol:** Length-prefixed frame stream and JSON control messages over TCP port 9000, compatible with Cardhopper server.

## Credits and Attributions

This build integrates or adapts code and ideas from the following projects:

...existing code...

## Credits and Attributions

This build integrates or adapts code and ideas from the following projects:

- Cardhopper — Tiernan Messmer (Neo-Vortex) — https://github.com/nvx/cardhopper — GPL v3+
- proxmark3 — RfidResearchGroup — https://github.com/RfidResearchGroup/proxmark3 — GPL v3
- danmichaelo/emv — https://github.com/danmichaelo/emv — MIT
- dimalinux/EMV-Tools — https://github.com/dimalinux/EMV-Tools — GPL v3
- atzedevs/emv-crypto — https://github.com/atzedevs/emv-crypto — MIT
- Yagoor/EMV — https://github.com/Yagoor/EMV — GPL v3
- LucaBongiorni/EMV-NFC-Paycard-Reader — https://github.com/LucaBongiorni/EMV-NFC-Paycard-Reader — GPL v3
- dlenski/python-pyscard — https://github.com/dlenski/python-pyscard — GPL v2
- AdamLaurie/RFIDIOt — https://github.com/AdamLaurie/RFIDIOt — GPL v2
- peterfillmore/RFIDIOt/preplayattack — https://github.com/peterfillmore/RFIDIOt/tree/master/preplayattack — GPL v2
- destroythedrones/* — https://github.com/destroythedrones — various
- openemv — https://github.com/openemv — GPL v3
- MichaelsPlayground/TalkToYourCreditCardPart7 — https://github.com/MichaelsPlayground/TalkToYourCreditCardPart7 — GPL v3


### Raspberry Pi server
Use `python3 pi_console.py` for a simple menu or `python3 pi_server.py` for a one shot read. Data is stored in `data/cards/*.json`.

### Companion protocol
Length prefixed frame stream and JSON control messages over TCP port 9000, compatible with Cardhopper server.
