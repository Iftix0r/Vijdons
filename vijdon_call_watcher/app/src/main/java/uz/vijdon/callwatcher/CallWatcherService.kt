package uz.vijdon.callwatcher

import android.app.AlarmManager
import android.app.Notification
import android.app.NotificationChannel
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.content.IntentFilter
import android.os.Build
import android.os.IBinder
import android.os.SystemClock
import android.telephony.TelephonyManager
import android.util.Log
import androidx.core.app.NotificationCompat
import java.util.concurrent.ExecutorService
import java.util.concurrent.Executors

/**
 * Doimiy (foreground) xizmat — qurilmaga qo'ng'iroq kelganda raqamni ushlab,
 * saytga yuboradi. Ilova recents'dan o'chirilsa yoki tizim tomonidan
 * to'xtatilsa ham ishlashda davom etishi uchun START_STICKY + onTaskRemoved
 * orqali qayta ishga tushirish qo'llanilgan.
 */
class CallWatcherService : Service() {

    private lateinit var executor: ExecutorService
    private var receiverRegistered = false
    private var lastReportedNumber: String? = null
    private var lastReportedAt: Long = 0L

    private val phoneStateReceiver = object : BroadcastReceiver() {
        override fun onReceive(context: Context, intent: Intent) {
            try {
                handlePhoneStateChanged(intent)
            } catch (e: Exception) {
                Log.e(TAG, "Broadcast qayta ishlashda xato", e)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        executor = Executors.newSingleThreadExecutor()
        createNotificationChannel()
        try {
            startForeground(NOTIF_ID, buildNotification())
        } catch (e: Exception) {
            Log.e(TAG, "startForeground xatosi", e)
        }
        try {
            registerReceiver(phoneStateReceiver, IntentFilter(TelephonyManager.ACTION_PHONE_STATE_CHANGED))
            receiverRegistered = true
        } catch (e: Exception) {
            Log.e(TAG, "Receiver ro'yxatga olishda xato", e)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int {
        return START_STICKY
    }

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        if (receiverRegistered) {
            try {
                unregisterReceiver(phoneStateReceiver)
            } catch (e: Exception) {
                Log.w(TAG, "Receiverni bekor qilishda xato", e)
            }
        }
        executor.shutdownNow()
        super.onDestroy()
    }

    override fun onTaskRemoved(rootIntent: Intent?) {
        // Foydalanuvchi ilovani recents'dan surib tashlasa ham, xizmat 1 soniyadan
        // keyin avtomatik qayta ishga tushishi uchun.
        try {
            val restartIntent = Intent(applicationContext, CallWatcherService::class.java)
            val pending = PendingIntent.getService(
                applicationContext, 1, restartIntent,
                PendingIntent.FLAG_ONE_SHOT or PendingIntent.FLAG_IMMUTABLE
            )
            val alarmManager = getSystemService(Context.ALARM_SERVICE) as? AlarmManager
            alarmManager?.set(
                AlarmManager.ELAPSED_REALTIME,
                SystemClock.elapsedRealtime() + 1000,
                pending
            )
        } catch (e: Exception) {
            Log.e(TAG, "onTaskRemoved qayta ishga tushirishda xato", e)
        }
        super.onTaskRemoved(rootIntent)
    }

    private fun handlePhoneStateChanged(intent: Intent) {
        val state = intent.getStringExtra(TelephonyManager.EXTRA_STATE) ?: return
        if (state != TelephonyManager.EXTRA_STATE_RINGING) return

        val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
        if (number.isNullOrBlank()) {
            Log.w(TAG, "Qo'ng'iroq raqami bo'sh keldi (ruxsat berilmagan yoki operator yashirgan)")
            return
        }

        // Bitta qo'ng'iroq uchun RINGING broadcast bir necha marta kelishi mumkin —
        // shu raqam uchun 10 soniya ichida faqat bitta so'rov yuboriladi.
        val now = System.currentTimeMillis()
        if (number == lastReportedNumber && now - lastReportedAt < 10_000) return
        lastReportedNumber = number
        lastReportedAt = now

        val prefs = Prefs(applicationContext)
        val token = prefs.token
        if (token.isNullOrEmpty()) {
            Log.w(TAG, "Token yo'q — avval ilovaga kiring")
            return
        }

        val siteUrl = prefs.siteUrl
        executor.execute {
            try {
                ApiClient.reportIncomingCall(siteUrl, token, number)
            } catch (e: Exception) {
                Log.e(TAG, "reportIncomingCall xatosi", e)
            }
        }
    }

    private fun createNotificationChannel() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val channel = NotificationChannel(
                CHANNEL_ID,
                getString(R.string.notif_channel_name),
                NotificationManager.IMPORTANCE_LOW
            )
            val manager = getSystemService(NotificationManager::class.java)
            manager?.createNotificationChannel(channel)
        }
    }

    private fun buildNotification(): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java)
        val contentIntent = PendingIntent.getActivity(
            this, 0, openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(getString(R.string.notif_text))
            .setSmallIcon(R.drawable.ic_stat_call)
            .setOngoing(true)
            .setContentIntent(contentIntent)
            .build()
    }

    companion object {
        private const val TAG = "VijdonCallWatcher"
        private const val CHANNEL_ID = "call_watcher_channel"
        private const val NOTIF_ID = 42
    }
}
