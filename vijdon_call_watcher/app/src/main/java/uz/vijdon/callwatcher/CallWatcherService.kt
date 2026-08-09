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
import android.os.Handler
import android.os.IBinder
import android.os.Looper
import android.os.SystemClock
import android.telephony.TelephonyManager
import android.util.Log
import android.view.ContextThemeWrapper
import android.webkit.WebView
import android.widget.Toast
import androidx.core.app.NotificationCompat
import java.text.SimpleDateFormat
import java.util.Date
import java.util.Locale

/**
 * Doimiy (foreground) xizmat — qurilmaga qo'ng'iroq kelganda raqamni ushlab,
 * saytga yuboradi. Saytga ulanish uchun oddiy HTTP so'rov emas, balki
 * WebView (haqiqiy brauzer dvigateli) ishlatiladi — sababi: server oldidagi
 * bot-tekshiruv (JS challenge) faqat JavaScript bajaradigan mijozlarni
 * o'tkazadi (SiteSession.kt'ga qarang). Ilova recents'dan o'chirilsa yoki
 * tizim tomonidan to'xtatilsa ham ishlashda davom etishi uchun START_STICKY +
 * onTaskRemoved orqali qayta ishga tushirish qo'llanilgan.
 *
 * Qo'ng'iroq audiosi: Android uchinchi tomon ilovalarga qo'ng'iroq vaqtida
 * mikrofon/telefoniya ovozini bermaydi (sinovdan o'tgan — hamma manba jim
 * chiqadi), shuning uchun to'g'ridan-to'g'ri yozib olishga urinilmaydi.
 * Buning o'rniga telefonning O'Z Dialer ilovasi (agar shunday funksiyasi
 * bo'lsa) saqlagan yozuvni MediaStore'dan topib, saytga yuklaymiz
 * (NativeRecordingWatcher.kt'ga qarang).
 */
class CallWatcherService : Service() {

    private var webView: WebView? = null
    private var siteSession: SiteSession? = null
    private var receiverRegistered = false
    private var lastReportedNumber: String? = null
    private var lastReportedAt: Long = 0L

    private var pendingCallNumber: String? = null
    private var answeredCallNumber: String? = null
    private val recordingHandler = Handler(Looper.getMainLooper())

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
        createNotificationChannel()
        try {
            startForeground(NOTIF_ID, buildNotification())
        } catch (e: Exception) {
            Log.e(TAG, "startForeground xatosi", e)
        }
        try {
            val themedContext = ContextThemeWrapper(applicationContext, R.style.Theme_CallWatcher)
            val wv = WebView(themedContext)
            webView = wv
            siteSession = SiteSession(this, wv)
        } catch (e: Exception) {
            Log.e(TAG, "WebView yaratishda xato", e)
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
        recordingHandler.removeCallbacksAndMessages(null)
        if (receiverRegistered) {
            try {
                unregisterReceiver(phoneStateReceiver)
            } catch (e: Exception) {
                Log.w(TAG, "Receiverni bekor qilishda xato", e)
            }
        }
        try {
            webView?.destroy()
        } catch (e: Exception) {
            Log.w(TAG, "WebView'ni tozalashda xato", e)
        }
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
        when (state) {
            TelephonyManager.EXTRA_STATE_RINGING -> handleRinging(intent)
            TelephonyManager.EXTRA_STATE_OFFHOOK -> handleOffhook()
            TelephonyManager.EXTRA_STATE_IDLE     -> handleIdle()
        }
    }

    private fun handleRinging(intent: Intent) {
        val number = intent.getStringExtra(TelephonyManager.EXTRA_INCOMING_NUMBER)
        if (number.isNullOrBlank()) {
            Log.w(TAG, "Qo'ng'iroq raqami bo'sh keldi (ruxsat berilmagan yoki operator yashirgan)")
            return
        }
        pendingCallNumber = number

        // Bitta qo'ng'iroq uchun RINGING broadcast bir necha marta kelishi mumkin —
        // shu raqam uchun 10 soniya ichida faqat bitta so'rov yuboriladi.
        val now = System.currentTimeMillis()
        if (number == lastReportedNumber && now - lastReportedAt < 10_000) return
        lastReportedNumber = number
        lastReportedAt = now

        val prefs = Prefs(applicationContext)
        if (!prefs.loggedIn) {
            Log.w(TAG, "Kirilmagan — avval ilovaga login qiling")
            return
        }
        val session = siteSession
        if (session == null) {
            Log.e(TAG, "SiteSession tayyor emas")
            return
        }

        // handlePhoneStateChanged asosiy (UI) thread'da ishlaydi (registerReceiver
        // Handler'siz chaqirilgan), WebView ham faqat shu thread'dan ishlatilishi
        // shart — shuning uchun to'g'ridan-to'g'ri, alohida thread'siz chaqiramiz.
        session.reportIncomingCall(prefs.siteUrl, number) { success, detail ->
            val time = SimpleDateFormat("HH:mm", Locale.getDefault()).format(Date())
            if (success) {
                Log.i(TAG, "Qo'ng'iroq yuborildi: $number ($detail)")
                Toast.makeText(applicationContext, getString(R.string.notif_call_sent, number, time), Toast.LENGTH_LONG).show()
                updateNotification(getString(R.string.notif_call_sent, number, time))
            } else {
                Log.e(TAG, "Qo'ng'iroqni yuborib bo'lmadi: $number ($detail)")
                val text = getString(R.string.notif_call_failed, number, time) + " [$detail]"
                Toast.makeText(applicationContext, text, Toast.LENGTH_LONG).show()
                updateNotification(text)
            }
        }
    }

    /** Qo'ng'iroq javob berildi (OFFHOOK) — faqat RINGING'dan keyin kelgan (ya'ni
     * kiruvchi) qo'ng'iroqlar uchun kuzatamiz, operator o'zi chiqish qo'ng'iroq
     * qilganda emas (u holda RINGING kelmaydi, pendingCallNumber bo'sh bo'ladi). */
    private fun handleOffhook() {
        val number = pendingCallNumber ?: return
        pendingCallNumber = null
        answeredCallNumber = number
    }

    /** Qo'ng'iroq tugadi — telefonning o'z Dialer ilovasi yozib olgan bo'lsa,
     * MediaStore'da bir necha marta (kechikish bilan) qidirib, topilsa saytga
     * yuklaymiz. */
    private fun handleIdle() {
        pendingCallNumber = null
        val number = answeredCallNumber ?: return
        answeredCallNumber = null
        scheduleRecordingSearch(number, System.currentTimeMillis(), attempt = 1)
    }

    private fun scheduleRecordingSearch(number: String, callEndedAt: Long, attempt: Int) {
        val delayMs = SEARCH_DELAYS_MS.getOrElse(attempt - 1) { SEARCH_DELAYS_MS.last() }
        recordingHandler.postDelayed({
            try {
                val file = NativeRecordingWatcher(applicationContext).findRecentRecording(callEndedAt - 3000)
                if (file != null) {
                    uploadNativeRecording(number, file)
                } else if (attempt < SEARCH_DELAYS_MS.size) {
                    scheduleRecordingSearch(number, callEndedAt, attempt + 1)
                } else {
                    Log.w(TAG, "Native qo'ng'iroq yozuvi topilmadi: $number (telefonda bunday funksiya yo'q yoki boshqa papkaga saqlanadi)")
                }
            } catch (e: Exception) {
                Log.e(TAG, "Native yozuvni qidirishda xato", e)
            }
        }, delayMs)
    }

    private fun uploadNativeRecording(number: String, file: java.io.File) {
        val prefs = Prefs(applicationContext)
        val session = siteSession
        if (!prefs.loggedIn || session == null) {
            file.delete()
            return
        }
        session.uploadCallRecording(prefs.siteUrl, number, file, 0) { success, detail ->
            if (success) {
                Log.i(TAG, "Qo'ng'iroq yozuvi yuklandi: $number ($detail)")
                toast(getString(R.string.rec_uploaded_native))
                file.delete()
            } else {
                Log.e(TAG, "Qo'ng'iroq yozuvini yuklab bo'lmadi: $number ($detail)")
                toast(getString(R.string.rec_upload_failed, detail))
            }
        }
    }

    private fun toast(text: String) {
        Toast.makeText(applicationContext, text, Toast.LENGTH_LONG).show()
    }

    private fun updateNotification(text: String) {
        try {
            val manager = getSystemService(NotificationManager::class.java)
            manager?.notify(NOTIF_ID, buildNotification(text))
        } catch (e: Exception) {
            Log.w(TAG, "Bildirishnomani yangilashda xato", e)
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

    private fun buildNotification(statusText: String = getString(R.string.notif_text)): Notification {
        val openAppIntent = Intent(this, MainActivity::class.java)
        val contentIntent = PendingIntent.getActivity(
            this, 0, openAppIntent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE
        )
        return NotificationCompat.Builder(this, CHANNEL_ID)
            .setContentTitle(getString(R.string.notif_title))
            .setContentText(statusText)
            .setStyle(NotificationCompat.BigTextStyle().bigText(statusText))
            .setSmallIcon(R.drawable.ic_stat_call)
            .setOngoing(true)
            .setContentIntent(contentIntent)
            .build()
    }

    companion object {
        private const val TAG = "VijdonCallWatcher"
        private const val CHANNEL_ID = "call_watcher_channel"
        private const val NOTIF_ID = 42

        // Native yozuvchi faylni MediaStore'ga saqlab ulgurishi uchun qo'ng'iroq
        // tugagandan keyin bir necha marta, oralig'ini kattalashtirib qidiramiz.
        private val SEARCH_DELAYS_MS = longArrayOf(3000, 4000, 6000, 8000)
    }
}
