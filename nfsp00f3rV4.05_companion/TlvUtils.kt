// =====================================================================
// File: TlvUtils.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Recursive EMV/BER TLV parser for multi-level, multi-byte tags and
//   constructed/nested trees. Full parity with desktop logic.
// =====================================================================

package com.nfsp00f3r.companion.utils

data class TLVNode(
    val tag: String,
    val length: Int,
    val value: ByteArray,
    val children: List<TLVNode> = listOf()
) {
    fun valueHex(): String = HexUtils.bytesToHex(value)
    fun valueAscii(): String? = value.decodeToString().takeIf { it.all { c -> c in ' '..'~' } }
}

object TlvUtils {
    /**
     * Parses BER-TLV/EMV data, returns all top-level TLVNode objects (recursive tree).
     */
    fun parse(data: ByteArray): List<TLVNode> {
        val nodes = mutableListOf<TLVNode>()
        var idx = 0
        while (idx < data.size) {
            val (tag, tagLen) = parseTag(data, idx)
            idx += tagLen
            if (idx >= data.size) break

            val (len, lenLen) = parseLength(data, idx)
            idx += lenLen
            if (idx + len > data.size) break

            val value = data.copyOfRange(idx, idx + len)
            idx += len

            // If tag is constructed (bit 6 set in first byte)
            val children = if (isConstructed(tag)) parse(value) else listOf()
            nodes.add(TLVNode(tag, len, value, children))
        }
        return nodes
    }

    // Parses tag (1 or more bytes), returns (tagHex, tagLength)
    private fun parseTag(data: ByteArray, start: Int): Pair<String, Int> {
        var idx = start
        val first = data[idx].toInt() and 0xFF
        idx++
        val tagBytes = mutableListOf<Byte>((first).toByte())
        // Multi-byte tag if bits 5-1 of first byte are all 1
        if ((first and 0x1F) == 0x1F) {
            while (idx < data.size) {
                val b = data[idx]
                tagBytes.add(b)
                idx++
                if ((b.toInt() and 0x80) == 0) break
            }
        }
        val tagHex = tagBytes.joinToString("") { "%02X".format(it) }
        return tagHex to tagBytes.size
    }

    // Parses length (short or long form), returns (length, bytesUsed)
    private fun parseLength(data: ByteArray, start: Int): Pair<Int, Int> {
        val first = data[start].toInt() and 0xFF
        if (first and 0x80 == 0) return first to 1
        val numBytes = first and 0x7F
        var len = 0
        for (i in 1..numBytes) {
            len = (len shl 8) or (data[start + i].toInt() and 0xFF)
        }
        return len to (1 + numBytes)
    }

    // True if tag is constructed (bit 6 of first tag byte set)
    private fun isConstructed(tag: String): Boolean {
        if (tag.length < 2) return false
        val firstByte = tag.substring(0, 2).toInt(16)
        return (firstByte and 0x20) != 0
    }
}
