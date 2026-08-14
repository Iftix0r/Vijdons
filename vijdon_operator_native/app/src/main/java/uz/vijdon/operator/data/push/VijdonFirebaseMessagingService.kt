package uz.vijdon.operator.data.push

import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Intent
import android.os.Build
import androidx.core.app.NotificationCompat
import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.vijdon.operator.MainActivity
import uz.vijdon.operator.R
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

/** Operator ilovasi uchun push — `taxi/utils.py: notify_operators()`dan
 * kelgan `type` (`new_order`/`topup_request`/`sos`) bo'yicha mos kanal va
 * ikonka bilan ko'rsatiladi. Bosilganda ilova tegishli bo'limga ochiladi
 * (`OpenTabBus`) — driverapp'dagi "to'liq ekran"/tugmali harakatlar bu
 * bosqichda YO'Q, ataylab soddalashtirilgan (MVP). */
@AndroidEntryPoint
class VijdonFirebaseMessagingService : FirebaseMessagingService() {

    @Inject lateinit var repository: OperatorRepository

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        CoroutineScope(Dispatchers.IO).launch { repository.syncFcmToken(token) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        val data = message.data
        val type = data["type"] ?: "info"
        val title = data["title"] ?: "Vijdon Operator"
        val body = data["body"] ?: ""

        val (channel, tab) = when (type) {
            "new_order" -> "operator_alerts_channel" to "orders"
            "sos" -> "operator_alerts_channel" to "drivers"
            "topup_request" -> "operator_info_channel" to "balance"
            else -> "operator_info_channel" to "dashboard"
        }

        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(MainActivity.EXTRA_OPEN_TAB, tab)
        }
        val pendingIntent = PendingIntent.getActivity(
            this, System.currentTimeMillis().toInt(), intent,
            PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )

        val notification = NotificationCompat.Builder(this, channel)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentTitle(title)
            .setContentText(body)
            .setAutoCancel(true)
            .setPriority(if (channel == "operator_alerts_channel") NotificationCompat.PRIORITY_HIGH else NotificationCompat.PRIORITY_DEFAULT)
            .setContentIntent(pendingIntent)
            .build()

        val manager = getSystemService(NotificationManager::class.java)
        manager.notify(System.currentTimeMillis().toInt(), notification)
    }
}
