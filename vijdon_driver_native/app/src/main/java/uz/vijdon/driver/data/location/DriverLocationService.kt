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
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
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

    // FCM hali sozlanmagan (Firebase loyihasi ulanmagan) — shu sabab
    // "shaxsan menga yuborilgan" yangi buyurtmani ilova fonda/boshqa ilova
    // ustida ochiq bo'lganda ham bilish uchun push'ga tayanib bo'lmaydi.
    // Shu foreground service (haydovchi onlayn bo'lgan vaqt davomida ishlaydi)
    // GPS bilan bir qatorda buyurtmalarni ham davriy so'raydi va topilsa
    // xuddi FCM push kelgandagi kabi to'liq ekranli bildirishnoma chiqaradi
    // (VijdonFirebaseMessagingService.onMessageReceived bilan bir xil uslubda).
    private var alertedOrderId: Int? = null

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
            maybeReportToServer(location.latitude, location.longitude)
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

    /** Har bir nuqtada emas — >=30m harakatda yoki 60s dan ko'p vaqt o'tganda serverga yuboradi. */
    private fun maybeReportToServer(lat: Double, lng: Double) {
        val prevLat = lastReportedLat
        val prevLng = lastReportedLng
        val movedEnough = prevLat == null || prevLng == null || distanceMeters(prevLat, prevLng, lat, lng) >= 30.0
        if (!movedEnough) return
        lastReportedLat = lat
        lastReportedLng = lng
        scope.launch { repository.sendLocation(lat, lng) }
    }

    private fun distanceMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val dLat = (lat2 - lat1) * 111_000
        val dLng = (lng2 - lng1) * 111_000 * kotlin.math.cos(Math.toRadians(lat1))
        return sqrt(dLat * dLat + dLng * dLng)
    }

    /** HomeViewModel.refreshOrders()dagi bilan bir xil kadensiya (~4-6s) va
     * "menga shaxsan yuborilgan" mezoni (is_dispatched + hali tugamagan
     * timer_sec) — ekranda ham, shu yerda ham bir xil buyurtma alert deb topiladi. */
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
            alertedOrderId = null
            return
        }
        // Bir xil buyurtma uchun har 6 soniyada qayta-qayta bezovta
        // qilmaslik — faqat YANGI (hali ogohlantirilmagan) buyurtmada.
        if (candidate.id == alertedOrderId) return
        alertedOrderId = candidate.id
        showNewOrderNotification(candidate)
    }

    private fun showNewOrderNotification(order: OrderDto) {
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
            .setAutoCancel(true)
            .setPriority(NotificationCompat.PRIORITY_HIGH)
            .setCategory(NotificationCompat.CATEGORY_CALL)

        // "To'liq ekran" bildirishnoma — VijdonFirebaseMessagingService bilan
        // bir xil (ilova fonda yoki qurilma qulflangan bo'lsa ham, boshqa
        // ilovalar ustidan avtomatik ochiladi).
        val canUseFullScreen = Build.VERSION.SDK_INT < Build.VERSION_CODES.UPSIDE_DOWN_CAKE ||
            getSystemService(NotificationManager::class.java).canUseFullScreenIntent()
        if (canUseFullScreen) {
            builder.setFullScreenIntent(pendingIntent, true)
        }

        if (ActivityCompat.checkSelfPermission(this, Manifest.permission.POST_NOTIFICATIONS) == PackageManager.PERMISSION_GRANTED) {
            NotificationManagerCompat.from(this).notify(NEW_ORDER_ALERT_NOTIFICATION_ID, builder.build())
        }
    }

    private companion object {
        const val NEW_ORDER_ALERT_NOTIFICATION_ID = 2
    }
}
