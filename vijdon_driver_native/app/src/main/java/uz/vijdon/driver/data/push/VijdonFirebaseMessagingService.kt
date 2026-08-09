package uz.vijdon.driver.data.push

import android.app.PendingIntent
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.vijdon.driver.MainActivity
import uz.vijdon.driver.R
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

/**
 * FCM ishlashi uchun app/google-services.json fayli qo'shilishi va Firebase
 * loyihasi ulanishi kerak (rejaning 0.3-bandi) — fayl bo'lmasa bu servis
 * shunchaki hech qachon chaqirilmaydi, ilova build/ishga tushishiga
 * ta'sir qilmaydi.
 */
@AndroidEntryPoint
class VijdonFirebaseMessagingService : FirebaseMessagingService() {

    @Inject lateinit var repository: DriverRepository

    override fun onNewToken(token: String) {
        CoroutineScope(Dispatchers.IO).launch { repository.syncFcmToken(token) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        val title = message.notification?.title ?: message.data["title"] ?: "Vijdon Taxi"
        val body = message.notification?.body ?: message.data["body"] ?: ""
        val channelId = if (message.data["type"] == "new_order") "new_orders_channel" else "duty_channel"

        val intent = android.content.Intent(this, MainActivity::class.java)
        val pendingIntent = PendingIntent.getActivity(
            this, 0, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val notification = NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(body)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)
            .build()
        NotificationManagerCompat.from(this).notify(message.messageId?.hashCode() ?: 0, notification)
    }
}
