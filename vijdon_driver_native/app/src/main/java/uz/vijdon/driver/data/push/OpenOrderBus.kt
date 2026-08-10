package uz.vijdon.driver.data.push

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * Bildirishnomadagi "Qabul qilish" tugmasi bosilib, buyurtma muvaffaqiyatli
 * qabul qilingandan keyin (`OrderActionWorker`) — ilova ochilib, to'g'ridan-
 * to'g'ri o'sha buyurtma tafsiloti oynasi ko'rinishi uchun `MainActivity`
 * shu orqali `HomeViewModel`ga signal beradi (`TestAlertBus`/`LocationBus`
 * bilan bir xil Activity → ViewModel ko'prik g'oyasi).
 */
object OpenOrderBus {
    private val _events = MutableSharedFlow<Int>(extraBufferCapacity = 1)
    val events: SharedFlow<Int> = _events

    suspend fun trigger(orderId: Int) = _events.emit(orderId)
}
