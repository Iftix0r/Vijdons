package uz.vijdon.smsgateway.data.service

import android.Manifest
import android.content.Context
import android.content.pm.PackageManager
import android.telephony.SmsManager
import androidx.core.content.ContextCompat
import kotlinx.coroutines.delay
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import uz.vijdon.smsgateway.data.api.PendingSmsDto
import uz.vijdon.smsgateway.data.repository.ApiResult
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository

/**
 * Navbatdagi SMS'larni haqiqiy jo'natadigan yagona joy — ham fon xizmati
 * (`SmsGatewayService`, muntazam polling), ham push kelganda (`SmsFirebaseMessagingService`)
 * shu funksiyani chaqiradi. Ikkalasi bir vaqtda ishga tushib qolsa ham
 * (masalan push aynan poll bilan bir onda kelsa), `mutex` ular ketma-ket,
 * bir xil sekinlik bilan yuborishini kafolatlaydi — mobil operatorga
 * "portlash" (bir zumda o'nlab SMS) ko'rinishida emas, tabiiyroq oqim
 * sifatida ko'rinishi uchun (spam-aniqlashdan qochish).
 *
 * Diqqat: navbatning O'ZI serverda (`taxi/smsgatewayapp_views.py: pending()`)
 * "band qilib olish" (claim) bilan himoyalangan — shu sabab bir nechta
 * SMS-shlyuz QURILMASI (turli telefonlar) bir xil xabarni ikki marta
 * yubormaydi, bu yerdagi mutex esa faqat BITTA qurilma ICHIDA (FCM va
 * poll orasida) tartib saqlaydi.
 */
object SmsSender {
    private val mutex = Mutex()

    // Ketma-ket yuborishlar orasidagi tanaffus — mobil operatorlar
    // odatda ANIQ shu naqshni ("bir zumda ko'plab SMS, bir xil qurilmadan")
    // avtomatik/spam deb belgilaydi. Batafsil: SmsSettings.provider
    // izohiga qarang (taxi/models.py).
    private const val SEND_THROTTLE_MS = 4_000L

    /** @return true bo'lsa — token yaroqsiz (401), chaqiruvchi (Service)
     * foydalanuvchini avtomatik chiqarib, qayta kirishni so'rashi kerak. */
    suspend fun processPendingBatch(context: Context, repository: SmsGatewayRepository): Boolean {
        mutex.withLock {
            val result = repository.pending()
            if (result is ApiResult.Error && result.httpCode == 401) return true
            val messages = (result as? ApiResult.Success)?.data ?: return false
            for (message in messages) {
                sendOne(context, repository, message)
                if (message != messages.last()) delay(SEND_THROTTLE_MS)
            }
        }
        return false
    }

    private suspend fun sendOne(context: Context, repository: SmsGatewayRepository, message: PendingSmsDto) {
        if (ContextCompat.checkSelfPermission(context, Manifest.permission.SEND_SMS) != PackageManager.PERMISSION_GRANTED) {
            repository.reportFailed(message.id, "SEND_SMS ruxsati berilmagan")
            SentLogBus.log(message.phone_number, success = false, error = "Ruxsat yo'q")
            return
        }
        try {
            val smsManager = SmsManager.getDefault()
            val parts = smsManager.divideMessage(message.text)
            if (parts.size > 1) {
                smsManager.sendMultipartTextMessage(message.phone_number, null, parts, null, null)
            } else {
                smsManager.sendTextMessage(message.phone_number, null, message.text, null, null)
            }
            repository.reportSent(message.id)
            SentLogBus.log(message.phone_number, success = true)
        } catch (e: Exception) {
            repository.reportFailed(message.id, e.message ?: "Noma'lum xato")
            SentLogBus.log(message.phone_number, success = false, error = e.message)
        }
    }
}
