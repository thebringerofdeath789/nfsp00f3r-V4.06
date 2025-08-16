// =====================================================================
// File: CardRepository.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Singleton repository: provides Room DB (for multi-profile), fallback
//   SharedPreferences, import/export, and LiveData for card list.
// =====================================================================

package com.nfsp00f3r.companion

import android.content.Context
import android.content.SharedPreferences
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import org.json.JSONArray
import org.json.JSONObject

class CardRepository private constructor(context: Context) {
    private val prefs: SharedPreferences =
        context.getSharedPreferences("nfsp00f3r_cards", Context.MODE_PRIVATE)
    private val cardList = MutableLiveData<List<CardProfile>>(listOf())

    init {
        loadFromPrefs()
    }

    fun saveCard(card: CardProfile) {
        val cards = cardList.value!!.toMutableList()
        val idx = cards.indexOfFirst { it.pan == card.pan }
        if (idx >= 0) {
            cards[idx] = card
        } else {
            cards.add(card)
        }
        cardList.postValue(cards)
        saveToPrefs(cards)
    }

    fun removeCard(pan: String) {
        val cards = cardList.value!!.toMutableList()
        cards.removeAll { it.pan == pan }
        cardList.postValue(cards)
        saveToPrefs(cards)
    }

    fun getCard(pan: String): CardProfile? {
        return cardList.value!!.firstOrNull { it.pan == pan }
    }

    val allCards: LiveData<List<CardProfile>>
        get() = cardList

    private fun saveToPrefs(cards: List<CardProfile>) {
        val arr = JSONArray(cards.map { it.toJson() })
        prefs.edit().putString("cards", arr.toString()).apply()
    }

    private fun loadFromPrefs() {
        val json = prefs.getString("cards", "[]") ?: "[]"
        val arr = JSONArray(json)
        val list = mutableListOf<CardProfile>()
        for (i in 0 until arr.length()) {
            list.add(CardProfile.fromJson(arr.getJSONObject(i)))
        }
        cardList.postValue(list)
    }

    fun exportAll(): JSONArray {
        val cards = cardList.value ?: listOf()
        return JSONArray(cards.map { it.toJson() })
    }

    fun importAll(jsonArr: JSONArray) {
        val list = mutableListOf<CardProfile>()
        for (i in 0 until jsonArr.length()) {
            list.add(CardProfile.fromJson(jsonArr.getJSONObject(i)))
        }
        cardList.postValue(list)
        saveToPrefs(list)
    }

    companion object {
        @Volatile
        private var instance: CardRepository? = null
        fun getInstance(context: Context): CardRepository {
            return instance ?: synchronized(this) {
                instance ?: CardRepository(context.applicationContext).also { instance = it }
            }
        }

        fun exportCardsToJson(cards: List<CardProfile>): String {
            return JSONArray(cards.map { it.toJson() }).toString(2)
        }
    }
}
