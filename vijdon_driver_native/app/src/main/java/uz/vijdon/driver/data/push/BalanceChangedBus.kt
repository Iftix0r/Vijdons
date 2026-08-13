package uz.vijdon.driver.data.push

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/**
 * Balans o'zgarganda (admin qo'shdi/ayirdi yoki to'lov cheki tasdiqlandi —
 * `taxi/views.py`: `driver_recharge`/`topup_resolve`) server FCM orqali
 * `data.type = "balance_changed"` push yuboradi. `VijdonFirebaseMessagingService`
 * buni ushlab, shu bus orqali (ilova FONDA yoki OLDINDA ochiq bo'lsa, tugmani
 * bosishni kutmasdan) `HomeViewModel`/`ProfileViewModel`ga signal beradi —
 * ular esa darhol serverdan yangi balansni qayta so'raydi. `OpenOrderBus`/
 * `TestAlertBus` bilan bir xil Service/Activity → ViewModel ko'prik g'oyasi.
 */
object BalanceChangedBus {
    private val _events = MutableSharedFlow<Unit>(extraBufferCapacity = 1)
    val events: SharedFlow<Unit> = _events

    suspend fun trigger() = _events.emit(Unit)
}
