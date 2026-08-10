package uz.vijdon.driver.ui.home

import android.content.Context
import android.content.Intent
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.ConfigDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.data.location.DriverLocationService
import uz.vijdon.driver.data.location.LocationBus
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import uz.vijdon.driver.ui.orders.TaximeterTracker
import javax.inject.Inject
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class HomeUiState(
    val driver: DriverDto? = null,
    val orders: List<OrderDto> = emptyList(),
    val lowBalance: Boolean = false,
    val error: String? = null,
    val loading: Boolean = true,
    val actionInProgress: Set<Int> = emptySet(),
    val operatorPhone: String = "1351",
    val rank: Int? = null,
    val alertOrder: OrderDto? = null,
    val alertTotalSec: Int = 30,
    val addresses: List<AddressDto> = emptyList(),
    val addressDistancesM: Map<Int, Double> = emptyMap(),
    val expandedAddressId: Int? = null,
    val queuePosition: Int? = null,
    val queueDrivers: List<QueueDriverDto> = emptyList(),
    val queueLoading: Boolean = false,
    val orderDistancesM: Map<Int, Double> = emptyMap(),
)

@HiltViewModel
class HomeViewModel @Inject constructor(
    private val repository: DriverRepository,
    @ApplicationContext private val context: Context,
) : ViewModel() {

    private val _uiState = MutableStateFlow(HomeUiState())
    val uiState: StateFlow<HomeUiState> = _uiState.asStateFlow()

    private var config: ConfigDto? = null
    private var pollJob: Job? = null
    private val taximeters = mutableMapOf<Int, TaximeterTracker>()
    private var driverLat: Double? = null
    private var driverLng: Double? = null
    private var autoExpandedOnce = false

    // Yandex Pro uslubidagi to'liq ekranli "yangi buyurtma" ogohlantirishi
    // uchun — faqat shu haydovchiga shaxsan yo'naltirilgan (is_dispatched)
    // va hali javob berish muddati (timer_sec) tugamagan buyurtmada ko'rinadi.
    private var alertOrderId: Int? = null
    private var alertInitialTimerSec: Int = 30

    init {
        viewModelScope.launch {
            val result = repository.config()
            config = (result as? ApiResult.Success)?.data
            config?.let { _uiState.value = _uiState.value.copy(operatorPhone = it.operator_phone) }
        }
        startPolling()
        startAddressPolling()
        collectLocationForTaximeter()
        viewModelScope.launch {
            val result = repository.rating()
            val rank = (result as? ApiResult.Success)?.data?.my_row?.rank
            _uiState.value = _uiState.value.copy(rank = rank)
        }
    }

    fun setDriver(driver: DriverDto) {
        _uiState.value = _uiState.value.copy(driver = driver)
        syncLocationService(driver.is_on_duty)
    }

    /** Ruxsat ekrandan so'ralganda KEYINROQ berilsa (masalan haydovchi
     * ilovani birinchi ochganda allaqachon "onlayn" bo'lsa) — fon xizmatini
     * shu paytda qayta boshlashga urinadi. */
    fun onLocationPermissionGranted() {
        _uiState.value.driver?.let { syncLocationService(it.is_on_duty) }
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                refreshOrders()
                delay(4_000)
            }
        }
    }

    // Veb haydovchi panelida "Asosiy" sahifaning fon kontenti aynan shu
    // ro'yxat (xarita hozircha o'chirilgan) — navbatdagi haydovchilar va
    // bugungi buyurtmalar soni haydovchiga talab qayerda ekanini ko'rsatadi,
    // shu sabab bu native Home ekraniga ham qo'shildi (ilgari faqat Profil >
    // "Yaqin manzillar" bo'limida ko'rinardi). Veb bilan bir xil kadensiya — 20s.
    private var addressPollJob: Job? = null
    private fun startAddressPolling() {
        addressPollJob?.cancel()
        addressPollJob = viewModelScope.launch {
            while (true) {
                val result = repository.addresses()
                if (result is ApiResult.Success) {
                    _uiState.value = _uiState.value.copy(addresses = result.data)
                    recomputeAddressDistances()
                }
                delay(20_000)
            }
        }
    }

    /** Masofa haydovchining joriy GPS'iga bog'liq bo'lgani uchun server
     * bermaydi (veb versiyada ham xuddi shunday — JS'da hisoblanadi),
     * shu sabab mahalliy so'nggi joylashuv asosida hisoblanadi. Eng yaqin
     * (<=1000m) manzil bo'lsa va navbatda odam bo'lsa, veb'dagi kabi
     * avtomatik ochiladi — haydovchi darhol kim navbatda ekanini ko'rsin. */
    private fun recomputeAddressDistances() {
        val lat = driverLat
        val lng = driverLng
        val addresses = _uiState.value.addresses
        if (lat == null || lng == null || addresses.isEmpty()) return
        val distances = addresses.associate { it.id to haversineMeters(lat, lng, it.lat, it.lng) }
        _uiState.value = _uiState.value.copy(addressDistancesM = distances)

        if (!autoExpandedOnce) {
            val nearest = addresses.minByOrNull { distances[it.id] ?: Double.MAX_VALUE }
            val nearestDist = nearest?.let { distances[it.id] }
            if (nearest != null && nearestDist != null && nearestDist <= 1000.0 && nearest.queue_count > 0) {
                autoExpandedOnce = true
                toggleAddressExpand(nearest, forceExpand = true)
            }
        }
    }

    fun toggleAddressExpand(address: AddressDto, forceExpand: Boolean = false) {
        val current = _uiState.value
        if (!forceExpand && current.expandedAddressId == address.id) {
            _uiState.value = current.copy(expandedAddressId = null, queuePosition = null, queueDrivers = emptyList())
            return
        }
        _uiState.value = current.copy(expandedAddressId = address.id, queueLoading = true)
        viewModelScope.launch {
            val posResult = repository.addressQueuePosition(address.id, driverLat, driverLng)
            val driversResult = repository.addressQueueDrivers(address.id)
            if (_uiState.value.expandedAddressId != address.id) return@launch
            _uiState.value = _uiState.value.copy(
                queuePosition = (posResult as? ApiResult.Success)?.data?.position,
                queueDrivers = (driversResult as? ApiResult.Success)?.data ?: emptyList(),
                queueLoading = false,
            )
        }
    }

    /** Yandex Pro'dagi "Offer Screen"dagi kabi — mijozgacha bo'lgan masofa
     * server bermaydi (manzillar bilan bir xil sabab: haydovchining joriy
     * GPS'iga bog'liq), shu sabab mahalliy hisoblanadi. Faqat hali
     * mijozning oldiga yetib borilmagan holatlarda (pending/accepted)
     * ma'noli — yo'lda/yetib kelgan holatda taximetr o'zi ishlaydi. */
    private fun recomputeOrderDistances() {
        val lat = driverLat ?: return
        val lng = driverLng ?: return
        val distances = _uiState.value.orders.mapNotNull { order ->
            val flat = order.from_lat
            val flng = order.from_lng
            if (flat != null && flng != null && (order.isPending || order.isAccepted)) {
                order.id to haversineMeters(lat, lng, flat, flng)
            } else {
                null
            }
        }.toMap()
        _uiState.value = _uiState.value.copy(orderDistancesM = distances)
    }

    private fun haversineMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2) * sin(dLng / 2)
        return r * 2 * atan2(sqrt(a), sqrt(1 - a))
    }

    fun refreshOrders() {
        viewModelScope.launch {
            when (val result = repository.availableOrders()) {
                is ApiResult.Success -> {
                    val alertCandidate = result.data.orders.firstOrNull {
                        it.isPending && it.is_dispatched && (it.timer_sec ?: 0) > 0
                    }
                    if (alertCandidate != null && alertCandidate.id != alertOrderId) {
                        alertOrderId = alertCandidate.id
                        alertInitialTimerSec = alertCandidate.timer_sec ?: 30
                    } else if (alertCandidate == null) {
                        alertOrderId = null
                    }
                    _uiState.value = _uiState.value.copy(
                        orders = result.data.orders,
                        lowBalance = result.data.low_balance,
                        error = null,
                        loading = false,
                        alertOrder = alertCandidate,
                        alertTotalSec = alertInitialTimerSec,
                    )
                    recomputeOrderDistances()
                    pruneFinishedTaximeters(result.data.orders)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message, loading = false)
            }
        }
    }

    fun toggleDuty() {
        viewModelScope.launch {
            when (val result = repository.toggleDuty()) {
                is ApiResult.Success -> {
                    val driver = _uiState.value.driver?.copy(is_on_duty = result.data.is_on_duty)
                    _uiState.value = _uiState.value.copy(driver = driver)
                    syncLocationService(result.data.is_on_duty)
                    refreshOrders()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }

    fun acceptOrder(id: Int) = runAction(id) { repository.acceptOrder(id) }
    fun rejectOrder(id: Int) = runAction(id) { repository.rejectOrder(id) }
    fun orderOnWay(id: Int) = runAction(id) { repository.orderOnWay(id) }
    fun orderArrived(id: Int) = runAction(id) { repository.orderArrived(id) }

    fun orderComplete(id: Int) {
        val tracker = taximeters[id]
        runAction(id) { repository.orderComplete(id, tracker?.distanceKm, tracker?.priceUzs) }
    }

    fun toggleWaiting(id: Int) {
        taximeters[id]?.setWaiting(!(taximeters[id]?.isWaiting ?: false))
    }

    fun taximeterFor(id: Int): TaximeterTracker? = taximeters[id]

    private fun runAction(orderId: Int, onSuccess: () -> Unit = {}, block: suspend () -> ApiResult<*>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = _uiState.value.actionInProgress + orderId)
            when (val result = block()) {
                is ApiResult.Success -> {
                    refreshOrders()
                    onSuccess()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
            _uiState.value = _uiState.value.copy(actionInProgress = _uiState.value.actionInProgress - orderId)
        }
    }

    private fun collectLocationForTaximeter() {
        viewModelScope.launch {
            LocationBus.points.collect { point ->
                driverLat = point.lat
                driverLng = point.lng
                recomputeAddressDistances()
                recomputeOrderDistances()
                val cfg = config ?: return@collect
                val activeOrderIds = _uiState.value.orders.filter { it.isOnWay || it.isArrived }.map { it.id }
                activeOrderIds.forEach { orderId ->
                    val tracker = taximeters.getOrPut(orderId) {
                        TaximeterTracker(cfg.base_price, cfg.price_per_km, cfg.waiting_price_per_minute)
                    }
                    if (tracker.addPoint(point.lat, point.lng, point.accuracy, point.timestampMs)) {
                        flushMeter(orderId, tracker)
                    }
                }
            }
        }
    }

    private var lastFlushAtMs = mutableMapOf<Int, Long>()
    private fun flushMeter(orderId: Int, tracker: TaximeterTracker) {
        val now = System.currentTimeMillis()
        val last = lastFlushAtMs[orderId] ?: 0L
        if (now - last < 5_000) return
        lastFlushAtMs[orderId] = now
        viewModelScope.launch {
            repository.updateMeter(orderId, tracker.distanceKm, tracker.priceUzs, tracker.isWaiting, tracker.waitingMs)
        }
    }

    private fun pruneFinishedTaximeters(orders: List<OrderDto>) {
        val activeIds = orders.filter { it.isActive }.map { it.id }.toSet()
        taximeters.keys.retainAll(activeIds)
    }

    private fun syncLocationService(onDuty: Boolean) {
        val intent = Intent(context, DriverLocationService::class.java)
        if (onDuty) {
            // Android 14+ da joylashuv ruxsati bo'lmasa foreground service
            // boshlash SecurityException bilan qulaydi — ruxsat hali
            // so'ralayotgan yoki rad etilgan bo'lishi mumkin (masalan
            // haydovchi avvaldan "onlaynligicha" ilovani birinchi marta
            // ochsa), shu sabab avval tekshiramiz.
            val granted = androidx.core.content.ContextCompat.checkSelfPermission(
                context, android.Manifest.permission.ACCESS_FINE_LOCATION,
            ) == android.content.pm.PackageManager.PERMISSION_GRANTED
            if (granted) {
                context.startForegroundService(intent)
            }
        } else {
            context.stopService(intent)
        }
    }

    override fun onCleared() {
        pollJob?.cancel()
        addressPollJob?.cancel()
        super.onCleared()
    }
}
