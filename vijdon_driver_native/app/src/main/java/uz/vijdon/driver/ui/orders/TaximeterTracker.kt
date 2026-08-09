package uz.vijdon.driver.ui.orders

import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

/**
 * Haydovchi ilovasidagi web taximetr (taxi/templates/driver/base.html) bilan
 * bir xil filtr qoidalarini takrorlaydi: aniqlik/shovqin/tez sakrash
 * filtrlari — bularsiz GPS shovqini masofani soxta oshirib yuboradi.
 * Server har doim faqat "kamaymaydigan" (never-decrease) qiymatlarni qabul
 * qiladi, shu sabab bu klass ham faqat oshib boruvchi kumulyativ masofani
 * hisoblaydi.
 */
class TaximeterTracker(
    private val basePrice: Double,
    private val pricePerKm: Double,
    private val waitingPricePerMinute: Double,
) {
    companion object {
        private const val MAX_ACCURACY_M = 60.0
        private const val MIN_INTERVAL_MS = 4_000L
        private const val MIN_NOISE_FLOOR_M = 15.0
        private const val MAX_PLAUSIBLE_SPEED_KMH = 140.0
    }

    var distanceKm: Double = 0.0
        private set
    var waitingMs: Long = 0L
        private set
    var isWaiting: Boolean = false

    private var lastLat: Double? = null
    private var lastLng: Double? = null
    private var lastAccuracy: Float = 0f
    private var lastTimestampMs: Long = 0L
    private var waitingStartedAtMs: Long? = null

    val priceUzs: Double
        get() = basePrice + distanceKm * pricePerKm + (waitingMs / 60_000.0) * waitingPricePerMinute

    fun setWaiting(waiting: Boolean, nowMs: Long = System.currentTimeMillis()) {
        if (waiting == isWaiting) return
        if (waiting) {
            waitingStartedAtMs = nowMs
        } else {
            waitingStartedAtMs?.let { waitingMs += nowMs - it }
            waitingStartedAtMs = null
        }
        isWaiting = waiting
    }

    /** Yangi GPS nuqtasini qabul qiladi; nuqta rad etilsa false qaytaradi. */
    fun addPoint(lat: Double, lng: Double, accuracy: Float, timestampMs: Long = System.currentTimeMillis()): Boolean {
        if (accuracy > MAX_ACCURACY_M) return false
        if (timestampMs - lastTimestampMs < MIN_INTERVAL_MS && lastTimestampMs != 0L) return false

        val prevLat = lastLat
        val prevLng = lastLng
        val prevAccuracy = lastAccuracy
        val prevTimestamp = lastTimestampMs

        lastLat = lat; lastLng = lng; lastAccuracy = accuracy; lastTimestampMs = timestampMs

        if (prevLat == null || prevLng == null) return true // birinchi nuqta — hisoblanadigan asos yo'q

        val distMeters = haversineMeters(prevLat, prevLng, lat, lng)
        val noiseFloor = maxOf(MIN_NOISE_FLOOR_M, (prevAccuracy + accuracy) / 2.0)
        if (distMeters < noiseFloor) return true // harakatsizlik/shovqin — masofaga qo'shilmaydi

        val elapsedHours = (timestampMs - prevTimestamp) / 3_600_000.0
        if (elapsedHours > 0) {
            val impliedSpeedKmh = (distMeters / 1000.0) / elapsedHours
            if (impliedSpeedKmh > MAX_PLAUSIBLE_SPEED_KMH) return false // GPS sakrashi
        }

        if (!isWaiting) {
            distanceKm += distMeters / 1000.0
        }
        return true
    }

    private fun haversineMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2) * sin(dLng / 2)
        val c = 2 * atan2(sqrt(a), sqrt(1 - a))
        return r * c
    }
}
