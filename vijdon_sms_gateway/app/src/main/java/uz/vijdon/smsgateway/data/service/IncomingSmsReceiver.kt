package uz.vijdon.smsgateway.data.service

import android.content.BroadcastReceiver
import android.content.Context
import android.content.Intent
import android.provider.Telephony
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import java.time.Instant
import javax.inject.Inject

/**
 * SIM kartaga kelgan SMS'larni (mijoz/haydovchi javob yozsa) serverga
 * bildiradi — Eskiz/alfa-nomdan farqli, real SIM raqamiga javob yozish
 * mumkin, operator buni panelda (`/system/sms/`) ko'rishi uchun.
 */
@AndroidEntryPoint
class IncomingSmsReceiver : BroadcastReceiver() {

    @Inject lateinit var repository: SmsGatewayRepository

    override fun onReceive(context: Context, intent: Intent) {
        if (intent.action != Telephony.Sms.Intents.SMS_RECEIVED_ACTION) return
        val messages = Telephony.Sms.Intents.getMessagesFromIntent(intent)
        if (messages.isNullOrEmpty()) return

        // Ko'p qismli (uzun) SMS bir nechta PDU sifatida kelishi mumkin —
        // hammasini bitta matn qilib birlashtiramiz; jo'natuvchi manzil
        // birinchi qismdan olinadi (barcha qismlar bir xil jo'natuvchidan).
        val sender = messages.first().originatingAddress ?: return
        val body = messages.joinToString(separator = "") { it.messageBody ?: "" }
        if (body.isBlank()) return
        val receivedAt = Instant.now().toString()

        val pending = goAsync()
        CoroutineScope(Dispatchers.IO).launch {
            try {
                repository.reportIncoming(sender, body, receivedAt)
            } finally {
                pending.finish()
            }
        }
    }
}
