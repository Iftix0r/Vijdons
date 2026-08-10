package uz.vijdon.driver.data.location

import kotlinx.coroutines.flow.MutableSharedFlow
import kotlinx.coroutines.flow.SharedFlow

/** `speedMps` — GPS chipi to'g'ridan-to'g'ri bergan tezlik (m/s, Doppler
 * siljishi asosida, ikkita nuqta orasidagi masofa/vaqtdan hisoblashdan
 * ancha aniqroq); qurilma tezlik bermasa (masalan qadam sanoq rejimida) 0. */
data class LocationPoint(val lat: Double, val lng: Double, val accuracy: Float, val speedMps: Float, val timestampMs: Long)

/**
 * DriverLocationService (fon xizmati) o'qigan GPS nuqtalarini ilova ichidagi
 * boshqa qismlarga (masalan taximetr) ham yetkazadi — xuddi veb ilovadagi
 * native bridge bitta GPS oqimini bir nechta iste'molchiga (dispetcherlikka
 * yuborish HAM taximetr) uzatgani kabi, bitta joylashuv obunasi yetarli.
 */
object LocationBus {
    private val _points = MutableSharedFlow<LocationPoint>(extraBufferCapacity = 4)
    val points: SharedFlow<LocationPoint> = _points

    suspend fun emit(point: LocationPoint) = _points.emit(point)
}
