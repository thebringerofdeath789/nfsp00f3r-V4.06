// =====================================================================
// File: ThemeUtils.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   Provides theme/light/dark toggling for all activities.
// =====================================================================

package com.nfsp00f3r.companion.utils

import android.content.Context
import androidx.appcompat.app.AppCompatDelegate

object ThemeUtils {
    fun toggleTheme(context: Context) {
        val mode = AppCompatDelegate.getDefaultNightMode()
        if (mode == AppCompatDelegate.MODE_NIGHT_YES) {
            AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_NO)
        } else {
            AppCompatDelegate.setDefaultNightMode(AppCompatDelegate.MODE_NIGHT_YES)
        }
    }
}
