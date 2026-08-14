package uz.vijdon.driver.data.push

import android.content.Context
import android.content.Intent
import androidx.core.app.NotificationManagerCompat
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.hilt.EntryPoint
import dagger.hilt.InstallIn
import dagger.hilt.android.EntryPointAccessors
import dagger.hilt.components.SingletonComponent
import uz.vijdon.driver.MainActivity
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository

/** `androidx.hilt:hilt-work`ning `@HiltWorker` kapt generatsiyasi hozirgi
 * Kotlin (2.2.20) metadata formatini o'qiy olmasdan xato berdi, shu sabab
 * bu yerda Hilt'ning kodsiz (`EntryPointAccessors`) usuli ishlatiladi —
 * `OrderActionWorker` WorkManager'ning ODDIY (context, params) Worker'i
 * sifatida qoladi, faqat kerak bo'lganda `DriverRepository`ni shu orqali
 * qo'lda "so'rab oladi". */
@EntryPoint
@InstallIn(SingletonComponent::class)
interface OrderActionEntryPoint {
    fun driverRepository(): DriverRepository
}

/**
 * Bildirishnomadagi "Qabul qilish"/"Rad etish" tugmasi bosilganda haqiqiy
 * tarmoq so'rovini bajaradi — `OrderActionReceiver` (oddiy `goAsync()` +
 * korutina) o'rniga WorkManager ishlatiladi, chunki tizim (ayniqsa OEM'larning
 * agressiv quvvat tejash rejimlari) ilova jarayonini bildirishnoma bosilgan
 * zahoti to'xtatib qo'yishi mumkin edi — natijada so'rov hech qachon
 * serverga yetib bormay qolardi. WorkManager esa buni albatta (kerak
 * bo'lsa jarayon qayta tirilgach ham) bajarilishini kafolatlaydi.
 */
class OrderActionWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {

    override suspend fun doWork(): Result {
        val orderId = inputData.getInt(KEY_ORDER_ID, -1)
        if (orderId == -1) return Result.failure()
        val action = inputData.getString(KEY_ACTION)
        val notificationId = inputData.getInt(KEY_NOTIFICATION_ID, orderId)

        // SINOV buyurtmasi serverda mavjud emas — API'ga murojaat qilinmaydi,
        // faqat bildirishnoma yopiladi.
        if (orderId != TEST_ORDER_ID) {
            val repository = EntryPointAccessors.fromApplication(applicationContext, OrderActionEntryPoint::class.java).driverRepository()
            when (action) {
                OrderActionReceiver.ACTION_ACCEPT -> {
                    if (repository.acceptOrder(orderId) is ApiResult.Success) {
                        DriverSoundPlayer.play(DriverSoundEvent.ACCEPT)
                        // Ilova ochilib, to'g'ridan-to'g'ri shu buyurtma tafsiloti
                        // ko'rsatilsin — haydovchi qabul qilgandan keyin nima
                        // bo'layotganini darhol ko'rishi kerak.
                        val intent = Intent(applicationContext, MainActivity::class.java).apply {
                            flags = Intent.FLAG_ACTIVITY_NEW_TASK
                            putExtra(MainActivity.EXTRA_OPEN_ORDER_ID, orderId)
                        }
                        applicationContext.startActivity(intent)
                    }
                }
                OrderActionReceiver.ACTION_REJECT -> {
                    if (repository.rejectOrder(orderId) is ApiResult.Success) {
                        DriverSoundPlayer.play(DriverSoundEvent.REJECT)
                    }
                }
            }
        }

        NotificationManagerCompat.from(applicationContext).cancel(notificationId)
        // Bildirishnomani yopish "Yangi buyurtma" ringtonini to'xtatmaydi
        // (ikkalasi mustaqil) — shu sabab bu yerda ham aniq to'xtatiladi.
        DriverSoundPlayer.stop()
        return Result.success()
    }

    companion object {
        const val KEY_ORDER_ID = "order_id"
        const val KEY_ACTION = "action"
        const val KEY_NOTIFICATION_ID = "notification_id"
    }
}
