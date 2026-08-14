package uz.vijdon.operator.data.push

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/** Push-bildirishnoma bosilganda ilova qaysi bo'limni (tab) ochishi
 * kerakligini `MainActivity`dan `ApprovedScaffold`ga uzatish uchun
 * (driverapp'dagi `OpenOrderBus` bilan bir xil Activity → Compose ko'prik
 * g'oyasi) — MVP bosqichida aniq buyurtma/chatga emas, shunchaki tegishli
 * bo'limga ochadi. */
object OpenTabBus {
    private val _events = MutableSharedFlow<String>(extraBufferCapacity = 1)
    val events: SharedFlow<String> = _events

    suspend fun trigger(tab: String) = _events.emit(tab)
}
