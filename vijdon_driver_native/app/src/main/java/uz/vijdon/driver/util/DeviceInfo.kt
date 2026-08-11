package uz.vijdon.driver.util

import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.BatteryManager
import android.os.Build

/**
 * Server real qurilma holatini kuzatib turishi uchun (operator panelida
 * ko'rsatish) — qurilma modeli va batareya foizi. `model` statik
 * (Context kerak emas), `batteryPercent` esa har chaqirilganda tizimdan
 * so'nggi ma'lum qiymatni o'qiydi.
 */
object DeviceInfo {
    val model: String = "${Build.MANUFACTURER} ${Build.MODEL}".trim()

    /** Haqiqiy vaqtdagi batareya foizi (0..100), aniqlab bo'lmasa `null`.
     * Doimiy ro'yxatdan o'tgan BroadcastReceiver shart emas — `null` receiver
     * bilan ro'yxatga olish so'nggi "sticky" ACTION_BATTERY_CHANGED
     * intentini darhol qaytaradi (standart Android patterni). */
    fun batteryPercent(context: Context): Int? {
        val intent = context.registerReceiver(null, IntentFilter(Intent.ACTION_BATTERY_CHANGED)) ?: return null
        val level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1)
        val scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1)
        if (level < 0 || scale <= 0) return null
        return (level * 100) / scale
    }
}
