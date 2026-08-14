package uz.vijdon.smsgateway.data.service

import com.google.firebase.messaging.FirebaseMessagingService
import com.google.firebase.messaging.RemoteMessage
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import javax.inject.Inject

/**
 * `taxi/utils.py: notify_sms_gateway()`dan kelgan `type: new_sms` pushi —
 * navbatni DARHOL (fon xizmatining 20s'lik navbatdagi tekshiruvini
 * kutmasdan) tekshirib, topilgan SMS'larni yuboradi. FCM ulanmagan/
 * yetib bormagan holatda ham `SmsGatewayService`ning muntazam polling'i
 * baribir bir necha soniya ichida xuddi shu ishni bajaraveradi — shu
 * sabab bu servis SOF TEZLASHTIRISH, yagona kanal emas.
 */
@AndroidEntryPoint
class SmsFirebaseMessagingService : FirebaseMessagingService() {

    @Inject lateinit var repository: SmsGatewayRepository

    override fun onNewToken(token: String) {
        super.onNewToken(token)
        CoroutineScope(Dispatchers.IO).launch { repository.syncFcmToken(token) }
    }

    override fun onMessageReceived(message: RemoteMessage) {
        super.onMessageReceived(message)
        if (message.data["type"] != "new_sms") return
        CoroutineScope(Dispatchers.IO).launch {
            SmsSender.processPendingBatch(applicationContext, repository)
        }
    }
}
