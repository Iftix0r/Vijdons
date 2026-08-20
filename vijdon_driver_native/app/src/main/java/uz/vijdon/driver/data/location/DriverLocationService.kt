package uz.vijdon.driver.data.location

import android.Manifest
import android.app.Notification
import android.app.NotificationManager
import android.app.PendingIntent
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
import androidx.core.app.NotificationManagerCompat
import androidx.core.app.ServiceCompat
import com.google.android.gms.location.LocationCallback
import com.google.android.gms.location.LocationRequest
import com.google.android.gms.location.LocationResult
import com.google.android.gms.location.LocationServices
import com.google.android.gms.location.Priority
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.CoroutineScope
import kotlinx.coroutines.SupervisorJob
import kotlinx.coroutines.cancel
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import uz.vijdon.driver.MainActivity
import uz.vijdon.driver.R
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.push.DriverSoundEvent
import uz.vijdon.driver.data.push.DriverSoundPlayer
import uz.vijdon.driver.data.push.OrderActionReceiver
import uz.vijdon.driver.data.push.OrderAlertDismissReceiver
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import uz.vijdon.driver.util.DeviceInfo
import javax.inject.Inject
import kotlin.math.sqrt

/**
 * Haydovchi "onlayn" bo'lgan vaqt davomida ishlaydigan fon xizmati — GPS
 * nuqtalarini /location/ endpointga yuboradi (dispetcherlik va manzil
 * navbati shunga tayanadi) va har bir nuqtani LocationBus orqali taximetrga
 * ham uzatadi. Veb ilovadagi doimiy Wake Lock o'rniga foreground service +
 * doimiy bildirishnoma ishlatiladi (Android'ning tavsiya etilgan usuli).
 */
@AndroidEntryPoint
class DriverLocationService : Service() {

    @Inject lateinit var repository: DriverRepository

    private val scope = CoroutineScope(SupervisorJob())
    private var lastReportedLat: Double? = null
    private var lastReportedLng: Double? = null
    private var lastReportedAtMs: Long = 0L

    /** FCM endi ulangan — "shaxsan menga yuborilgan" yangi buyurtma haqida
     * asosiy signal endi VijdonFirebaseMessagingService.onMessageReceived()
     * orqali (deyarli bir zumda, ilova fonda/o'chirilgan bo'lsa ham) keladi.
     * Shu polling endi faqat ZAXIRA — ba'zi qurilmalarda (masalan agressiv
     * "battery saver"li Xiaomi/Huawei kabi OEM'lar) FCM push kechikishi yoki
     * butunlay yetib bormasligi mumkin, shu holat uchun davom etadi. */
    private var alertedOrderId: Int?
        get() = prefs().getInt(PREF_ALERTED_ORDER_ID, -1).takeIf { it != -1 }
        set(value) { prefs().edit().putInt(PREF_ALERTED_ORDER_ID, value ?: -1).apply() }

    private fun prefs() = getSharedPreferences("driver_location_service", MODE_PRIVATE)

    private val fusedClient by lazy { LocationServices.getFusedLocationProviderClient(this) }
    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            scope.launch {
                LocationBus.emit(
                    LocationPoint(
                        location.latitude, location.longitude, location.accuracy,
                        if (location.hasSpeed()) location.speed else 0f,
                        System.currentTimeMillis(),
                    ),
                )
            }
            // "Online bo'lish" bosilgan zahoti FusedLocationProvider ko'pincha
            // birinchi navbatda tarmoq/hujayra minorasi asosidagi taxminiy
            // (aniqligi past — yuzlab metr xato bilan) nuqtani qaytaradi, aniq
            // GPS fix bir necha soniyadan keyin keladi. Bu taxminiy nuqta
            // serverga yuborilsa, haydovchi haqiqatda u yerda bo'lmasa ham
            // yaqin atrofdagi SavedAddress navbatiga (ADDRESS_QUEUE_RADIUS_KM
            // 300m) xato qo'shilib qolishi mumkin edi. Shu sabab yetarlicha
            // aniq (accuracy) nuqta kelmaguncha serverga umuman yubormaymiz.
            if (location.accuracy <= LOCATION_ACCURACY_THRESHOLD_M) {
                maybeReportToServer(location.latitude, location.longitude)
            }
        }
    }

    override fun onCreate() {
        super.onCreate()
        // Android 14+ (API 34) joylashuv turidagi foreground service'ni
        // ACCESS_FINE_LOCATION ruxsati bo'lmasa boshlashga umuman
        // ruxsat bermaydi (SecurityException) — shu sabab avval ruxsat
        // tekshiriladi, aks holda hech qanday bildirishnoma ko'rsatmasdan
        // darhol to'xtaydi (HomeViewModel ham xuddi shu tekshiruvni
        // qiladi, lekin bu yerda ham himoya sifatida qoldirilgan).
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            stopSelf()
            return
        }
        startForegroundWithNotification()
        startLocationUpdates()
        startOrderAlertPolling()
        // Ovozlar (HomeViewModel bilan bir xil) — ilova hech ochilmagan,
        // faqat shu fon xizmati onlayn bo'lgan holatda ham "Yangi buyurtma"
        // ovozi to'g'ri chalinishi uchun shu yerda ham yuklab olinadi.
        scope.launch {
            val result = repository.driverSounds()
            if (result is ApiResult.Success) DriverSoundPlayer.updateSounds(result.data)
        }
    }

    override fun onStartCommand(intent: Intent?, flags: Int, startId: Int): Int = START_STICKY

    override fun onDestroy() {
        fusedClient.removeLocationUpdates(locationCallback)
        scope.cancel()
        super.onDestroy()
    }

    override fun onBind(intent: Intent?): IBinder? = null

    private fun startForegroundWithNotification() {
        val notification: Notification = NotificationCompat.Builder(this, "duty_channel")
            .setContentTitle("Siz onlaynsiz")
            .setContentText("Yangi buyurtmalarni kutyapmiz")
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setOngoing(true)
            .build()
        val serviceType = if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            ServiceInfo.FOREGROUND_SERVICE_TYPE_LOCATION
        } else {
            0
        }
        ServiceCompat.startForeground(this, 1, notification, serviceType)
    }

    private fun startLocationUpdates() {
        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            stopSelf()
            return
        }
        val request = LocationRequest.Builder(Priority.PRIORITY_HIGH_ACCURACY, 5_000L)
            .setMinUpdateIntervalMillis(3_000L)
            .build()
        fusedClient.requestLocationUpdates(request, locationCallback, mainLooper)
    }

    /** Har bir nuqtada emas — >=30m harakatda YOKI 2 daqiqadan ko'p vaqt
     * o'tganda serverga yuboradi. Diqqat: avval FAQAT harakat mezoni bo'lgan
     * (>=30m) — bu haydovchi to'xtab turganda (masalan svetofor/navbatda)
     * `last_seen` yangilanmay qolishiga olib kelardi, ko'p joyda ishlatiladigan
     * "oxirgi 120s ichida ko'ringan = onlayn" tekshiruvi uni noto'g'ri
     * "oflayn" deb hisoblab qolishi mumkin edi. Vaqt mezoni shu muammoni
     * bartaraf qiladi — haydovchi harakatsiz bo'lsa ham holati yangi turadi. */
    private fun maybeReportToServer(lat: Double, lng: Double) {
        val prevLat = lastReportedLat
        val prevLng = lastReportedLng
        val now = System.currentTimeMillis()
        val movedEnough = prevLat == null || prevLng == null || distanceMeters(prevLat, prevLng, lat, lng) >= 30.0
        val staleByTime = now - lastReportedAtMs >= 90_000L
        if (!movedEnough && !staleByTime) return
        lastReportedLat = lat
        lastReportedLng = lng
        lastReportedAtMs = now
        val battery = DeviceInfo.batteryPercent(this)
        scope.launch { repository.sendLocation(lat, lng, battery) }
    }

    private fun distanceMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val dLat = (lat2 - lat1) * 111_000
        val dLng = (lng2 - lng1) * 111_000 * kotlin.math.cos(Math.toRadians(lat1))
        return sqrt(dLat * dLat + dLng * dLng)
    }

    /** "Menga shaxsan yuborilgan" mezoni (is_dispatched + hali tugamagan
     * timer_sec) — ekrandagi HomeViewModel.refreshOrders() bilan bir xil.
     * Diqqat: FCM ulanmasdan oldin bu yerda 3s oralig'da so'ralar edi (o'sha
     * paytda YAGONA signal manbai shu edi, operatordagi `dispatch_timeout`
     * SUKUT BO'YICHA atigi 10 soniya bo'lgani uchun tez-tez so'rash shart
     * edi). Endi FCM push tezkor asosiy kanal bo'lgani sabab bu — faqat
     * zaxira tarmoq: FCM chindan yetib bormagan kamdan-kam holatda ham
     * haydovchi butunlay bexabar qolmasin degan "xavfsizlik to'ri". */
    private fun startOrderAlertPolling() {
        scope.launch {
            while (true) {
                pollForDispatchedOrder()
                delay(6_000L)
            }
        }
    }

    private suspend fun pollForDispatchedOrder() {
        val result = repository.availableOrders()
        if (result !is ApiResult.Success) return
        val candidate = result.data.orders.firstOrNull {
            it.isPending && it.is_dispatched && (it.timer_sec ?: 0) > 0
        }
        if (candidate == null) {
            // Buyurtma endi nomzod emas (qabul/rad etildi, vaqti tugadi yoki
            // boshqasiga o'tkazildi) — hali ijro etilib turgan ringtone va
            // shu buyurtmaga oid bildirishnoma bo'lsa, himoya sifatida shu
            // yerda ham to'xtatiladi/yopiladi (asosiy to'xtatish odatda
            // OrderActionReceiver/HomeViewModel orqali allaqachon bo'lgan
            // bo'ladi — bu faqat zaxira).
            val previous = alertedOrderId
            alertedOrderId = null
            if (previous != null) {
                DriverSoundPlayer.stop()
                NotificationManagerCompat.from(this).cancel(previous)
            }
            return
        }
        // Bir xil buyurtma uchun har 6 soniyada qayta-qayta bezovta
        // qilmaslik — faqat YANGI (hali ogohlantirilmagan) buyurtmada.
        if (candidate.id == alertedOrderId) return
        alertedOrderId = candidate.id
        showNewOrderNotification(candidate)
    }

    private fun showNewOrderNotification(order: OrderDto) {
        DriverSoundPlayer.play(DriverSoundEvent.NEW_ORDER)
        val intent = Intent(this, MainActivity::class.java).apply {
            flags = Intent.FLAG_ACTIVITY_NEW_TASK or Intent.FLAG_ACTIVITY_CLEAR_TOP
            putExtra(MainActivity.EXTRA_NEW_ORDER_ALERT, true)
        }
        val pendingIntent = PendingIntent.getActivity(
            this, order.id, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
        val builder = NotificationCompat.Builder(this, "new_orders_channel")
            .setContentTitle("Yangi buyurtma!")
            .setContentText(order.from_address)
            .setSmallIcon(R.drawable.ic_launcher_foreground)
            .setContentIntent(pendingIntent)
            .setDeleteIntent(orderAlertDismissPendingIntent(order.id))
            .setAutoCancel(true)
            // Bir xil ID'ga qayta `notify()` chaqirilsa (masalan keyingi
            // poll'da hali ham shu buyurtma ko'rsatilsa) — kanalning o'z
            // ovozi/vibratsiyasi faqat BIRINCHI marta chalinadi, har safar
            // emas.
            .setOnlyAlertOnce(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)
            .addAction(0, "✅ Qabul qilish", orderActionPendingIntent(order.id, OrderActionReceiver.ACTION_ACCEPT))
            .addAction(0, "❌ Rad etish", orderActionPendingIntent(order.id, OrderActionReceiver.ACTION_REJECT))

        // "To'liq ekran" bildirishnoma — VijdonFirebaseMessagingService bilan
        // bir xil (ilova fonda yoki qurilma qulflangan bo'lsa ham, boshqa
        // ilovalar ustidan avtomatik ochiladi).
        val canUseFullScreen = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE ||
            getSystemService(NotificationManager::class.java).canUseFullScreenIntent()
        if (canUseFullScreen) {
            builder.setFullScreenIntent(pendingIntent, true)
        }

        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            // Diqqat: ID endi TURG'UN doimiy qiymat (2) EMAS, `order.id` —
            // VijdonFirebaseMessagingService va HomeViewModel.acceptOrder()/
            // rejectOrder() aynan shu ID (order.id) bo'yicha yopadi. Avval
            // bu yerda alohida turg'un ID ishlatilgani sabab, ilova ICHIDA
            // "Qabul qilish" bosilganda ushbu (poll orqali ko'rsatilgan)
            // bildirishnoma UMUMAN yopilmas edi — notifikatsiya ekranda
            // "osilib" qolar, hech kim yopmagani uchun.
            NotificationManagerCompat.from(this).notify(order.id, builder.build())
        }
    }

    /** Bildirishnomadagi "Qabul qilish"/"Rad etish" tugmasi bosilganda —
     * ilovani ochmasdan, to'g'ridan-to'g'ri `OrderActionReceiver`ga
     * (boshqa ilova ustida turgan holatda ham) signal beradi. */
    private fun orderActionPendingIntent(orderId: Int, actionName: String): PendingIntent {
        val intent = Intent(this, OrderActionReceiver::class.java).apply {
            action = actionName
            putExtra(OrderActionReceiver.EXTRA_ORDER_ID, orderId)
            putExtra(OrderActionReceiver.EXTRA_NOTIFICATION_ID, orderId)
        }
        val requestCode = orderId * 10 + (if (actionName == OrderActionReceiver.ACTION_ACCEPT) 1 else 2)
        return PendingIntent.getBroadcast(this, requestCode, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE)
    }

    /** Bildirishnoma tugmasiz, oddiy SURIB (swipe) yopilganda ham
     * "Yangi buyurtma" ringtoni to'xtatilishi uchun. */
    private fun orderAlertDismissPendingIntent(orderId: Int): PendingIntent {
        val intent = Intent(this, OrderAlertDismissReceiver::class.java)
        return PendingIntent.getBroadcast(
            this, orderId * 10 + 3, intent, PendingIntent.FLAG_UPDATE_CURRENT or PendingIntent.FLAG_IMMUTABLE,
        )
    }

    private companion object {
        const val PREF_ALERTED_ORDER_ID = "alerted_order_id"
        const val LOCATION_ACCURACY_THRESHOLD_M = 100f
    }
}
