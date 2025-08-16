// =====================================================================
// File: HceService.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Host Card Emulation: responds to APDU select/GPO/GENAC/VERIFY from
//   POS terminals, uses active CardProfile, supports PIN-less flows,
//   replay, and cryptogram return. Parity with desktop replay logic.
// =====================================================================

package com.nfsp00f3r.companion

import android.nfc.cardemulation.HostApduService
import android.os.Bundle
import android.util.Log
import org.json.JSONObject

class HceService : HostApduService() {

    companion object {
        // Example AID for Visa/Mastercard test; should match desktop/app config
        private val SUPPORTED_AIDS = listOf(
            "A0000000031010", "A0000000041010"
        )
        // Magic APDU for status/echo
        private val STATUS_APDU = byteArrayOf(0x00.toByte(), 0xCA.toByte(), 0xDE.toByte(), 0xAD.toByte())
    }

    private val profileRepo: CardRepository by lazy {
        CardRepository.getInstance(applicationContext)
    }

    // Holds currently selected card for HCE replay
    private var activeCard: CardProfile? = null

    override fun processCommandApdu(commandApdu: ByteArray, extras: Bundle?): ByteArray {
        Log.d("HCE", "APDU RX: ${commandApdu.toHexString()}")
        // Handle status APDU
        if (commandApdu.contentEquals(STATUS_APDU)) {
            return "NFSP00F3R OK".toByteArray() + byteArrayOf(0x90.toByte(), 0x00.toByte())
        }
        // On SELECT PPSE or SELECT AID, respond as per profile
        if (commandApdu.size >= 5 && commandApdu[1] == 0xA4.toByte()) {
            val aid = commandApdu.copyOfRange(5, commandApdu.size).toHexString()
            Log.d("HCE", "SELECT AID $aid")
            val card = getActiveCard()
            if (card != null && SUPPORTED_AIDS.any { aid.contains(it) }) {
                // Return FCI Template (dummy or loaded from profile)
                val fci = buildFciTemplate(card)
                return fci + byteArrayOf(0x90.toByte(), 0x00.toByte())
            }
        }
        // On GPO/GENAC: respond with cryptogram from card
        if (commandApdu.size >= 4 && commandApdu[1] == 0xA8.toByte()) {
            val card = getActiveCard()
            if (card != null && card.cryptograms.isNotEmpty()) {
                return card.cryptograms[0].hexToBytes() + byteArrayOf(0x90.toByte(), 0x00.toByte())
            }
        }
        // VERIFY: always success for PIN-less
        if (commandApdu.size >= 4 && commandApdu[1] == 0x20.toByte()) {
            return byteArrayOf(0x90.toByte(), 0x00.toByte())
        }
        // Default: return SW 6A82 (File not found)
        return byteArrayOf(0x6A.toByte(), 0x82.toByte())
    }

    override fun onDeactivated(reason: Int) {
        Log.d("HCE", "Deactivated: $reason")
    }

    private fun getActiveCard(): CardProfile? {
        // Returns the active card (most recent, or pinned in prefs)
        if (activeCard != null) return activeCard
        val cards = profileRepo.allCards.value ?: return null
        return if (cards.isNotEmpty()) cards.last() else null
    }

    private fun buildFciTemplate(card: CardProfile): ByteArray {
        // Dummy FCI: tag 6F, contains 84 (AID), 50 (label)
        val aid = card.pan.padEnd(16, '0').substring(0, 16) // not really AID, but for demo
        val label = (card.name ?: "nfsp00f3r").padEnd(8, ' ')
        val fci = byteArrayOf(
            0x6F, 0x1A, // FCI template, length 26
            0x84, 0x08
        ) + aid.hexToBytes().take(8).toByteArray() +
            byteArrayOf(0x50, 0x08) +
            label.toByteArray()
        return fci
    }

    // Extension: Converts bytearray to hex string
    private fun ByteArray.toHexString(): String =
        joinToString("") { "%02X".format(it) }

    // Extension: Converts hex string to bytearray
    private fun String.hexToBytes(): ByteArray {
        val clean = replace(Regex("[^0-9A-Fa-f]"), "")
        val out = ByteArray(clean.length / 2)
        for (i in out.indices) {
            out[i] = clean.substring(i*2, i*2+2).toInt(16).toByte()
        }
        return out
    }
}
