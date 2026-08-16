package uz.vijdon.driver.ui.widget

import android.content.Context
import androidx.work.CoroutineWorker
import androidx.work.WorkerParameters
import dagger.hilt.android.EntryPointAccessors
import uz.vijdon.driver.data.push.OrderActionEntryPoint
import uz.vijdon.driver.data.repository.ApiResult

/**
 * Bosh ekran vidjeti uchun 30 daqiqalik fon yangilanishi (Android'ning
 * eng qisqa ruxsat beradigan oralig'i) — `SessionViewModel`/
 * `VijdonFirebaseMessagingService` orqali kelgan tezroq yangilanishlarga
 * qo'shimcha "zaxira", ilova uzoq ochilmagan/push kelmagan holatlar uchun.
 *
 * `OrderActionWorker.kt`dagi bilan AYNAN bir xil naqsh — `@HiltWorker`
 * EMAS (kapt nomuvofiqligi sabab, `app/build.gradle.kts`da hujjatlashtirilgan),
 * mavjud `OrderActionEntryPoint`ning o'zi qayta ishlatiladi (yangi
 * EntryPoint interfeysi yaratish shart emas — u ham `driverRepository()`ni beradi).
 */
class WidgetRefreshWorker(context: Context, params: WorkerParameters) : CoroutineWorker(context, params) {
    override suspend fun doWork(): Result {
        val repository = EntryPointAccessors.fromApplication(applicationContext, OrderActionEntryPoint::class.java).driverRepository()
        val result = repository.me()
        if (result is ApiResult.Success) {
            updateWidgetData(applicationContext, result.data)
        }
        // Tarmoq vaqtinchalik yo'q bo'lsa ham qayta-qayta urinib
        // "muvaffaqiyatsizlik"ka chiqarish shart emas — vidjet oxirgi
        // ko'rgan ma'lumotini ko'rsatishda davom etadi, keyingi safar
        // (30 daqiqadan keyin yoki ilova ochilganda) qayta uriniladi.
        return Result.success()
    }
}
