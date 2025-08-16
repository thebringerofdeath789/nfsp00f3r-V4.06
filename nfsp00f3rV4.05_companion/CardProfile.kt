// =====================================================================
// File: CardProfile.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Data class for EMV card profiles, including TLVs, PAN, expiry,
//   tracks, crypto, and serialization/parsing for BLE, HCE, and UI.
// =====================================================================

package com.nfsp00f3r.companion

import org.json.JSONArray
import org.json.JSONObject

data class CardProfile(
    val pan: String,
    val expiry: String?,
    val name: String?,
    val cvv: String?,
    val zip: String?,
    val pin: String?,
    val tlvs: List<TlvEntry> = listOf(),
    val track1: String? = null,
    val track2: String? = null,
    val cryptograms: List<String> = listOf(),
    val transactions: List<String> = listOf()
) {
    companion object {
        fun fromJson(json: JSONObject): CardProfile {
            return CardProfile(
                pan = json.optString("PAN"),
                expiry = json.optString("Expiry"),
                name = json.optString("Name"),
                cvv = json.optString("CVV"),
                zip = json.optString("ZIP"),
                pin = json.optString("PIN"),
                tlvs = parseTlvs(json.optJSONArray("TLVs")),
                track1 = json.optString("Track1", null),
                track2 = json.optString("Track2", null),
                cryptograms = json.optJSONArray("cryptograms")?.let { arr ->
                    List(arr.length()) { arr.getString(it) }
                } ?: listOf(),
                transactions = json.optJSONArray("transactions")?.let { arr ->
                    List(arr.length()) { arr.getString(it) }
                } ?: listOf()
            )
        }

        private fun parseTlvs(arr: JSONArray?): List<TlvEntry> {
            if (arr == null) return listOf()
            val list = mutableListOf<TlvEntry>()
            for (i in 0 until arr.length()) {
                val obj = arr.getJSONObject(i)
                list.add(TlvEntry(
                    tag = obj.getString("tag"),
                    value = obj.getString("value"),
                    name = obj.optString("name", null)
                ))
            }
            return list
        }
    }

    fun toJson(): JSONObject {
        val obj = JSONObject()
        obj.put("PAN", pan)
        obj.put("Expiry", expiry ?: "")
        obj.put("Name", name ?: "")
        obj.put("CVV", cvv ?: "")
        obj.put("ZIP", zip ?: "")
        obj.put("PIN", pin ?: "")
        obj.put("TLVs", JSONArray(tlvs.map { it.toJson() }))
        obj.put("Track1", track1 ?: "")
        obj.put("Track2", track2 ?: "")
        obj.put("cryptograms", JSONArray(cryptograms))
        obj.put("transactions", JSONArray(transactions))
        return obj
    }
}

data class TlvEntry(
    val tag: String,
    val value: String,
    val name: String? = null
) {
    fun toJson(): JSONObject {
        val obj = JSONObject()
        obj.put("tag", tag)
        obj.put("value", value)
        obj.put("name", name ?: "")
        return obj
    }
}
