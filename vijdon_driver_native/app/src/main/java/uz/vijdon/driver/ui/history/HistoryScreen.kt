package uz.vijdon.driver.ui.history

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.IntrinsicSize
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CreditCard
import androidx.compose.material.icons.rounded.Flag
import androidx.compose.material.icons.rounded.Inbox
import androidx.compose.material.icons.rounded.Payments
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material.icons.rounded.Route
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextDecoration
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.RouteAddresses
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.formatMoney
import java.util.Locale

@Composable
fun HistoryScreen(viewModel: HistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    // Bottom-tab navigatsiyasida (saveState/restoreState) ViewModel qayta
    // yaratilmaydi, shu sabab `init{}`dagi bir martalik yuklash yetarli
    // emas — har safar shu bo'limga qaytilganda yangi yakunlangan
    // buyurtmalarni ko'rsatish uchun qayta so'raladi.
    LaunchedEffect(Unit) { viewModel.load() }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Tarix")
        Spacer(Modifier.height(12.dp))

        // Ikkita mustaqil filtr — holat (Hammasi/Yakunlangan/Bekor) va davr
        // (Bugun/7 kun/30 kun/Barchasi) — bir-biriga aralashib ketmasligi
        // uchun har biriga o'z sarlavhasi qo'yiladi, aks holda ikkalasida
        // ham "hammasi" ma'nosidagi so'z borligi haydovchini chalg'itardi.
        Text("HOLAT", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(4.dp))
        Row(
            modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface, CardShape).padding(4.dp),
            horizontalArrangement = Arrangement.SpaceEvenly,
        ) {
            STATUS_TABS.forEach { (value, label) ->
                val selected = state.statusTab == value
                Text(
                    label,
                    color = if (selected) VijdonColors.Background else VijdonColors.TextSecondary,
                    textAlign = TextAlign.Center,
                    style = MaterialTheme.typography.labelLarge,
                    modifier = Modifier
                        .weight(1f)
                        .background(if (selected) VijdonColors.TextPrimary else VijdonColors.Surface, ChipShape)
                        .clickable { viewModel.onStatusTabChange(value) }
                        .padding(vertical = 10.dp),
                )
            }
        }

        Spacer(Modifier.height(12.dp))
        Text("DAVR", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        Spacer(Modifier.height(4.dp))
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            HISTORY_PERIODS.forEach { (value, label) ->
                val selected = state.period == value
                Text(
                    label,
                    color = if (selected) VijdonColors.TextOnYellow else VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.labelMedium,
                    modifier = Modifier
                        .background(if (selected) VijdonColors.Yellow else VijdonColors.Surface, ChipShape)
                        .clickable { viewModel.onPeriodChange(value) }
                        .padding(horizontal = 12.dp, vertical = 8.dp),
                )
            }
        }

        Spacer(Modifier.height(14.dp))
        // Uchala karta bir xil balandlikda bo'lishi uchun Row IntrinsicSize.Min
        // bilan o'lchanadi va har bir karta shu balandlikkacha cho'ziladi —
        // aks holda uzunroq qiymatli (masalan "Daromad") karta boshqalaridan
        // balandroq bo'lib, tekis bo'lmagan qatorga aylanardi.
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.height(IntrinsicSize.Min)) {
            StatCard(Icons.Rounded.Flag, "Jami", state.completed.toString(), VijdonColors.Yellow, Modifier.weight(1f).fillMaxHeight())
            StatCard(Icons.Rounded.Payments, "Daromad", "${formatMoney(state.totalEarned.toString())} so'm", VijdonColors.Green, Modifier.weight(1f).fillMaxHeight())
            StatCard(Icons.Rounded.Route, "Km", String.format(Locale.US, "%.1f", state.totalKm), VijdonColors.Cyan, Modifier.weight(1f).fillMaxHeight())
        }

        state.error?.let {
            Spacer(Modifier.height(10.dp))
            ErrorBanner(it)
        }

        Spacer(Modifier.height(14.dp))
        if (state.loading && state.visibleOrders.isEmpty()) {
            CenteredLoading()
        } else if (state.visibleOrders.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier.size(72.dp).background(VijdonColors.Surface, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Rounded.Inbox, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(32.dp))
                    }
                    Spacer(Modifier.height(12.dp))
                    Text("Bu bo'limda buyurtma yo'q", color = VijdonColors.TextSecondary)
                }
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.visibleOrders, key = { it.id }) { order ->
                    Column(Modifier.animateItem()) { HistoryRow(order) }
                }
            }
        }
    }
}

@Composable
private fun StatCard(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    label: String,
    value: String,
    valueColor: androidx.compose.ui.graphics.Color,
    modifier: Modifier = Modifier,
) {
    Column(
        modifier = modifier.cardShadow().background(VijdonColors.Surface, CardShape).padding(horizontal = 10.dp, vertical = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = valueColor, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text(label, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall, maxLines = 1)
        }
        Spacer(Modifier.height(6.dp))
        Text(
            value,
            color = valueColor,
            style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            textAlign = TextAlign.Center,
        )
    }
}

/** Server "yyyy-MM-ddTHH:mm:ss..." beradi — veb'dagi kabi "kun.oy soat:daqiqa" ko'rinishiga o'giradi. */
internal fun formatHistoryDate(iso: String): String {
    if (iso.length < 16) return iso
    val month = iso.substring(5, 7)
    val day = iso.substring(8, 10)
    val time = iso.substring(11, 16)
    return "$day.$month $time"
}

@Composable
private fun HistoryRow(order: OrderDto) {
    val isCompleted = order.status == "completed"
    Column(
        modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(14.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Pill(
                order.status_label,
                color = if (isCompleted) VijdonColors.Green else VijdonColors.Red,
                background = VijdonColors.BadgeNeutral,
            )
            // Avval labelSmall + TextSecondary edi — juda kichik va xira
            // bo'lgani uchun o'qish qiyin edi, shu sabab kattaroq shrift va
            // to'liq (alpha kamaytirilmagan) rangga o'tkazildi.
            Text(
                "#${order.id} · ${formatHistoryDate(order.created_at)}",
                color = VijdonColors.TextPrimary.copy(alpha = 0.7f),
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Medium),
            )
        }
        Spacer(Modifier.height(12.dp))
        RouteAddresses(order.from_address, order.to_address)
        Spacer(Modifier.height(10.dp))
        HorizontalDivider(color = VijdonColors.Border)
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            // Bekor qilingan/yakunlanmagan buyurtmada narx chindan olinmagan
            // pul emas — veb'dagi kabi chiziqcha bilan, xira rangda ko'rsatiladi,
            // aks holda haydovchi buni "ishlab topilgan" deb noto'g'ri tushunishi
            // mumkin. To'lov turi endi emoji emas, aniq ikonka bilan ko'rsatiladi
            // — narx yonida turgan "💵"/"💳" avval mijoz raqami bilan bir qatorda
            // bo'lib, nima ekanligi (haydovchi ID, mijoz raqami, to'lov turi?)
            // noaniq edi.
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(
                    if (order.payment_type == "cash") Icons.Rounded.Payments else Icons.Rounded.CreditCard,
                    contentDescription = if (order.payment_type == "cash") "Naqd" else "Karta",
                    tint = VijdonColors.TextSecondary,
                    modifier = Modifier.size(15.dp),
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    order.price?.let { "${formatMoney(it)} so'm" } ?: "—",
                    color = if (isCompleted) VijdonColors.Green else VijdonColors.TextSecondary,
                    style = MaterialTheme.typography.titleMedium.copy(
                        fontWeight = FontWeight.Bold,
                        textDecoration = if (isCompleted) null else TextDecoration.LineThrough,
                    ),
                )
            }
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                order.distance_km?.let {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Icon(Icons.Rounded.Route, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(13.dp))
                        Spacer(Modifier.width(3.dp))
                        Text(String.format(Locale.US, "%.1f km", it), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
                    }
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Icon(Icons.Rounded.Phone, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(13.dp))
                    Spacer(Modifier.width(3.dp))
                    Text(order.client_phone, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
                }
            }
        }
    }
    Spacer(Modifier.height(10.dp))
}
