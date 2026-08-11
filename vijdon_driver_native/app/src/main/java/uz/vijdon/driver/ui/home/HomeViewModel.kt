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
import uz.vijdon.driver.data.push.DriverSoundEvent
import uz.vijdon.driver.data.push.DriverSoundPlayer
import uz.vijdon.driver.data.push.OpenOrderBus
import uz.vijdon.driver.data.push.TEST_ORDER_ID
import uz.vijdon.driver.data.push.TestAlertBus
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
    val surgeMultiplier: Double? = null,
    val surgeReason: String? = null,
    val pendingOpenOrderId: Int? = null,
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
        startSurgePolling()
        collectLocationForTaximeter()
        viewModelScope.launch {
            val result = repository.rating()
            val rank = (result as? ApiResult.Success)?.data?.my_row?.rank
            _uiState.value = _uiState.value.copy(rank = rank)
        }
        // SINOV bildirishnomasi bosilganda (MainActivity → TestAlertBus) —
        // haqiqiy buyurtma kutmasdan, to'liq ekranli "Yangi buyurtma" oynasini
        // (qabul qilish/rad etish bilan) SOXTA ma'lumot bilan ko'rsatish uchun.
        viewModelScope.launch {
            TestAlertBus.events.collect {
                alertOrderId = TEST_ORDER_ID
                _uiState.value = _uiState.value.copy(alertOrder = fakeTestOrder(), alertTotalSec = 30)
            }
        }
        // Veb paneldagi kabi ovozli bildirishnomalar (operator sozlagan yoki
        // standart fayllar) — bir marta yuklab olinadi, keyin qabul
        // qilish/rad etish/yakunlash kabi hodisalarda shundan chalinadi.
        viewModelScope.launch {
            val result = repository.driverSounds()
            if (result is ApiResult.Success) DriverSoundPlayer.updateSounds(result.data)
        }
        // Bildirishnomadagi "Qabul qilish" tugmasidan keyin (MainActivity →
        // OpenOrderBus) — o'sha buyurtma tafsiloti oynasini avtomatik ochish.
        viewModelScope.launch {
            OpenOrderBus.events.collect { orderId ->
                _uiState.value = _uiState.value.copy(pendingOpenOrderId = orderId)
                refreshOrders()
            }
        }
    }

    /** `HomeScreen` buyurtma `state.orders`da paydo bo'lishi bilan sheet'ni
     * ochib, shu funksiyani chaqirib holatni tozalaydi. */
    fun clearPendingOpenOrder() {
        _uiState.value = _uiState.value.copy(pendingOpenOrderId = null)
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

    // Talab ko'p bo'lgan paytda (masalan yomg'ir, bayram) narx ko'paytmasi
    // haqida ogohlantirish — veb'dagi kabi Bosh sahifada banner sifatida
    // ko'rinadi. Tez-tez o'zgarmaydi, shu sabab manzillar (20s) kabi emas,
    // kamroq (60s) so'raladi.
    private var surgePollJob: Job? = null
    private fun startSurgePolling() {
        surgePollJob?.cancel()
        surgePollJob = viewModelScope.launch {
            while (true) {
                val result = repository.surge()
                if (result is ApiResult.Success) {
                    _uiState.value = _uiState.value.copy(
                        surgeMultiplier = result.data.multiplier.takeIf { it > 1.0 },
                        surgeReason = result.data.reason,
                    )
                }
                delay(60_000)
            }
        }
    }

    /** Masofa haydovchining joriy GPS'iga bog'liq bo'lgani uchun server
     * bermaydi (veb versiyada ham xuddi shunday — JS'da hisoblanadi),
     * shu sabab mahalliy so'nggi joylashuv asosida hisoblanadi. Eng yaqin
     * (<=1000m) manzil bo'lsa — bosh sahifada FAQAT shu (haydovchining o'zi
     * turgan joyi) va uning navbati ko'rsatiladi (boshqa barcha manzillar
     * ro'yxati endi faqat qidiruv orqali, alohida ekranda). Navbat bo'sh
     * bo'lsa ham ochiladi — "Navbatda hech kim yo'q" ko'rinsin, aks holda
     * haydovchi o'zi turgan joyi haqida umuman hech narsa ko'rmas edi. */
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
            if (nearest != null && nearestDist != null && nearestDist <= 1000.0) {
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
                    // SINOV (soxta) ogohlantirish ko'rsatilib turgan bo'lsa —
                    // bu yerda hisoblangan (serverdan kelgan haqiqiy
                    // buyurtmalar asosidagi) alertCandidate uni qayta
                    // yozib, muddatidan oldin yopib qo'ymasin.
                    val showingTestAlert = alertOrderId == TEST_ORDER_ID
                    val alertCandidate = if (showingTestAlert) {
                        _uiState.value.alertOrder
                    } else {
                        result.data.orders.firstOrNull {
                            it.isPending && it.is_dispatched && (it.timer_sec ?: 0) > 0
                        }
                    }
                    if (!showingTestAlert) {
                        if (alertCandidate != null && alertCandidate.id != alertOrderId) {
                            alertOrderId = alertCandidate.id
                            alertInitialTimerSec = alertCandidate.timer_sec ?: 30
                            DriverSoundPlayer.play(DriverSoundEvent.NEW_ORDER)
                        } else if (alertCandidate == null) {
                            alertOrderId = null
                        }
                    }
                    // Faqat "oflaynda edi, endi kamaydi" chegarasini kesib
                    // o'tganda bir marta ogohlantiradi — har 4 soniyalik
                    // pollingda qayta-qayta chalinib ketmasin deb.
                    if (result.data.low_balance && !_uiState.value.lowBalance) {
                        DriverSoundPlayer.play(DriverSoundEvent.LOW_BALANCE)
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
                    // Ilova qayta ochilganda (masalan yo'lda paytida majburan
                    // yopib qo'yilgan bo'lsa) safar allaqachon "yo'lda"/"yetib
                    // keldim" holatida bo'lishi mumkin — taximetr shu yerda
                    // ham (faqat GPS nuqtasini kutmasdan) darhol yaratiladi,
                    // aks holda vidjet birinchi GPS nuqtasigacha ko'rinmasdi.
                    result.data.orders.filter { it.isOnWay || it.isArrived }.forEach { ensureTaximeter(it.id) }
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

    fun acceptOrder(id: Int) {
        // SOXTA (sinov) buyurtma serverda mavjud emas — API'ga murojaat
        // qilmasdan, shunchaki oynani yopamiz.
        if (id == TEST_ORDER_ID) {
            alertOrderId = null
            _uiState.value = _uiState.value.copy(alertOrder = null)
            return
        }
        runAction(id, onSuccess = { DriverSoundPlayer.play(DriverSoundEvent.ACCEPT) }) { repository.acceptOrder(id) }
    }

    fun rejectOrder(id: Int) {
        if (id == TEST_ORDER_ID) {
            alertOrderId = null
            _uiState.value = _uiState.value.copy(alertOrder = null)
            return
        }
        runAction(id, onSuccess = { DriverSoundPlayer.play(DriverSoundEvent.REJECT) }) { repository.rejectOrder(id) }
    }

    fun orderOnWay(id: Int) {
        // Server javobini kutmasdan darhol yaratiladi — "Yo'lga chiqdim"
        // bosilgan zahoti taximetr vidjeti (VAQT sekundomeri) shu ondan
        // boshlab ishga tushishi kerak, tarmoq javobi kelguncha emas.
        ensureTaximeter(id)
        runAction(id) { repository.orderOnWay(id, driverLat, driverLng) }
    }

    fun orderArrived(id: Int) = runAction(id) { repository.orderArrived(id, driverLat, driverLng) }

    fun orderComplete(id: Int) {
        val tracker = taximeters[id]
        runAction(id, onSuccess = { DriverSoundPlayer.play(DriverSoundEvent.COMPLETE) }) {
            repository.orderComplete(id, tracker?.distanceKm, tracker?.priceUzs())
        }
    }

    fun toggleWaiting(id: Int) {
        taximeters[id]?.setWaiting(!(taximeters[id]?.isWaiting ?: false))
    }

    fun taximeterFor(id: Int): TaximeterTracker? = taximeters[id]

    private fun ensureTaximeter(id: Int) {
        if (taximeters.containsKey(id)) return
        val cfg = config ?: return
        taximeters[id] = TaximeterTracker(cfg.base_price, cfg.price_per_km, cfg.waiting_price_per_minute)
    }

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
                if (config == null) return@collect
                val activeOrderIds = _uiState.value.orders.filter { it.isOnWay || it.isArrived }.map { it.id }
                activeOrderIds.forEach { orderId ->
                    ensureTaximeter(orderId)
                    val tracker = taximeters[orderId] ?: return@forEach
                    if (tracker.addPoint(point.lat, point.lng, point.accuracy, point.speedMps, point.timestampMs)) {
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
            repository.updateMeter(orderId, tracker.distanceKm, tracker.priceUzs(), tracker.isWaiting, tracker.currentWaitingMs())
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
        surgePollJob?.cancel()
        super.onCleared()
    }
}

private fun fakeTestOrder() = OrderDto(
    id = TEST_ORDER_ID,
    status = "pending",
    status_label = "Kutilmoqda",
    from_address = "SINOV: Bu — haqiqiy buyurtma emas",
    to_address = "SINOV: Yo'nalish manzili",
    client_name = "Sinov mijoz",
    client_phone = "+998 90 000 00 00",
    price = "25000",
    commission = "3000",
    distance_km = 4.2,
    payment_type = "cash",
    payment_type_display = "Naqd",
    car_type = "light",
    car_type_display = "Yengil",
    note = "Bu bildirishnoma/oyna oqimini sinash uchun yaratilgan soxta buyurtma.",
    is_dispatched = true,
    timer_sec = 30,
    created_at = "",
    updated_at = "",
)
