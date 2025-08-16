// =====================================================================
// File: RelayActivity.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   UI and logic for live APDU relay mode: BLE pair, card select,
//   start/stop, real-time APDU color log, status indicators.
// =====================================================================

package com.nfsp00f3r.companion

import android.os.Bundle
import android.os.Handler
import android.os.Looper
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import androidx.lifecycle.Observer
import com.nfsp00f3r.companion.databinding.ActivityRelayBinding

class RelayActivity : AppCompatActivity() {

    private lateinit var binding: ActivityRelayBinding
    private lateinit var repo: CardRepository
    private lateinit var bleService: BleService
    private var selectedCard: CardProfile? = null
    private val relayLog = StringBuilder()
    private var isRelaying = false

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityRelayBinding.inflate(layoutInflater)
        setContentView(binding.root)
        repo = CardRepository.getInstance(this)
        bleService = BleService.getInstance(this)

        val cardList = repo.allCards.value ?: listOf()
        val panList = cardList.map { "${it.pan}  ${it.name ?: ""}" }
        val adapter = ArrayAdapter(this, android.R.layout.simple_spinner_dropdown_item, panList)
        binding.spinnerRelayCards.adapter = adapter

        binding.spinnerRelayCards.onItemSelectedListener = object : AdapterView.OnItemSelectedListener {
            override fun onItemSelected(parent: AdapterView<*>, view: android.view.View?, pos: Int, id: Long) {
                selectedCard = cardList.getOrNull(pos)
                updateCardDetails(selectedCard)
            }
            override fun onNothingSelected(parent: AdapterView<*>) {
                selectedCard = null
            }
        }

        binding.btnPairRelay.setOnClickListener { pairBle() }
        binding.btnStartRelay.setOnClickListener { startRelay() }
        binding.btnStopRelay.setOnClickListener { stopRelay() }

        bleService.bleStatus.observe(this, Observer { status ->
            binding.txtRelayStatus.text = "BLE: $status"
        })
    }

    private fun updateCardDetails(card: CardProfile?) {
        binding.txtRelayStatus.text = card?.let {
            "Ready to relay: ${it.pan}"
        } ?: "No card selected."
    }

    private fun pairBle() {
        bleService.startScanAndReceive()
        Handler(Looper.getMainLooper()).postDelayed({
            binding.txtRelayStatus.append("\nPaired. Ready to relay.")
        }, 3000)
    }

    private fun startRelay() {
        if (isRelaying) return
        val card = selectedCard ?: return
        relayLog.clear()
        isRelaying = true
        binding.txtRelayLog.text = ""
        // Relay loop, simplified for demo: in production, use APDU relay protocol
        bleService.setCardReceiver { apduCard ->
            if (!isRelaying) return@setCardReceiver
            val logEntry = "APDU RX: ${apduCard.pan}"
            relayLog.append(logEntry).append("\n")
            Handler(Looper.getMainLooper()).post {
                binding.txtRelayLog.append("$logEntry\n")
            }
        }
        binding.txtRelayStatus.append("\nRelay started.")
    }

    private fun stopRelay() {
        isRelaying = false
        bleService.setCardReceiver { }
        binding.txtRelayStatus.append("\nRelay stopped.")
    }
}
