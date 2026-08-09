package uz.vijdon.driver.ui.history

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Flag
import androidx.compose.material.icons.rounded.Payments
import androidx.compose.material.icons.rounded.Route
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun HistoryScreen(viewModel: HistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        Text("Tarix", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.headlineMedium)
        Spacer(Modifier.height(12.dp))

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

        Spacer(Modifier.height(10.dp))
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
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            StatCard(Icons.Rounded.Flag, "Jami", state.completed.toString(), VijdonColors.Yellow, Modifier.weight(1f))
            StatCard(Icons.Rounded.Payments, "Daromad", "${state.totalEarned.toInt()} so'm", VijdonColors.Green, Modifier.weight(1f))
            StatCard(Icons.Rounded.Route, "Km", String.format("%.1f", state.totalKm), VijdonColors.Blue, Modifier.weight(1f))
        }

        Spacer(Modifier.height(14.dp))
        if (state.visibleOrders.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Bu bo'limda buyurtma yo'q", color = VijdonColors.TextSecondary)
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.visibleOrders, key = { it.id }) { order -> HistoryRow(order) }
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
        modifier = modifier.background(VijdonColors.Surface, CardShape).padding(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(icon, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text(label, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.height(4.dp))
        Text(value, color = valueColor, style = MaterialTheme.typography.titleMedium)
    }
}

@Composable
private fun HistoryRow(order: OrderDto) {
    Column(
        modifier = Modifier.fillMaxWidth().background(VijdonColors.Surface, CardShape).padding(14.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Pill(
                order.status_label,
                color = if (order.status == "completed") VijdonColors.Green else VijdonColors.Red,
                background = VijdonColors.BadgeNeutral,
            )
            Text("#${order.id} · ${order.created_at.take(10)}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
        }
        Spacer(Modifier.height(8.dp))
        Text(order.from_address, color = VijdonColors.TextPrimary)
        if (order.to_address.isNotBlank()) {
            Text(order.to_address, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
        Spacer(Modifier.height(8.dp))
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
            Text(order.price?.let { "$it so'm" } ?: "—", color = VijdonColors.Green, style = MaterialTheme.typography.titleMedium)
            Text(order.client_phone, color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
    }
    Spacer(Modifier.height(10.dp))
}
