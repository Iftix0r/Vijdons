package uz.vijdon.driver.ui.home

import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.animation.core.tween
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.Payments
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableLongStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Size
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.StrokeCap
import androidx.compose.ui.graphics.drawscope.Stroke
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Yandex Pro haydovchi ilovasidagi kabi — yangi (shaxsan shu haydovchiga
 * yo'naltirilgan) buyurtma kelganda butun ekranni egallaydigan, aylana
 * countdown-taymerli qabul/rad qilish ekrani. Vaqt tugasa (yoki boshqa
 * haydovchi qabul qilib ulgursa) buyurtma ro'yxatdan o'chib, bu ekran ham
 * o'zi yopiladi (HomeViewModel `alertOrder=null` qilib qo'yadi).
 */
@Composable
fun IncomingOrderOverlay(order: OrderDto, totalSec: Int, onAccept: () -> Unit, onReject: () -> Unit) {
    val safeTotal = totalSec.coerceAtLeast(1)
    var remainingMs by remember(order.id) { mutableLongStateOf((order.timer_sec ?: safeTotal).toLong() * 1000L) }

    // Server har poll'da (~4s) haqiqiy qolgan vaqtni qaytaradi — shu bilan
    // qayta sinxronlanadi, lekin orasidagi tebranishni silliq ko'rsatish
    // uchun mahalliy 200ms tikligi davom etadi.
    LaunchedEffect(order.timer_sec) {
        order.timer_sec?.let { remainingMs = it.toLong() * 1000L }
    }
    LaunchedEffect(order.id) {
        while (isActive) {
            delay(200)
            remainingMs = (remainingMs - 200).coerceAtLeast(0)
        }
    }

    val fraction by animateFloatAsState(
        targetValue = (remainingMs / 1000f / safeTotal).coerceIn(0f, 1f),
        animationSpec = tween(200),
        label = "countdown",
    )
    val ringColor = if (fraction < 0.25f) VijdonColors.Red else VijdonColors.Yellow

    Column(
        modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.End) {
            androidx.compose.material3.IconButton(onClick = onReject) {
                Icon(Icons.Rounded.Close, contentDescription = "Rad etish", tint = VijdonColors.TextSecondary)
            }
        }

        Spacer(Modifier.weight(1f))

        val trackColor = VijdonColors.Border
        Box(contentAlignment = Alignment.Center, modifier = Modifier.size(180.dp)) {
            Canvas(modifier = Modifier.fillMaxSize()) {
                val stroke = Stroke(width = 10.dp.toPx(), cap = StrokeCap.Round)
                drawArc(
                    color = trackColor,
                    startAngle = -90f,
                    sweepAngle = 360f,
                    useCenter = false,
                    style = stroke,
                    size = Size(size.width - stroke.width, size.height - stroke.width),
                    topLeft = androidx.compose.ui.geometry.Offset(stroke.width / 2, stroke.width / 2),
                )
                drawArc(
                    color = ringColor,
                    startAngle = -90f,
                    sweepAngle = 360f * fraction,
                    useCenter = false,
                    style = stroke,
                    size = Size(size.width - stroke.width, size.height - stroke.width),
                    topLeft = androidx.compose.ui.geometry.Offset(stroke.width / 2, stroke.width / 2),
                )
            }
            Column(horizontalAlignment = Alignment.CenterHorizontally) {
                Text(
                    "${(remainingMs / 1000).coerceAtLeast(0)}",
                    style = MaterialTheme.typography.displayMedium,
                    color = VijdonColors.TextPrimary,
                )
                Text("soniya", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
            }
        }

        Spacer(Modifier.height(28.dp))
        Text("Yangi buyurtma!", style = MaterialTheme.typography.headlineSmall, color = VijdonColors.TextPrimary)
        Spacer(Modifier.height(16.dp))

        order.price?.let {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Payments, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(20.dp))
                Spacer(Modifier.width(6.dp))
                Text("$it so'm", style = MaterialTheme.typography.headlineSmall, color = VijdonColors.Green)
            }
            Spacer(Modifier.height(12.dp))
        }

        Column(
            modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface, MaterialTheme.shapes.large).padding(16.dp),
        ) {
            AddressLine(order.from_address, VijdonColors.Yellow)
            if (order.to_address.isNotBlank()) {
                Spacer(Modifier.height(8.dp))
                AddressLine(order.to_address, VijdonColors.Blue)
            }
        }
        Spacer(Modifier.height(4.dp))
        Text(
            "${order.client_name} · ${order.client_phone}",
            color = VijdonColors.TextSecondary,
            style = MaterialTheme.typography.bodySmall,
            textAlign = TextAlign.Center,
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp),
        )

        Spacer(Modifier.weight(1f))

        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            OutlinedButton(
                onClick = onReject,
                colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.Red),
                modifier = Modifier.weight(1f).height(56.dp),
            ) { Text("Rad etish") }
            Button(
                onClick = onAccept,
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
                modifier = Modifier.weight(2f).height(56.dp),
            ) { Text("Qabul qilish", style = MaterialTheme.typography.titleMedium) }
        }
    }
}

@Composable
private fun AddressLine(text: String, dotColor: Color) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Box(modifier = Modifier.size(10.dp).background(dotColor, CircleShape))
        Spacer(Modifier.width(10.dp))
        Text(text, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
    }
}
