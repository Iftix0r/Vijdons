package uz.vijdon.driver.ui.widget

import android.content.Context
import android.content.Intent
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.datastore.preferences.core.Preferences
import androidx.datastore.preferences.core.booleanPreferencesKey
import androidx.datastore.preferences.core.intPreferencesKey
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.glance.GlanceId
import androidx.glance.GlanceModifier
import androidx.glance.action.clickable
import androidx.glance.appwidget.GlanceAppWidget
import androidx.glance.appwidget.GlanceAppWidgetManager
import androidx.glance.appwidget.GlanceAppWidgetReceiver
import androidx.glance.appwidget.action.actionStartActivity
import androidx.glance.appwidget.cornerRadius
import androidx.glance.appwidget.provideContent
import androidx.glance.appwidget.state.updateAppWidgetState
import androidx.glance.appwidget.updateAll
import androidx.glance.background
import androidx.glance.layout.Alignment
import androidx.glance.layout.Column
import androidx.glance.layout.Row
import androidx.glance.layout.Spacer
import androidx.glance.layout.fillMaxSize
import androidx.glance.layout.fillMaxWidth
import androidx.glance.layout.height
import androidx.glance.layout.padding
import androidx.glance.layout.width
import androidx.glance.state.PreferencesGlanceStateDefinition
import androidx.glance.currentState
import androidx.glance.text.FontWeight
import androidx.glance.text.Text
import androidx.glance.text.TextStyle
import androidx.glance.unit.ColorProvider
import uz.vijdon.driver.MainActivity
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.util.formatMoney

private val KEY_NAME = stringPreferencesKey("driver_name")
private val KEY_ON_DUTY = booleanPreferencesKey("driver_on_duty")
private val KEY_BALANCE = stringPreferencesKey("driver_balance")
private val KEY_RATING = stringPreferencesKey("driver_rating")
private val KEY_TRIPS = intPreferencesKey("driver_trips")
private val KEY_CAR = stringPreferencesKey("driver_car")

// Vidjet — brend belgisi ("1351" ikon) bilan bir xil, TURG'UN (kun/tun
// rejimiga moslashmaydigan) rang sxemasi: sariq (#F5B400) fon, to'q
// (#1A1A1A) matn. Diqqat: `ColorProvider`ning kun/tun (day/night)
// parametrli konstruktori bu Glance versiyasida yo'q edi (build xatosi
// berdi) — shu sabab eng oddiy, kafolatlangan `ColorProvider(Color)`
// ishlatiladi.
private val INK = ColorProvider(Color(0xFF1A1A1A))
private val DIM = ColorProvider(Color(0xFF6B5A00))
private val AMBER_BG = ColorProvider(Color(0xFFF5B400))
private val GREEN = ColorProvider(Color(0xFF1E8E3E))
private val GRAY = ColorProvider(Color(0xFF8A8A8A))

/** "Iftixor To'ychiyev" -> "Iftixor T." — `HomeScreen.kt`dagi `shortDriverName`
 * bilan bir xil g'oya (bu yerda alohida nusxasi — u fayl `private`). */
private fun shortName(fullName: String): String {
    val parts = fullName.trim().split(" ").filter { it.isNotBlank() }
    if (parts.size < 2) return fullName
    return "${parts[0]} ${parts[1].first()}."
}

/**
 * Telefon bosh ekrani vidjeti — haydovchi profilining "dashboard"i (ism,
 * onlayn/oflayn, balans, reyting, buyurtmalar soni, mashina). Android
 * vidjetlarni 30 daqiqadan tezroq avtomatik yangilashga umuman ruxsat
 * bermaydi (OS chegarasi) — shu sabab bu klass o'zi hech qachon tarmoqqa
 * murojaat qilmaydi, faqat `updateWidgetData()` orqali yozilgan OXIRGI
 * ma'lumotni ko'rsatadi. Haqiqiy yangilanish uch joydan keladi:
 * `SessionViewModel` (ilova ochilganda/profil yangilanganda),
 * `VijdonFirebaseMessagingService` (balans push'i kelganda) va
 * `WidgetRefreshWorker` (30 daqiqalik fon oqimi).
 */
class DriverDashboardWidget : GlanceAppWidget() {
    override val stateDefinition = PreferencesGlanceStateDefinition

    override suspend fun provideGlance(context: Context, id: GlanceId) {
        provideContent {
            val prefs = currentState<Preferences>()
            val name = prefs[KEY_NAME]
            val onDuty = prefs[KEY_ON_DUTY] ?: false
            val balance = prefs[KEY_BALANCE]
            val rating = prefs[KEY_RATING]
            val trips = prefs[KEY_TRIPS] ?: 0
            val car = prefs[KEY_CAR]

            val openAppIntent = Intent(context, MainActivity::class.java)

            Column(
                modifier = GlanceModifier
                    .fillMaxSize()
                    .background(AMBER_BG)
                    .cornerRadius(20.dp)
                    .padding(16.dp)
                    .clickable(actionStartActivity(openAppIntent)),
            ) {
                Row(
                    modifier = GlanceModifier.fillMaxWidth(),
                    verticalAlignment = Alignment.CenterVertically,
                ) {
                    Text(
                        if (onDuty) "● Onlayn" else "● Oflayn",
                        style = TextStyle(color = if (onDuty) GREEN else GRAY, fontSize = 12.sp),
                    )
                    Spacer(GlanceModifier.width(8.dp))
                    Text(
                        name?.let { shortName(it) } ?: "1351",
                        style = TextStyle(color = DIM, fontSize = 12.sp, fontWeight = FontWeight.Medium),
                    )
                }
                Spacer(GlanceModifier.height(10.dp))
                Text(
                    if (balance != null) "${formatMoney(balance)} so'm" else "— so'm",
                    style = TextStyle(color = INK, fontSize = 22.sp, fontWeight = FontWeight.Bold),
                )
                Spacer(GlanceModifier.height(8.dp))
                Row(modifier = GlanceModifier.fillMaxWidth()) {
                    Text(
                        "⭐ ${rating ?: "—"}",
                        style = TextStyle(color = INK, fontSize = 13.sp, fontWeight = FontWeight.Bold),
                    )
                    Spacer(GlanceModifier.width(16.dp))
                    Text(
                        "🚕 $trips ta safar",
                        style = TextStyle(color = DIM, fontSize = 13.sp),
                    )
                }
                Spacer(GlanceModifier.height(6.dp))
                Text(
                    car ?: "",
                    style = TextStyle(color = DIM, fontSize = 11.sp),
                )
            }
        }
    }
}

/** `SessionViewModel`, `VijdonFirebaseMessagingService`, `WidgetRefreshWorker`
 * — uchalasi ham shu bitta funksiya orqali vidjetni yangilaydi. Ekranda
 * hozircha bitta nusxa bo'lsa ham, foydalanuvchi bir nechta joyga qo'shib
 * qo'ygan bo'lishi mumkin — barcha nusxalarga bir xil ma'lumot yoziladi. */
suspend fun updateWidgetData(context: Context, driver: DriverDto) {
    val manager = GlanceAppWidgetManager(context)
    val ids = manager.getGlanceIds(DriverDashboardWidget::class.java)
    if (ids.isEmpty()) return
    for (id in ids) {
        updateAppWidgetState(context, id) { prefs ->
            prefs[KEY_NAME] = driver.full_name
            prefs[KEY_ON_DUTY] = driver.is_on_duty
            prefs[KEY_BALANCE] = driver.balance
            prefs[KEY_RATING] = driver.rating
            prefs[KEY_TRIPS] = driver.trips_count
            prefs[KEY_CAR] = "${driver.car_model} · ${driver.car_number}"
        }
    }
    DriverDashboardWidget().updateAll(context)
}

/** Vidjet qo'shilganda/yangilanish kerak bo'lganda tizim shu qabul
 * qiluvchini chaqiradi — o'zi hech narsa qilmaydi, faqat qaysi
 * `GlanceAppWidget`ni chizishni ko'rsatadi. */
class DriverDashboardWidgetReceiver : GlanceAppWidgetReceiver() {
    override val glanceAppWidget: GlanceAppWidget = DriverDashboardWidget()
}
