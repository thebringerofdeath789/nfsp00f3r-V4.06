// =====================================================================
// File: BleService.kt
// Project: nfsp00f3r Companion - Android BLE/HCE App
// Authors: Gregory King & Matthew Braunschweig
// Date: 2025-08-04
//
// Description:
//   BLE service for GATT communication with desktop, chunked JSON
//   transfer, scan, notification, and live status. No PyBluez.
// =====================================================================

package com.nfsp00f3r.companion

import android.annotation.SuppressLint
import android.app.Service
import android.bluetooth.*
import android.bluetooth.le.*
import android.content.Context
import android.content.Intent
import android.os.Binder
import android.os.IBinder
import android.os.ParcelUuid
import androidx.lifecycle.LiveData
import androidx.lifecycle.MutableLiveData
import com.nfsp00f3r.companion.CardProfile
import org.json.JSONObject
import java.nio.charset.Charset
import java.util.*

class BleService : Service() {

    companion object {
        val SERVICE_UUID: UUID = UUID.fromString("d9a9fc49-143c-46be-9c86-78be20c7d776")
        val CARD_CHAR_UUID: UUID = UUID.fromString("bb2cfd0d-690a-4cf6-96f7-07dc6e6c13a0")
        val CMD_CHAR_UUID: UUID = UUID.fromString("1b3e39d2-ecf7-4dc1-8e8a-c0b34f6e8c12")
        private var instance: BleService? = null
        fun getInstance(context: Context): BleService {
            if (instance == null) {
                instance = BleService()
            }
            return instance!!
        }
    }

    enum class BleStatus { OFF, SCANNING, PAIRED, CONNECTED }

    private val bleStatusMutable = MutableLiveData(BleStatus.OFF)
    val bleStatus: LiveData<BleStatus> get() = bleStatusMutable

    private var bluetoothGatt: BluetoothGatt? = null
    private var gattCallback: BluetoothGattCallback? = null
    private var cardReceiver: ((CardProfile) -> Unit)? = null
    private var buffer = StringBuilder()

    override fun onBind(intent: Intent?): IBinder = Binder()

    fun setCardReceiver(callback: (CardProfile) -> Unit) {
        this.cardReceiver = callback
    }

    @SuppressLint("MissingPermission")
    fun startScanAndReceive() {
        bleStatusMutable.postValue(BleStatus.SCANNING)
        val bluetoothAdapter = (getSystemService(Context.BLUETOOTH_SERVICE) as BluetoothManager).adapter
        val scanner = bluetoothAdapter.bluetoothLeScanner
        val filter = ScanFilter.Builder()
            .setServiceUuid(ParcelUuid(SERVICE_UUID)).build()
        val settings = ScanSettings.Builder().setScanMode(ScanSettings.SCAN_MODE_LOW_LATENCY).build()
        scanner.startScan(listOf(filter), settings, object : ScanCallback() {
            override fun onScanResult(callbackType: Int, result: ScanResult) {
                scanner.stopScan(this)
                connectToDevice(result.device)
            }
            override fun onScanFailed(errorCode: Int) {
                bleStatusMutable.postValue(BleStatus.OFF)
            }
        })
    }

    @SuppressLint("MissingPermission")
    fun connectToDevice(device: BluetoothDevice) {
        bleStatusMutable.postValue(BleStatus.PAIRED)
        gattCallback = object : BluetoothGattCallback() {
            override fun onConnectionStateChange(gatt: BluetoothGatt, status: Int, newState: Int) {
                if (newState == BluetoothProfile.STATE_CONNECTED) {
                    bleStatusMutable.postValue(BleStatus.CONNECTED)
                    gatt.discoverServices()
                } else {
                    bleStatusMutable.postValue(BleStatus.OFF)
                }
            }

            override fun onServicesDiscovered(gatt: BluetoothGatt, status: Int) {
                val cardChar = gatt.getService(SERVICE_UUID)?.getCharacteristic(CARD_CHAR_UUID)
                cardChar?.let {
                    gatt.setCharacteristicNotification(it, true)
                }
            }

            override fun onCharacteristicChanged(gatt: BluetoothGatt, characteristic: BluetoothGattCharacteristic) {
                if (characteristic.uuid == CARD_CHAR_UUID) {
                    val data = characteristic.value.toString(Charset.forName("UTF-8"))
                    buffer.append(data)
                    if (data.endsWith("}")) {
                        try {
                            val json = JSONObject(buffer.toString())
                            val card = CardProfile.fromJson(json)
                            cardReceiver?.invoke(card)
                        } catch (e: Exception) { /* Ignore bad JSON */ }
                        buffer.clear()
                    }
                }
            }
        }
        bluetoothGatt = device.connectGatt(this, false, gattCallback!!)
    }

    fun stopConnection() {
        bluetoothGatt?.close()
        bluetoothGatt = null
        bleStatusMutable.postValue(BleStatus.OFF)
    }
}
