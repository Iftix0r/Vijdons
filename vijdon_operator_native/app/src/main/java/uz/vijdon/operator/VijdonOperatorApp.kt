package uz.vijdon.operator

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.media.AudioAttributes
import android.media.RingtoneManager
import android.os.Build
import com.google.firebase.crashlytics.FirebaseCrashlytics
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class VijdonOperatorApp : Application() {
    override fun onCreate() {
        super.onCreate()
        // google-services.json qo'shilmagan muhitda Firebase umuman ishga
        // tushmaydi (BuildConfig.HAS_FCM). Debug build'da ataylab
        // O'CHIRILGAN — aks holda dasturchi sinovi productiondagi haqiqiy
        // operatorlar bilan bir xil Crashlytics panelida aralashib ketardi.
        if (BuildConfig.HAS_FCM) {
            FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            // Yangi (dispetcherlanmagan) buyurtma / SOS — operator boshqa
            // ilova ochiq yoki ekran qulflangan bo'lsa ham darhol bilishi
            // kerak, shu sabab qo'ng'iroqdek kuchli tovush + tebranish.
            val alertChannel = NotificationChannel(
                "operator_alerts_channel", "Muhim ogohlantirishlar (buyurtma/SOS)",
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
            manager.createNotificationChannel(alertChannel)
            manager.createNotificationChannel(
                NotificationChannel(
                    "operator_info_channel", "Boshqa xabarlar (chat, to'lov so'rovi)",
                    NotificationManager.IMPORTANCE_DEFAULT,
                ),
            )
        }
    }
}
