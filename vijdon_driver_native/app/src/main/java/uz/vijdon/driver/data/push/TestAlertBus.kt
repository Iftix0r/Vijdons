package uz.vijdon.driver.data.push

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * SINOV bildirishnomasi bosilganda (`MainActivity`) shuni signal qiladi —
 * `HomeViewModel` shu hodisani tinglab, to'liq ekranli "Yangi buyurtma"
 * oynasini (qabul qilish/rad etish tugmalari bilan) SOXTA buyurtma
 * ma'lumotlari bilan ko'rsatadi. Shu orqali haydovchi/dasturchi haqiqiy
 * buyurtma kutmasdan, butun oqimni (bildirishnoma → to'liq ekran →
 * tugmalar) boshidan-oxirigacha sinab ko'ra oladi — `LocationBus` bilan
 * bir xil g'oyadagi Activity → ViewModel signal ko'prigi.
 */
object TestAlertBus {
    private val _events = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val events: SharedFlow<Unit> = _events

    suspend fun trigger() = _events.emit(Unit)
}
