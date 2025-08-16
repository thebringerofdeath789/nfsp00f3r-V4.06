// =====================================================================
// File: HexUtils.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Utility for hex encoding/decoding.
// =====================================================================

package com.nfsp00f3r.companion.utils

object HexUtils {
    fun bytesToHex(bytes: ByteArray): String =
        bytes.joinToString("") { "%02X".format(it) }

    fun hexToBytes(hex: String): ByteArray {
        val clean = hex.replace(Regex("[^0-9A-Fa-f]"), "")
        val out = ByteArray(clean.length / 2)
        for (i in out.indices) {
            out[i] = clean.substring(i * 2, i * 2 + 2).toInt(16).toByte()
        }
        return out
    }
}
