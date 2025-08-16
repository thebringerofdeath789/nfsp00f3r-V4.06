// =====================================================================
// File: ReplayActivity.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Lets user select a card profile, then start HCE (or PN532 if supported).
//   Supports PIN-less, emulation mode switch, and shows result logs.
// =====================================================================

package com.nfsp00f3r.companion

import android.content.ComponentName
import android.content.Intent
import android.nfc.cardemulation.CardEmulation
import android.os.Bundle
import android.provider.Settings
import android.view.View
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Observer
import com.nfsp00f3r.companion.databinding.ActivityReplayBinding

class ReplayActivity : AppCompatActivity() {

    private lateinit var binding: ActivityReplayBinding
    private lateinit var repo: CardRepository
    private var selectedCard: CardProfile? = null

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityReplayBinding.inflate(layoutInflater)
        setContentView(binding.root)
        repo = CardRepository.getInstance(this)

        val cardList = repo.allCards.value ?: listOf()
        val panList = cardList.map { "${it.pan}  ${it.name ?: ""}" }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, panList)
        binding.spinnerCards.adapter = adapter

        binding.spinnerCards.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>, view: View?, pos: Int, id: Long) {
                selectedCard = cardList.getOrNull(pos)
                updateCardDetails(selectedCard)
            }
            override fun onNothingSelected(parent: AdapterView<*>) {
                selectedCard = null
            }
        }

        binding.switchPinless.setOnCheckedChangeListener { _, isChecked ->
            // Optionally toggle local flag for PIN-less
        }

        binding.btnReplay.setOnClickListener { runReplay() }
        binding.btnSetDefault.setOnClickListener { setAsDefaultCard() }
        binding.btnHceSettings.setOnClickListener { openHceSettings() }

        repo.allCards.observe(this, Observer {
            // Repopulate spinner if cards change
            val updatedList = it.map { card -> "${card.pan}  ${card.name ?: ""}" }
            val ad = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, updatedList)
            binding.spinnerCards.adapter = ad
        })
    }

    private fun updateCardDetails(card: CardProfile?) {
        if (card == null) {
            binding.txtReplayStatus.text = "No card selected."
            return
        }
        binding.txtReplayStatus.text = """
            PAN: ${card.pan}
            Name: ${card.name}
            Expiry: ${card.expiry}
            Track2: ${card.track2}
        """.trimIndent()
    }

    private fun runReplay() {
        val card = selectedCard ?: return
        // Tell HCE service to use this card (in-memory, or via repo)
        Toast.makeText(this, "Starting HCE replay for ${card.pan}", Toast.LENGTH_LONG).show()
        enableHceService()
        // Optionally log or show success/fail
        binding.txtReplayStatus.append("\nHCE started. Tap device to POS.")
    }

    private fun setAsDefaultCard() {
        val card = selectedCard ?: return
        repo.saveCard(card) // Will move card to end (becomes default for HCE)
        Toast.makeText(this, "Set as default replay card.", Toast.LENGTH_SHORT).show()
    }

    private fun openHceSettings() {
        val intent = Intent(Settings.ACTION_NFC_PAYMENT_SETTINGS)
        startActivity(intent)
    }

    private fun enableHceService() {
        val ce = CardEmulation.getInstance(null)
        val componentName = ComponentName(this, HceService::class.java)
        ce.setPreferredService(this, componentName)
    }
}
