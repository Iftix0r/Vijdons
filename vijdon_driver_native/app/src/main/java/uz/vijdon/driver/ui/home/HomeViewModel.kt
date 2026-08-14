package uz.vijdon.driver.ui.home

import android.content.Context
import android.content.Intent
import android.net.Uri
import androidx.core.app.NotificationManagerCompat
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Job
import kotlinx.coroutines.async
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
import uz.vijdon.driver.data.push.BalanceChangedBus
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
        startDutySyncPolling()
        startQueuePolling()
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
        // Balans o'zgarganda (admin to'ldirdi/ayirdi) server FCM push yuboradi
        // (`VijdonFirebaseMessagingService` → `BalanceChangedBus`) — shu orqali
        // ilova ochib-yopilishini kutmasdan, darhol yangi balansni so'raymiz.
        viewModelScope.launch {
            BalanceChangedBus.events.collect { refreshBalance() }
        }
    }

    /** `BalanceChangedBus` signali kelganda chaqiriladi — faqat `balance`
     * (va boshqa server-hisoblaydigan maydonlar: reyting, safarlar soni)
     * yangilanadi, `is_on_duty` esa (`setDriver()`dagi kabi) mahalliy
     * holatdan saqlanib qoladi — aks holda `SessionViewModel`dan kelgan
     * eskirgan qiymat bilan bosib yozilib, avval tuzatilgan xato qaytadi.
     * Diqqat: `repository.me()` javob berguncha (sekin tarmoq) haydovchi
     * onlayn/oflaynni almashtirib ulgurishi mumkin — shu sabab eskirganlik
     * tekshiruvi BUTUN `driver` obyektini emas, faqat shu davrda haqiqatan
     * ahamiyatli narsani (haydovchi hali ham mavjudmi) tekshiradi, va
     * `is_on_duty` ENG SO'NGGI holatdan (await'dan OLDIN emas, KEYIN)
     * olinadi — aks holda shu oraliqda bo'lgan onlayn/oflayn o'zgarishi
     * yangi balans bilan birga bekorga tashlab yuborilardi. */
    // Diqqat: bir nechta balans o'zgarishi (masalan admin ketma-ket ikki
    // marta to'ldirsa) yaqin vaqt ichida ikkita mustaqil push yuborishi
    // mumkin — FCM va tarmoq TARTIBNI kafolatlamaydi, shu sabab ESKI
    // so'rovning javobi YANGISIDAN keyin kelib qolsa, eskirgan balans
    // bilan bosib yozib qo'yishi mumkin edi. Faqat ENG SO'NGGI chaqiruv
    // natijasi qo'llanishi uchun oldingisi bekor qilinadi.
    private var balanceRefreshJob: Job? = null

    private fun refreshBalance() {
        balanceRefreshJob?.cancel()
        balanceRefreshJob = viewModelScope.launch {
            if (_uiState.value.driver == null) return@launch
            val result = repository.me()
            val latest = _uiState.value.driver
            if (result is ApiResult.Success && latest != null) {
                _uiState.value = _uiState.value.copy(driver = result.data.copy(is_on_duty = latest.is_on_duty))
            }
        }
    }

    /** `HomeScreen` buyurtma `state.orders`da paydo bo'lishi bilan sheet'ni
     * ochib, shu funksiyani chaqirib holatni tozalaydi. */
    fun clearPendingOpenOrder() {
        _uiState.value = _uiState.value.copy(pendingOpenOrderId = null)
    }

    /** `HomeScreen` `HorizontalPager` ichida bo'lgani uchun sahifadan
     * sahifaga o'tganda Compose uning KOMPOZITSIYASINI (o'zi emas — bu
     * ViewModel `Tabs.HOME` marshrutiga bog'langani uchun butun sessiya
     * davomida bitta nusxada qoladi) tashlab qayta yaratadi — shu payt
     * `HomeScreen`dagi `LaunchedEffect(driver) { setDriver(driver) }` qayta
     * ishga tushib, bu funksiya har safar `SessionViewModel`dan kelgan
     * (faqat login/refresh paytida yangilanadigan) `driver` bilan qayta
     * chaqiriladi. `toggleDuty()` esa `is_on_duty`ni FAQAT shu ViewModel
     * ichida yangilaydi, `SessionViewModel`ga xabar bermaydi — shu sabab
     * o'sha eskirgan (masalan hali "oflayn") qiymat bilan blindly
     * almashtirilsa, onlayn bosilgandan keyin sahifa almashtirilganda
     * haydovchi yana "oflayn" bo'lib qolardi. Shu sabab `is_on_duty` faqat
     * shu ViewModel'ning o'zidan (mahalliy, eng so'nggi) olinadi — boshqa
     * maydonlar (balans, ism va h.k.) esa yangilanishda davom etadi.
     * (`startDutySyncPolling()` — server o'zi navbatdan chiqarib qo'ygan
     * holatni ushlab olish uchun, chunki bu mexanizm sabab mahalliy
     * qiymat SessionViewModel'dan hech qachon "tuzatilmaydi".) */
    fun setDriver(driver: DriverDto) {
        val existing = _uiState.value.driver
        val merged = if (existing != null && existing.id == driver.id) {
            driver.copy(is_on_duty = existing.is_on_duty)
        } else {
            driver
        }
        _uiState.value = _uiState.value.copy(driver = merged)
        syncLocationService(merged.is_on_duty)
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

    // Diqqat: avval "Joriy navbatingiz" karta ochilganda navbatdagi
    // haydovchilar ro'yxati FAQAT bir marta so'ralar edi
    // (`toggleAddressExpand()`) — shu manzilda boshqa haydovchi navbatga
    // qo'shilsa/chiqsa, karta ochiq turgan bo'lsa ham ro'yxat
    // YANGILANMASDI (haydovchi o'zining navbatdagi o'rnini — ro'yxatdagi
    // qatoridan, `DarkQueueRow`/`is_me` orqali — ko'radi), faqat ilova
    // qayta ochilganda (yangi `HomeViewModel` — `autoExpandedOnce` qaytadan
    // ishga tushib) "sakrab" to'g'irlanardi. Veb versiyada xuddi shu
    // ro'yxat `_loadHomeAddressesList` orqali har 10s'da yangilanadi
    // (`driver/home.html`) — shu bilan bir xil kadensiyada, karta ochiq
    // turgan paytda fonda jim yangilanadi (`queueLoading`ga tegilmaydi —
    // bu faqat BIRINCHI ochilishdagi spinner uchun). Diqqat: faqat
    // `queueDrivers` (haqiqatan ko'rsatiladigan ro'yxat) yangilanadi —
    // `queuePosition` (alohida raqam) `CurrentQueueCard`da umuman
    // ko'rsatilmaydi, shu sabab uni ham fon rejimida qayta so'rash
    // behuda tarmoq/batareya sarfi bo'lardi.
    private var queuePollJob: Job? = null
    private fun startQueuePolling() {
        queuePollJob?.cancel()
        queuePollJob = viewModelScope.launch {
            while (true) {
                delay(10_000)
                val addressId = _uiState.value.expandedAddressId
                if (addressId != null) {
                    val requestId = addressExpandRequestId
                    val result = repository.addressQueueDrivers(addressId)
                    // `toggleAddressExpand()`dagi bilan bir xil sabab: shu
                    // so'rov davom etayotgan payt haydovchi panelni
                    // yopib-qayta ochib ulgursa (yangi so'rov boshlansa),
                    // shu (ESKI) fon so'rovi keyinroq javob berib, YANGI
                    // ochilishning natijasini bosib yozib qo'ymasin.
                    if (
                        result is ApiResult.Success &&
                        _uiState.value.expandedAddressId == addressId &&
                        requestId == addressExpandRequestId
                    ) {
                        _uiState.value = _uiState.value.copy(queueDrivers = result.data)
                    }
                }
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

    // `setDriver()` endi sahifa qayta yaratilganda mahalliy `is_on_duty`ni
    // ustun qo'yadi (yuqoridagi izohga qarang) — bu haydovchining o'zi
    // bosgan tugmasini himoya qiladi, lekin buning "narxi" bor: mahalliy va
    // server holati IKKALA yo'nalishda ham chalkashib qolishi mumkin —
    // (1) server haydovchini O'ZI navbatdan chiqarib qo'ysa (masalan
    // `driverapp_views.py` + `utils.auto_offline_stale_drivers()` — GPS
    // `AUTO_OFFLINE_MINUTES` davomida kelmasa), YOKI (2) `toggleDuty()`
    // so'rovi serverga YETIB BORIB bajarilgan bo'lsa-yu, javobi tarmoq
    // uzilishi sabab yo'qolib qolsa (`duty/toggle/` toggle — idempotent
    // EMAS, shu sabab `safeCall`ning o'zi ham qayta urinsa ham natija
    // serverda haqiqatan nima bo'lganidan qat'i nazar noaniq qolishi
    // mumkin) — bu holda mahalliy "oflayn"ga qaytariladi (xatolik
    // hisoblanib), server esa "onlayn" deb qolaveradi. Ilova bu ikkalasi
    // haqida ham hech qachon o'zidan bilib olmas edi. Shu sabab kam-kam
    // (60s — tez-tez emas, bu shunchaki "server meni hali ham NIMA deb
    // bilyapti" tekshiruvi) serverdan so'raladi va HAR IKKI yo'nalishdagi
    // tafovut ham tuzatiladi.
    //
    // Diqqat: shu bir so'rovning O'ZI endi `balance`/`rating`/`trips_count`
    // kabi boshqa server-hisoblaydigan maydonlarni ham yangilaydi —
    // `BalanceChangedBus` (push orqali darhol) ANIQ shu maqsadda mavjud,
    // lekin push yo'qolib qolishi (tarmoq, ilova hali biror ekranga
    // kirmagan bo'lishi) yoki javob xato bo'lishi mumkin — shu holatlarda
    // ham balans 60s ichida O'ZI tuzalib qolishi uchun zaxira sifatida.
    private var dutySyncPollJob: Job? = null
    private fun startDutySyncPolling() {
        dutySyncPollJob?.cancel()
        dutySyncPollJob = viewModelScope.launch {
            while (true) {
                delay(60_000)
                if (_uiState.value.driver != null) {
                    val result = repository.me()
                    // Diqqat: `repository.me()` javob berguncha (sekin tarmoq)
                    // haydovchi is_on_duty'ni o'zgartirib ulgurgan bo'lishi
                    // mumkin — shu sabab ENG SO'NGGI holatdan (await'dan
                    // OLDINGI eskirgan qiymatdan emas) olinadi.
                    val latest = _uiState.value.driver
                    if (result is ApiResult.Success && latest != null) {
                        // is_on_duty uchun: faqat serverning "onlayn -> oflayn"
                        // tuzatishi qabul qilinadi (auto-offline) — aks holda
                        // mahalliy holat ustun (`toggleDuty()`ning o'zi
                        // boshqaradi). Boshqa barcha maydonlar esa har doim
                        // eng yangi server qiymatidan olinadi.
                        val onDuty = if (!result.data.is_on_duty && latest.is_on_duty) false else latest.is_on_duty
                        _uiState.value = _uiState.value.copy(driver = result.data.copy(is_on_duty = onDuty))
                        if (onDuty != latest.is_on_duty) syncLocationService(onDuty)
                    }
                }
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

    // Haydovchi bitta manzilni tez-tez ochib-yopib-qayta ochsa (masalan A ->
    // yopish -> A) — har bir ochish o'zining mustaqil so'rovini boshlaydi.
    // Faqat `expandedAddressId`ga qarab tekshirish YETARLI EMAS: agar SHU
    // BIR XIL manzil qayta ochilsa, ID solishtirish "true" bo'lib qoladi,
    // lekin javob ESKI (birinchi) so'rovdan kelayotgan bo'lishi mumkin —
    // shu sabab har bir chaqiruv o'zining noyob raqamini oladi, faqat ENG
    // SO'NGGISI natijani qo'llaydi.
    private var addressExpandRequestId = 0

    fun toggleAddressExpand(address: AddressDto, forceExpand: Boolean = false) {
        val current = _uiState.value
        if (!forceExpand && current.expandedAddressId == address.id) {
            addressExpandRequestId++
            _uiState.value = current.copy(expandedAddressId = null, queuePosition = null, queueDrivers = emptyList())
            return
        }
        val requestId = ++addressExpandRequestId
        _uiState.value = current.copy(expandedAddressId = address.id, queueLoading = true)
        viewModelScope.launch {
            // Diqqat: avval bu ikkalasi KETMA-KET so'ralar edi (ikkinchisi
            // birinchisi tugashini kutib turardi) — har biri tarmoq
            // sekinlashganda ~15-45s cho'zilishi mumkinligini hisobga
            // olsak, bu "Joriy navbatingiz" kartasini ikki barobar sekin
            // ochilishiga olib kelardi. Endi ikkalasi PARALEL so'raladi.
            val posDeferred = async { repository.addressQueuePosition(address.id, driverLat, driverLng) }
            val driversDeferred = async { repository.addressQueueDrivers(address.id) }
            val posResult = posDeferred.await()
            val driversResult = driversDeferred.await()
            // Shu so'rov davom etayotgan payt haydovchi panelni yopgan
            // bo'lsa — natija endi kerak emas, lekin avvalgi versiyada bu
            // yerda qaytib ketilganda `queueLoading` HECH QACHON false
            // qilinmasdi, panel qayta ochilganda bir zumga eski
            // "yuklanmoqda" holati bilan chizilib ketishi mumkin edi.
            // Diqqat: agar shu orada BOSHQA manzil ochilgan bo'lsa (null
            // emas, boshqa ID), `queueLoading`ga tegilmaydi — u holatni
            // endi O'SHA (yangi) so'rovning o'zi to'g'ri boshqaradi.
            if (_uiState.value.expandedAddressId != address.id || requestId != addressExpandRequestId) {
                if (_uiState.value.expandedAddressId == null) {
                    _uiState.value = _uiState.value.copy(queueLoading = false)
                }
                return@launch
            }
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

    private var dutyToggleJob: Job? = null

    fun toggleDuty() {
        // Tugma tez-tez (masalan ikki marta ustma-ust) bosilsa — oldingi
        // so'rov hali javob bermagan paytda ikkinchisi boshlansa,
        // ikkinchisining `previousDriver`i BIRINCHISINING optimistik
        // (hali tasdiqlanmagan) qiymatini olib qo'yardi; ikkalasi ham xato
        // qaytarsa, holat serverdagi haqiqiy oxirgi holatga emas, o'sha
        // oraliq qiymatga qaytardi. Shu sabab davom etayotgan so'rov bo'lsa,
        // yangisi e'tiborsiz qoldiriladi.
        if (dutyToggleJob?.isActive == true) return
        val previousDriver = _uiState.value.driver ?: return
        // Optimistik yangilanish: tugma bosilgan zahoti DARHOL yangi
        // holatni ko'rsatadi, server javobini kutib turmaydi. Avval bu
        // yerda faqat server javobi kelgach o'zgarardi — tarmoq sekin
        // bo'lganda (safCall() ichida qayta urinishlar bilan ~45s gacha
        // cho'zilishi mumkin) "tugma bosilgandan ancha keyin o'zgaryapti"
        // degan shikoyatga aynan shu sabab bo'lgan edi. Xato qaytsa —
        // pastda ORQAGA qaytariladi.
        val optimisticOnDuty = !previousDriver.is_on_duty
        _uiState.value = _uiState.value.copy(driver = previousDriver.copy(is_on_duty = optimisticOnDuty))
        syncLocationService(optimisticOnDuty)
        dutyToggleJob = viewModelScope.launch {
            when (val result = repository.toggleDuty()) {
                is ApiResult.Success -> {
                    val driver = _uiState.value.driver?.copy(is_on_duty = result.data.is_on_duty)
                    _uiState.value = _uiState.value.copy(driver = driver)
                    syncLocationService(result.data.is_on_duty)
                    refreshOrders()
                }
                is ApiResult.Error -> {
                    // Diqqat: butun `previousDriver`ga emas, FAQAT
                    // `is_on_duty`ga qaytariladi — so'rov davom etayotgan
                    // paytda `setDriver()` orqali kelgan yangiroq maydonlar
                    // (masalan balans) shu bilan yo'qolib ketmasin.
                    val current = _uiState.value.driver
                    _uiState.value = _uiState.value.copy(
                        driver = current?.copy(is_on_duty = previousDriver.is_on_duty) ?: previousDriver,
                        error = result.message,
                    )
                    syncLocationService(previousDriver.is_on_duty)
                }
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
        // Ilova ICHIDAGI "Qabul qilish" tugmasi bosilganda — agar bu
        // buyurtma haqida bildirishnoma (push) ilgari ko'rsatilgan bo'lsa
        // (notificationId=order_id, VijdonFirebaseMessagingService'ga
        // qarang), uni ham darhol yopamiz. Aks holda push bildirishnoma
        // faqat o'zining tugmasi (yoki auto-cancel) orqali yopilardi —
        // ilova ichida qabul qilingandan keyin ekranda "osilib" qolardi.
        NotificationManagerCompat.from(context).cancel(id)
        runAction<OrderDto>(id, onSuccess = { accepted ->
            DriverSoundPlayer.play(DriverSoundEvent.ACCEPT)
            openClientDialer(accepted.client_phone)
        }) { repository.acceptOrder(id) }
    }

    /** Buyurtma qabul qilingandan so'ng — mijozga qo'ng'iroq qilish uchun
     * telefon terish ekranini avtomatik ochadi (qo'lda "Qo'ng'iroq"
     * tugmasini qidirib o'tirmasin, chunki odatda birinchi ish — mijozga
     * yo'lga chiqqanini xabar qilish). Faqat TERADI, o'zi qo'ng'iroq
     * QILMAYDI — haydovchi hali ham "Qo'ng'iroq" tugmasini bosishi kerak.
     * Diqqat: raqam `acceptOrder()` javobining O'ZIDAN olinadi, `state.
     * orders`dan emas — u hali eski ('pending') holatdagi, niqoblangan
     * ("+998 90 *** ** 67") raqamni saqlab turishi mumkin edi. */
    private fun openClientDialer(phone: String) {
        if (phone.isBlank()) return
        try {
            val intent = Intent(Intent.ACTION_DIAL, Uri.parse("tel:$phone")).apply {
                addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)
            }
            context.startActivity(intent)
        } catch (_: Exception) {
        }
    }

    fun rejectOrder(id: Int) {
        if (id == TEST_ORDER_ID) {
            alertOrderId = null
            _uiState.value = _uiState.value.copy(alertOrder = null)
            return
        }
        NotificationManagerCompat.from(context).cancel(id)
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

    private fun <T> runAction(orderId: Int, onSuccess: (T) -> Unit = {}, block: suspend () -> ApiResult<T>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionInProgress = _uiState.value.actionInProgress + orderId)
            when (val result = block()) {
                is ApiResult.Success -> {
                    refreshOrders()
                    onSuccess(result.data)
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
        dutySyncPollJob?.cancel()
        queuePollJob?.cancel()
        balanceRefreshJob?.cancel()
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
