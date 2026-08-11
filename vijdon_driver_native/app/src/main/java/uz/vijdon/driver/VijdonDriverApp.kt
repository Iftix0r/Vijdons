package uz.vijdon.driver

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import com.google.firebase.crashlytics.FirebaseCrashlytics
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class VijdonDriverApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // google-services.json qo'shilmagan muhitda (masalan boshqa
        // dasturchi mashinasida) Firebase umuman ishga tushmaydi — shu
        // sabab BuildConfig.HAS_FCM bilan tekshiriladi. Debug build'da esa
        // ataylab O'CHIRIB qo'yiladi — aks holda dasturchining o'zi
        // sinovdan o'tkazayotganda chiqqan xatoliklar ham productiondagi
        // haqiqiy haydovchilar bilan bir xil Crashlytics panelida aralashib
        // ketardi.
        if (BuildConfig.HAS_FCM) {
            FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            // Yangi buyurtma — haydovchi boshqa ilova ochiq yoki ekran
            // qulflangan bo'lsa ham darhol bilishi kerak, shu sabab
            // qo'ng'iroqdek kuchli tovush + tebranish beriladi (oddiy
            // bildirishnoma tovushidan farqli, ovoz balandligi tizim
            // "Ringtone" darajasida ishlaydi).
            val newOrderChannel = NotificationChannel(
                "new_orders_channel", "Yangi buyurtmalar",
                NotificationManager.IMPORTANCE_HIGH,
            ).apply {
                enableVibration(true)
                vibrationPattern = longArrayOf(0, 500, 250, 500, 250, 500)
                setSound(
                    RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE),
                    AudioAttributes.Builder()
                        .setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE)
                        .setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION)
                        .build(),
                )
            }
            manager.createNotificationChannel(newOrderChannel)
            manager.createNotificationChannel(
                NotificationChannel(
                    "duty_channel", "Onlayn holat",
                    NotificationManager.IMPORTANCE_LOW,
                ),
            )
        }
    }
}
