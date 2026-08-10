package uz.vijdon.driver.data.push

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import androidx.work.Constraints
import androidx.work.NetworkType
import androidx.work.OneTimeWorkRequestBuilder
import androidx.work.WorkManager
import androidx.work.workDataOf

/**
 * Bildirishnomadagi "Qabul qilish"/"Rad etish" tugmalari — ilovani ochmasdan,
 * to'g'ridan-to'g'ri bildirishnoma panelidan (boshqa ilova ustida turgan
 * holatda ham) buyurtmaga javob berish uchun. Haqiqiy tarmoq so'rovini
 * o'zi emas, `OrderActionWorker` (WorkManager) bajaradi — chunki oddiy
 * `BroadcastReceiver.onReceive()` juda qisqa vaqt ichida qaytishi shart,
 * tizim esa (ayniqsa OEM'larning quvvat tejash rejimida) shu zahotiyoq
 * jarayonni to'xtatib qo'yishi mumkin, so'rov hech qachon yetib bormasdan.
 */
class OrderActionReceiver : BroadcastReceiver() {

    override fun onReceive(context: Context, intent: Intent) {
        val orderId = intent.getIntExtra(EXTRA_ORDER_ID, -1)
        if (orderId == -1) return
        val notificationId = intent.getIntExtra(EXTRA_NOTIFICATION_ID, orderId)

        val request = OneTimeWorkRequestBuilder<OrderActionWorker>()
            .setInputData(
                workDataOf(
                    OrderActionWorker.KEY_ORDER_ID to orderId,
                    OrderActionWorker.KEY_ACTION to intent.action,
                    OrderActionWorker.KEY_NOTIFICATION_ID to notificationId,
                ),
            )
            .setConstraints(Constraints.Builder().setRequiredNetworkType(NetworkType.CONNECTED).build())
            .build()
        WorkManager.getInstance(context).enqueue(request)

        // Foydalanuvchiga darhol javob berildi degan taassurot uchun
        // bildirishnoma shu zahoti yopiladi — haqiqiy so'rov WorkManager
        // orqali fonda (kerak bo'lsa tarmoq kutib) kafolatlangan bajariladi.
        NotificationManagerCompat.from(context).cancel(notificationId)
    }

    companion object {
        const val ACTION_ACCEPT = "uz.vijdon.driver.action.ACCEPT_ORDER"
        const val ACTION_REJECT = "uz.vijdon.driver.action.REJECT_ORDER"
        const val EXTRA_ORDER_ID = "extra_order_id"
        const val EXTRA_NOTIFICATION_ID = "extra_notification_id"
    }
}
