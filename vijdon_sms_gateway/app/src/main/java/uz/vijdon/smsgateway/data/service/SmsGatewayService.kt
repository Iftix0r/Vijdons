package uz.vijdon.smsgateway.data.service

import android.app.Notification
import android.app.Service
import android.content.Intent
import android.content.pm.ServiceInfo
import android.os.IBinder
import androidx.core.app.NotificationCompat
import androidx.core.app.ServiceCompat
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.MainActivity
import uz.vijdon.smsgateway.R
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import javax.inject.Inject

/**
 * "Ish navbatida" bo'lgan vaqt davomida ishlaydigan fon xizmati — muntazam
 * (`POLL_INTERVAL_MS`) navbatni tekshiradi va topilgan SMS'larni yuboradi.
 * Bu — ASOSIY (kafolatlangan) kanal; push (`SmsFirebaseMessagingService`)
 * esa faqat TEZLASHTIRISH uchun (push kelmasa yoki kechiksa ham, bu
 * xizmat baribir bir necha soniya ichida topib yuboraveradi).
 */
@AndroidEntryPoint
class SmsGatewayService : Service() {

    @Inject lateinit var repository: SmsGatewayRepository

    private val scope = CoroutineScope(SupervisorJob() + Dispatchers.IO)
    private var pollJob: kotlinx.coroutines.Job? = null

    override fun onCreate() {
        super.onCreate()
        startForegroundWithNotification()
        startPolling()
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onBind(intent: Intent?): IBinder? = null

    override fun onDestroy() {
        pollJob?.cancel()
        scope.cancel()
        super.onDestroy()
    }

    private fun startForegroundWithNotification() {
        val openIntent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        }
        val pendingIntent = android.app.PendingIntent.getActivity(
            this, 0, openIntent, android.app.PendingIntent.FLAG_UPDATE_CURRENT or android.app.PendingIntent.FLAG_IMMUTABLE,
        )
        val notification: Notification = NotificationCompat.Builder(this, "sms_gateway_channel")
            .setContentTitle("SMS-shlyuz ishlamoqda")
            .setContentText("Yangi SMS navbati kuzatilmoqda")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setOngoing(true)
            .build()
        ServiceCompat.startForeground(
            this, 1, notification,
            if (android.os.Build.VERSION.SDK_INT >= android.os.Build.VERSION_CODES.Q) ServiceInfo.FOREGROUND_SERVICE_TYPE_DATA_SYNC else 0,
        )
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = scope.launch {
            while (true) {
                val authInvalid = SmsSender.processPendingBatch(applicationContext, repository)
                if (authInvalid) {
                    // Token yaroqsiz (masalan admin parolni o'zgartirgan) —
                    // hisobdan chiqarib, xizmatni to'xtatamiz. Foydalanuvchi
                    // ilovani ochganda qayta kirish oynasini ko'radi
                    // (`SessionViewModel`, tokenStore bo'sh bo'lgani uchun).
                    repository.logout()
                    stopSelf()
                    return@launch
                }
                delay(POLL_INTERVAL_MS)
            }
        }
    }

    private companion object {
        const val POLL_INTERVAL_MS = 20_000L
    }
}
