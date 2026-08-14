package uz.vijdon.smsgateway.data.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.os.Build
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.data.repository.TokenStore
import javax.inject.Inject

/**
 * Bu ilova ATAYLAB doim-onlayn, alohida telefonda (asosan SIM karta
 * ushlab turish uchun) ishlaydi — qurilma qayta ishga tushsa (elektr
 * uzilishi va h.k.), avval kirilgan bo'lsa, fon xizmati o'zi qayta
 * ishga tushishi kerak (operator har safar qo'lda ochib qo'yishi shart
 * bo'lmasin).
 */
@AndroidEntryPoint
class BootReceiver : BroadcastReceiver() {

    @Inject lateinit var tokenStore: TokenStore

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Intent.ACTION_BOOT_COMPLETED) return
        val pending = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                if (!tokenStore.currentToken().isNullOrBlank()) {
                    val serviceIntent = Intent(context, SmsGatewayService::class.java)
                    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                        context.startForegroundService(serviceIntent)
                    } else {
                        context.startService(serviceIntent)
                    }
                }
            } finally {
                pending.finish()
            }
        }
    }
}
