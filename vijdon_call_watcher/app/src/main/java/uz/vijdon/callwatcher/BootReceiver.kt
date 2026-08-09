package uz.vijdon.callwatcher

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import android.util.Log

/** Qurilma qayta yoqilganda, oldin yoqilgan bo'lsa, kuzatuv xizmatini avtomatik ishga tushiradi. */
class BootReceiver : BroadcastReceiver() {
    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED && intent.action != "android.intent.action.QUICKBOOT_POWERON") {
            return
        }
        try {
            val prefs = Prefs(context)
            if (prefs.serviceEnabled && !prefs.token.isNullOrEmpty()) {
                val serviceIntent = Intent(context, CallWatcherService::class.java)
                if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                    context.startForegroundService(serviceIntent)
                } else {
                    context.startService(serviceIntent)
                }
            }
        } catch (e: Exception) {
            Log.e("VijdonBootReceiver", "Qayta yoqilishda xizmatni ishga tushirishda xato", e)
        }
    }
}
