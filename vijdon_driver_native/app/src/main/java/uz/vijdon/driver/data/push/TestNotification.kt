package uz.vijdon.driver.data.push

import android.Manifest
import android.app.NotificationManager
import android.app.PendingIntent
import android.content.Context
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Build
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import uz.vijdon.driver.MainActivity
import uz.vijdon.driver.R

private const val TEST_NOTIFICATION_ID = 3

/**
 * Ilova ishga tushganda bir marta chaqiriladigan SINOV bildirishnomasi —
 * bildirishnoma quvuri (kanal, ruxsat, to'liq ekranli intent) real
 * buyurtma kutmasdan darhol tekshirilishi uchun. `DriverLocationService.
 * showNewOrderNotification()` bilan AYNAN bir xil yo'l (kanal, ustuvorlik,
 * to'liq ekranli intent) ishlatiladi — shu sabab bu sinov haqiqatan real
 * buyurtma bildirishnomasi ishlaydimi yoki yo'qligini ko'rsatadi.
 * Sarlavhasida "SINOV" deb aniq yozilgan — real buyurtma bilan
 * chalkashtirib bo'lmaydi.
 *
 * Bosilganda `EXTRA_TEST_ORDER_ALERT` orqali ilova ichida SOXTA buyurtma
 * ma'lumotlari bilan to'liq ekranli "Yangi buyurtma" oynasi (qabul
 * qilish/rad etish tugmalari) ham ko'rsatiladi (`MainActivity` →
 * `TestAlertBus` → `HomeViewModel`) — shunda haqiqiy buyurtma kutmasdan
 * BUTUN oqim (bildirishnoma → to'liq ekran → tugmalar) sinaladi.
 */
fun sendTestNewOrderNotification(context: Context) {
    val intent = Intent(context, MainActivity::class.java).apply {
        flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
        putExtra(MainActivity.EXTRA_NEW_ORDER_ALERT, true)
        putExtra(MainActivity.EXTRA_TEST_ORDER_ALERT, true)
    }
    val pendingIntent = PendingIntent.getActivity(
        context, TEST_NOTIFICATION_ID, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )
    val actionIntent = { actionName: String ->
        Intent(context, OrderActionReceiver::class.java).apply {
            action = actionName
            putExtra(OrderActionReceiver.EXTRA_ORDER_ID, TEST_ORDER_ID)
            putExtra(OrderActionReceiver.EXTRA_NOTIFICATION_ID, TEST_NOTIFICATION_ID)
        }
    }
    val acceptPendingIntent = PendingIntent.getBroadcast(
        context, TEST_NOTIFICATION_ID * 10 + 1, actionIntent(OrderActionReceiver.ACTION_ACCEPT),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )
    val rejectPendingIntent = PendingIntent.getBroadcast(
        context, TEST_NOTIFICATION_ID * 10 + 2, actionIntent(OrderActionReceiver.ACTION_REJECT),
        PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
    )
    val builder = NotificationCompat.Builder(context, "new_orders_channel")
        .setContentTitle("🧪 SINOV — Yangi buyurtma!")
        .setContentText("Bu sinov xabari — bildirishnoma to'g'ri ishlayaptimi tekshirish uchun yuborildi.")
        .setSmallIcon(R.drawable.ic_launcher_foreground)
        .setContentIntent(pendingIntent)
        .setAutoCancel(true)
        .setPriority(NotificationCompat.PRIORITY_HIGH)
        .setCategory(NotificationCompat.CATEGORY_CALL)
        .addAction(0, "✅ Qabul qilish", acceptPendingIntent)
        .addAction(0, "❌ Rad etish", rejectPendingIntent)

    val canUseFullScreen = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE ||
        context.getSystemService(NotificationManager::class.java).canUseFullScreenIntent()
    if (canUseFullScreen) {
        builder.setFullScreenIntent(pendingIntent, true)
    }

    if (ActivityCompat.checkSelfPermission(context, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
        NotificationManagerCompat.from(context).notify(TEST_NOTIFICATION_ID, builder.build())
    }
}
