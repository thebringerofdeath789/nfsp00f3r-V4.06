// =====================================================================
// File: DebugActivity.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Debug log window with color-coded APDU/system logs, filter/search,
//   and export log to file or share intent.
// =====================================================================

package com.nfsp00f3r.companion

import android.content.Intent
import android.os.Bundle
import android.text.Editable
import android.text.TextWatcher
import android.widget.*
import androidx.appcompat.app.AppCompatActivity
import com.nfsp00f3r.companion.databinding.ActivityDebugBinding

class DebugActivity : AppCompatActivity() {

    private lateinit var binding: ActivityDebugBinding
    private val logLines = mutableListOf<String>()
    private val filteredLines = mutableListOf<String>()

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        binding = ActivityDebugBinding.inflate(layoutInflater)
        setContentView(binding.root)

        // Populate from BLE and card logs
        loadLogs()
        updateLogView()

        binding.editSearch.addTextChangedListener(object : TextWatcher {
            override fun afterTextChanged(s: Editable?) = filterLogs(s?.toString() ?: "")
            override fun beforeTextChanged(s: CharSequence?, start: Int, count: Int, after: Int) {}
            override fun onTextChanged(s: CharSequence?, start: Int, before: Int, count: Int) {}
        })

        binding.btnExportLog.setOnClickListener { exportLogs() }
    }

    private fun loadLogs() {
        // In production, gather logs from BLE/CardRepository/etc
        logLines.clear()
        logLines.addAll(DebugLogger.getLogs())
    }

    private fun updateLogView() {
        val showLines = if (binding.editSearch.text.isNullOrBlank()) logLines else filteredLines
        binding.txtLog.text = showLines.joinToString("\n")
    }

    private fun filterLogs(query: String) {
        filteredLines.clear()
        if (query.isBlank()) {
            updateLogView()
            return
        }
        filteredLines.addAll(logLines.filter { it.contains(query, ignoreCase = true) })
        updateLogView()
    }

    private fun exportLogs() {
        val logs = logLines.joinToString("\n")
        val sendIntent = Intent().apply {
            action = Intent.ACTION_SEND
            putExtra(Intent.EXTRA_TEXT, logs)
            type = "text/plain"
        }
        startActivity(Intent.createChooser(sendIntent, "Export Log"))
    }
}

// For this demo, DebugLogger is a singleton in-memory log buffer
object DebugLogger {
    private val logs = mutableListOf<String>()
    fun log(msg: String) { logs.add(msg) }
    fun getLogs(): List<String> = logs
}
