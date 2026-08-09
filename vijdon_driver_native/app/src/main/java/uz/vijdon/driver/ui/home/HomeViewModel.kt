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
import uz.vijdon.driver.data.api.ConfigDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.location.DriverLocationService
import uz.vijdon.driver.data.location.LocationBus
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import uz.vijdon.driver.ui.orders.TaximeterTracker
import javax.inject.Inject

data class HomeUiState(
    val driver: DriverDto? = null,
    val orders: List<OrderDto> = emptyList(),
    val lowBalance: Boolean = false,
    val error: String? = null,
    val actionInProgress: Set<Int> = emptySet(),
    val operatorPhone: String = "1351",
    val rank: Int? = null,
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

    init {
        viewModelScope.launch {
            val result = repository.config()
            config = (result as? ApiResult.Success)?.data
            config?.let { _uiState.value = _uiState.value.copy(operatorPhone = it.operator_phone) }
        }
        startPolling()
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

    fun refreshOrders() {
        viewModelScope.launch {
            when (val result = repository.availableOrders()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        orders = result.data.orders,
                        lowBalance = result.data.low_balance,
                        error = null,
                    )
                    pruneFinishedTaximeters(result.data.orders)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
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

    private fun runAction(orderId: Int, block: suspend () -> ApiResult<*>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = _uiState.value.actionInProgress + orderId)
            when (val result = block()) {
                is ApiResult.Success -> refreshOrders()
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
            _uiState.value = _uiState.value.copy(actionInProgress = _uiState.value.actionInProgress - orderId)
        }
    }

    private fun collectLocationForTaximeter() {
        viewModelScope.launch {
            LocationBus.points.collect { point ->
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
        super.onCleared()
    }
}
