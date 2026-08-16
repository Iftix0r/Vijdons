package uz.vijdon.driver.ui.theme

import androidx.compose.animation.core.LinearEasing
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.aspectRatio
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material.icons.rounded.ErrorOutline
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.geometry.CornerRadius
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.Shape
import androidx.compose.ui.text.TextStyle
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import uz.vijdon.driver.util.formatMoney
import kotlin.math.sin

/**
 * Veb paneldagi "2 navbatda" / "Yakunlandi" kabi dumaloq nishonlar. Fon
 * sukut bo'yicha matn rangining o'zidan tintlanadi (`.pill-green`/`.pill-red`
 * web klasslari kabi) — bir xil neytral kulrang fonda rangli matnga
 * qaraganda ancha yaxshi kontrast beradi.
 */
@Composable
fun Pill(text: String, color: Color = VijdonColors.TextSecondary, background: Color = color.copy(alpha = 0.18f), modifier: Modifier = Modifier) {
    Text(
        text,
        color = color,
        style = MaterialTheme.typography.labelMedium,
        modifier = modifier
            .background(background, CircleShape)
            .padding(horizontal = 12.dp, vertical = 6.dp),
    )
}

val CardShape = RoundedCornerShape(CardRadius)
val ChipShape = RoundedCornerShape(ChipRadius)

/**
 * Balans matnini ko'rsatadi — qiymat o'zgarganda (masalan operator
 * to'ldirganda/ayirganda) raqamlar ORASIDA "aylanib" o'tadi, shu orqali
 * haydovchi o'zgarishni sezmasdan qolmaydi (avval raqam sezilmasdan,
 * sakrab yangilanardi — faqat ilovani qayta ochganda ko'rinardi).
 */
@Composable
fun AnimatedBalanceText(
    balance: String,
    modifier: Modifier = Modifier,
    color: Color = VijdonColors.Green,
    style: TextStyle = MaterialTheme.typography.labelMedium,
    suffix: String = "so'm",
) {
    val suffixed = if (suffix.isEmpty()) "" else " $suffix"
    val target = balance.toFloatOrNull()
    // Diqqat: `Float` ~16.7 mln'dan katta butun sonlarni ANIQ ifodalay
    // olmaydi (7 xonali aniqlik) — uzoq muddat ishlagan haydovchida
    // balans shu chegaradan oshib ketishi mumkin, shunda animatsiya
    // OXIRIDA (nishon qiymatning o'zida) bir necha birlik xato ko'rinib
    // qolardi. Shu sabab bunday holatlarda (yoki `balance` umuman raqam
    // bo'lmasa) animatsiyasiz, to'g'ridan-to'g'ri ANIQ qiymat ko'rsatiladi
    // — avvalgi (animatsiyasiz) xatti-harakat bilan bir xil.
    if (target == null || kotlin.math.abs(target) > 9_000_000f) {
        Text("${formatMoney(balance)}$suffixed", color = color, style = style, modifier = modifier)
        return
    }
    val animated by animateFloatAsState(targetValue = target, animationSpec = tween(durationMillis = 700), label = "balance")
    Text("${formatMoney(animated.toLong().toString())}$suffixed", color = color, style = style, modifier = modifier)
}

/**
 * Kartalarga yengil "ko'tarilgan" soya beradi. Diqqat: Yandex Pro'ning
 * o'zi og'ir soyali kartalar emas — TEKIS, grid-asosli bo'linmalar
 * ishlatadi (chuqurlik emas, bo'sh joy va chiziqlar bilan ajratish), shu
 * sabab sukut bo'yicha soya juda yengil (deyarli sezilmas) qilindi — faqat
 * chindan "suzib turadigan" elementlar (FAB, sarlavha) uchun yuqoriroq
 * qiymat beriladi.
 */
fun Modifier.cardShadow(
    shape: Shape = CardShape,
    elevation: androidx.compose.ui.unit.Dp = 2.dp,
    glowColor: Color = Color.Black,
    clip: Boolean = false,
): Modifier =
    this.shadow(elevation = elevation, shape = shape, clip = clip, ambientColor = glowColor, spotColor = glowColor)

/**
 * Veb paneldagi `.ios-navbar` + `.ios-large-title` bilan bir xil — suzib
 * turuvchi, dumaloq burchakli, chapga tekislangan katta sarlavha kartasi.
 * Barcha ichki ekranlarda (Tarix, Reyting, Manzillar, Balans, Shartnoma,
 * SOS...) bir xil uslubdagi sarlavha uchun ishlatiladi.
 */
@Composable
fun ScreenHeader(title: String, subtitle: String? = null, modifier: Modifier = Modifier, onBack: (() -> Unit)? = null) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(horizontal = if (onBack != null) 8.dp else 18.dp, vertical = if (onBack != null) 4.dp else 16.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        if (onBack != null) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Orqaga", tint = VijdonColors.TextPrimary)
            }
            Spacer(Modifier.width(2.dp))
        }
        Column {
            Text(
                title,
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
            )
            subtitle?.let {
                Spacer(Modifier.height(2.dp))
                Text(it, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

/**
 * Pastki panel bo'limlari ("Asosiy", "Tarix", "Profil") uchun — `ScreenHeader`
 * kabi soyali/suzuvchi karta EMAS, balki fonga to'g'ridan-to'g'ri yozilgan
 * TEKIS sarlavha. Ikkisining farqi ataylab: tab-bo'limlar (asosiy navigatsiya)
 * shu tekis uslubda, ichki (orqaga tugmali) sahifalar esa `ScreenHeader`
 * kartasida — shu bilan foydalanuvchi qayerda ekanini (asosiy tab / ichki
 * sahifa) hatto tugmasiz ham bir qarashda sezadi.
 */
@Composable
fun TabHeader(title: String, subtitle: String? = null, modifier: Modifier = Modifier) {
    Column(modifier = modifier.fillMaxWidth()) {
        Text(
            title,
            color = VijdonColors.TextPrimary,
            style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold),
        )
        subtitle?.let {
            Spacer(Modifier.height(2.dp))
            Text(it, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
    }
}

// "1351" — dispatch raqami, taksimetr uslubidagi segmentlardan (7-segment
// joylashuvi) yasalgan. `ic_launcher_foreground.xml` bilan bir xil 240x84
// koordinata katakchasi — faqat u yerda VectorDrawable pathData, bu yerda
// esa to'g'ridan-to'g'ri Canvas'ga chizilgan rounded-rect segmentlar.
private data class DispatchSegment(val x: Float, val y: Float, val w: Float, val h: Float)

private val DISPATCH_MARK_SEGMENTS: List<DispatchSegment> = run {
    val a = DispatchSegment(9f, 0f, 30f, 10f)
    val f = DispatchSegment(0f, 7f, 10f, 33f)
    val b = DispatchSegment(38f, 7f, 10f, 33f)
    val g = DispatchSegment(9f, 37f, 30f, 10f)
    val c = DispatchSegment(38f, 44f, 10f, 33f)
    val d = DispatchSegment(9f, 74f, 30f, 10f)
    fun shifted(offset: Float, segs: List<DispatchSegment>) = segs.map { it.copy(x = it.x + offset) }
    shifted(0f, listOf(b, c)) +            // "1"
        shifted(64f, listOf(a, b, g, c, d)) +  // "3"
        shifted(128f, listOf(a, f, g, c, d)) + // "5"
        shifted(192f, listOf(b, c))            // "1"
}
private const val DISPATCH_MARK_WIDTH = 240f
private const val DISPATCH_MARK_HEIGHT = 84f

/**
 * Brendlangan yuklanish animatsiyasi — oddiy dumaloq spinner o'rniga
 * "1351" belgisining segmentlari ustidan yorug'lik to'lqini o'tib turadi
 * (taksimetr yoqilganda raqamlar ustma-ust yonib-o'chganini eslatadi).
 * Splash-holat (`MainActivity`dagi `LoadingBox`) va barcha `CenteredLoading`
 * ekranlarida ishlatiladi.
 */
@Composable
fun DispatchLoadingMark(modifier: Modifier = Modifier, color: Color = VijdonColors.Yellow) {
    val infinite = rememberInfiniteTransition(label = "dispatch-mark")
    val t by infinite.animateFloat(
        initialValue = 0f,
        targetValue = (2 * Math.PI).toFloat(),
        animationSpec = infiniteRepeatable(animation = tween(2200, easing = LinearEasing)),
        label = "dispatch-mark-phase",
    )
    Canvas(modifier = modifier.aspectRatio(DISPATCH_MARK_WIDTH / DISPATCH_MARK_HEIGHT)) {
        val scale = size.width / DISPATCH_MARK_WIDTH
        val radius = CornerRadius(5f * scale, 5f * scale)
        DISPATCH_MARK_SEGMENTS.forEachIndexed { index, seg ->
            val glow = sin(t - index * 0.35f) * 0.5f + 0.5f
            drawRoundRect(
                color = color.copy(alpha = 0.3f + 0.7f * glow),
                topLeft = Offset(seg.x * scale, seg.y * scale),
                size = Size(seg.w * scale, seg.h * scale),
                cornerRadius = radius,
            )
        }
    }
}

/**
 * Ro'yxat birinchi marta yuklanayotganda (hali natija ham, xato ham yo'q)
 * ko'rsatiladi — aks holda ekran bir lahzaga "hozircha hech narsa yo'q"
 * degan noto'g'ri xulosaga olib keladigan bo'sh holatni ko'rsatib qo'yardi.
 */
@Composable
fun CenteredLoading(modifier: Modifier = Modifier) {
    Box(modifier = modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        DispatchLoadingMark(modifier = Modifier.width(96.dp), color = VijdonColors.Yellow)
    }
}

/**
 * Veb paneldagi buyurtma kartalaridagi kabi — yashil nuqta (qayerdan) va
 * qizil manzil belgisi (qayerga) orasida chiziq bilan marshrutni bir
 * qarashda ko'rsatadi. Matn prefiksi ("Qayerdan:"/"Qayerga:") o'rniga shu
 * vizual belgi ishlatiladi — Buyurtma kartasi (Home) va Tarix bir xil.
 * B nuqta har doim (manzil ko'rsatilmagan bo'lsa ham) chiziladi — ba'zi
 * kartalarda faqat A, boshqalarida A+B ko'rinishi haydovchini
 * chalg'itmasligi uchun format doim bir xil bo'lishi kerak.
 */
@Composable
fun RouteAddresses(fromAddress: String, toAddress: String, modifier: Modifier = Modifier) {
    val hasDestination = toAddress.isNotBlank()
    Row(modifier = modifier) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, modifier = Modifier.padding(top = 4.dp)) {
            Box(modifier = Modifier.size(8.dp).background(VijdonColors.Green, CircleShape))
            Box(modifier = Modifier.width(2.dp).height(20.dp).padding(vertical = 2.dp).background(VijdonColors.Border))
            Icon(
                Icons.Rounded.LocationOn, contentDescription = null,
                tint = if (hasDestination) VijdonColors.Red else VijdonColors.TextSecondary.copy(alpha = 0.5f),
                modifier = Modifier.size(12.dp),
            )
        }
        Spacer(Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(fromAddress, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
            Spacer(Modifier.height(6.dp))
            Text(
                if (hasDestination) toAddress else "Manzil ko'rsatilmagan",
                color = VijdonColors.TextSecondary.copy(alpha = if (hasDestination) 1f else 0.6f),
                style = MaterialTheme.typography.bodyMedium,
            )
        }
    }
}

/** Tarmoq/server xatoligini ko'rsatuvchi qizil banner — barcha ro'yxat ekranlarida bir xil ko'rinishda. */
@Composable
fun ErrorBanner(message: String, modifier: Modifier = Modifier) {
    Row(
        modifier = modifier
            .fillMaxWidth()
            .background(VijdonColors.Red.copy(alpha = 0.12f), CardShape)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Rounded.ErrorOutline, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
        Spacer(Modifier.width(8.dp))
        Text(message, color = VijdonColors.Red, style = MaterialTheme.typography.bodySmall)
    }
}
