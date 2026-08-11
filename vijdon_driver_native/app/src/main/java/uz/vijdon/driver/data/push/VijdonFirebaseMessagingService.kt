package uz.vijdon.driver.data.push

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
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
        val isNewOrder = message.data["type"] == "new_order"
        val channelId = if (isNewOrder) "new_orders_channel" else "duty_channel"
        val notificationId = message.messageId?.hashCode() ?: 0

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            if (isNewOrder) putExtra(MainActivity.EXTRA_NEW_ORDER_ALERT, true)
        }
        val pendingIntent = PendingIntent.getActivity(
            this, notificationId, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = NotificationCompat.Builder(this, channelId)
            .setContentTitle(title)
            .setContentText(body)
            // `body` bir necha qatorli bo'lishi mumkin (manzil + izoh) —
            // BigTextStyle bo'lmasa, tizim standart bildirishnomani
            // BITTA qatorga qisqartirib qo'yardi, izoh ko'rinmay qolardi.
            .setStyle(NotificationCompat.BigTextStyle().bigText(body))
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setAutoCancel(true)

        if (isNewOrder) {
            // "To'liq ekran" bildirishnoma — ilova fonda yoki qurilma
            // qulflangan bo'lsa ham, xuddi kiruvchi qo'ng'iroqdek, boshqa
            // ilovalar ustidan avtomatik ochiladi. Ekran yoqilgan/qulfsiz
            // bo'lsa tizim buni faqat "heads-up" bildirishnoma sifatida
            // ko'rsatadi (bu ham boshqa ilova ustida ko'rinadi).
            builder.priority = NotificationCompat.PRIORITY_HIGH
            builder.setCategory(NotificationCompat.CATEGORY_CALL)
            val canUseFullScreen = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE ||
                getSystemService(NotificationManager::class.java).canUseFullScreenIntent()
            if (canUseFullScreen) {
                builder.setFullScreenIntent(pendingIntent, true)
            }

            // Ilovani ochmasdan, to'g'ridan-to'g'ri bildirishnoma panelidan
            // qabul qilish/rad etish — DriverLocationService'dagi zaxira
            // (polling) bildirishnomasi bilan bir xil OrderActionReceiver
            // mexanizmi orqali.
            val orderId = message.data["order_id"]?.toIntOrNull()
            if (orderId != null) {
                builder.addAction(0, "✅ Qabul qilish", orderActionPendingIntent(orderId, notificationId, OrderActionReceiver.ACTION_ACCEPT))
                builder.addAction(0, "❌ Rad etish", orderActionPendingIntent(orderId, notificationId, OrderActionReceiver.ACTION_REJECT))
            }
        }

        NotificationManagerCompat.from(this).notify(notificationId, builder.build())
    }

    private fun orderActionPendingIntent(orderId: Int, notificationId: Int, actionName: String): PendingIntent {
        val intent = Intent(this, OrderActionReceiver::class.java).apply {
            action = actionName
            putExtra(OrderActionReceiver.EXTRA_ORDER_ID, orderId)
            putExtra(OrderActionReceiver.EXTRA_NOTIFICATION_ID, notificationId)
        }
        val requestCode = orderId * 10 + (if (actionName == OrderActionReceiver.ACTION_ACCEPT) 1 else 2)
        return PendingIntent.getBroadcast(this, requestCode, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }
}
