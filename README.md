

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
