// =====================================================================
// File: ApduUtils.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Helpers for EMV APDU construction and parsing: SELECT, GPO,
//   READ RECORD, VERIFY PIN, GENERATE AC, and response parsing.
// =====================================================================

package com.nfsp00f3r.companion.utils

object ApduUtils {

    // --- APDU BUILDERS ---

    /** Build a SELECT (AID) APDU. */
    fun buildSelectAidApdu(aid: String): ByteArray {
        val aidBytes = HexUtils.hexToBytes(aid)
        return byteArrayOf(0x00, 0xA4.toByte(), 0x04, 0x00, aidBytes.size.toByte()) + aidBytes
    }

    /** Build a SELECT PPSE APDU. */
    fun buildSelectPpseApdu(): ByteArray {
        val ppse = "325041592E5359532E4444463031"
        return buildSelectAidApdu(ppse)
    }

    /** Build a GPO (Get Processing Options) APDU with PDOL data. */
    fun buildGpoApdu(pdol: ByteArray): ByteArray {
        // Construct PDOL template: 0x83 LEN <PDOL>
        val pdolTemplate = byteArrayOf(0x83.toByte(), pdol.size.toByte()) + pdol
        return byteArrayOf(0x80.toByte(), 0xA8.toByte(), 0x00, 0x00, pdolTemplate.size.toByte()) + pdolTemplate
    }

    /** Build a READ RECORD APDU (SFI, record number). */
    fun buildReadRecordApdu(record: Int, sfi: Int): ByteArray {
        val p2 = ((sfi shl 3) or 4).toByte()
        return byteArrayOf(0x00, 0xB2.toByte(), record.toByte(), p2, 0x00)
    }

    /** Build a VERIFY PIN APDU with pin block (ISO 9564-1 Format 0). */
    fun buildVerifyPinApdu(pin: String): ByteArray {
        val pinDigits = pin.filter { it.isDigit() }
        val pinLen = pinDigits.length.coerceAtMost(12)
        val block = ByteArray(8) { 0xFF.toByte() }
        block[0] = 0x20.toByte() or pinLen.toByte()
        for (i in 0 until pinLen) {
            val d = pinDigits[i].toString().toInt()
            if (i % 2 == 0) block[1 + i / 2] = (d shl 4).toByte()
            else block[1 + i / 2] = (block[1 + i / 2].toInt() or d).toByte()
        }
        return byteArrayOf(0x00, 0x20, 0x00, 0x80.toByte(), 0x08) + block
    }

    /** Build a GENERATE AC APDU (ARQC) with CDOL1 data. */
    fun buildGenerateAcApdu(data: ByteArray, acType: Int = 0x80): ByteArray {
        // acType: 0x80 = ARQC, 0x40 = TC, 0x00 = AAC
        return byteArrayOf(0x80.toByte(), 0xAE.toByte(), acType.toByte(), 0x00, data.size.toByte()) + data
    }

    // --- APDU RESPONSE PARSERS ---

    /** Returns SW1/SW2 (status word) from APDU response. */
    fun getStatusWord(resp: ByteArray): Int {
        if (resp.size < 2) return -1
        return (resp[resp.size - 2].toInt() shl 8) or (resp[resp.size - 1].toInt() and 0xFF)
    }

    /** Returns data (excluding SW1/SW2) from APDU response. */
    fun getData(resp: ByteArray): ByteArray {
        if (resp.size < 2) return byteArrayOf()
        return resp.copyOf(resp.size - 2)
    }

    /** Returns true if APDU SW == 0x9000 (success). */
    fun isSuccess(resp: ByteArray): Boolean = getStatusWord(resp) == 0x9000
}
