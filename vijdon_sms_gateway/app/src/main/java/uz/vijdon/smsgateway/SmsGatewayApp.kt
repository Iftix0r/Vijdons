package uz.vijdon.smsgateway

import android.app.Application
import android.app.NotificationChannel
import android.app.NotificationManager
import android.os.Build
import com.google.firebase.crashlytics.FirebaseCrashlytics
import dagger.hilt.android.HiltAndroidApp

@HiltAndroidApp
class SmsGatewayApp : Application() {
    override fun onCreate() {
        super.onCreate()
        if (BuildConfig.HAS_FCM) {
            FirebaseCrashlytics.getInstance().setCrashlyticsCollectionEnabled(!BuildConfig.DEBUG)
        }
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
            val manager = getSystemService(NotificationManager::class.java)
            manager.createNotificationChannel(
                NotificationChannel(
                    "sms_gateway_channel", "SMS-shlyuz xizmati",
                    NotificationManager.IMPORTANCE_LOW,
                ),
            )
        }
    }
}
