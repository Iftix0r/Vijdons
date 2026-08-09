package uz.vijdon.driver.data.location

import android.Manifest
import android.app.Notification
import android.app.Service
import android.content.Intent
import android.content.pm.PackageManager
import android.content.pm.ServiceInfo
import android.os.Build
import android.os.IBinder
import androidx.core.app.ActivityCompat
import androidx.core.app.NotificationCompat
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
import kotlinx.coroutines.launch
import uz.vijdon.driver.R
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

    private val fusedClient by lazy { LocationServices.getFusedLocationProviderClient(this) }
    private val locationCallback = object : LocationCallback() {
        override fun onLocationResult(result: LocationResult) {
            val location = result.lastLocation ?: return
            scope.launch {
                LocationBus.emit(
                    LocationPoint(location.latitude, location.longitude, location.accuracy, System.currentTimeMillis()),
                )
            }
            maybeReportToServer(location.latitude, location.longitude)
        }
    }

    override fun onCreate() {
        super.onCreate()
        startForegroundWithNotification()
        startLocationUpdates()
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
}
