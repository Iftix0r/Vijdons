package uz.vijdon.smsgateway.data.service

import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow

data class SentLogEntry(
    val phoneNumber: String,
    val success: Boolean,
    val error: String? = null,
    val atMillis: Long,
)

/** Yuborilgan SMS'lar tarixi — StatusScreen'da "so'nggi harakatlar"
 * ro'yxatini ko'rsatish uchun. Server bilan bog'liq emas, faqat shu
 * qurilmaning jonli holatini aks ettiradi (ilova qayta ishga tushsa
 * tozalanadi — buning uchun serverdagi `taxi/views.py: sms_settings`
 * panelidagi "So'nggi xabarlar" doimiy jurnal sifatida xizmat qiladi). */
object SentLogBus {
    private const val MAX_ENTRIES = 50
    private val _entries = MutableStateFlow<List<SentLogEntry>>(emptyList())
    val entries: StateFlow<List<SentLogEntry>> = _entries

    fun log(phoneNumber: String, success: Boolean, error: String? = null) {
        _entries.value = (listOf(SentLogEntry(phoneNumber, success, error, System.currentTimeMillis())) + _entries.value)
            .take(MAX_ENTRIES)
    }
}
