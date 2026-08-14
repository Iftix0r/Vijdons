package uz.vijdon.operator.ui.dashboard

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Logout
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.data.api.DashboardDto
import uz.vijdon.operator.data.api.OperatorDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.TabHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

@Composable
fun DashboardScreen(
    operator: OperatorDto,
    onOpenOrders: () -> Unit,
    onOpenBalance: () -> Unit,
    onOpenDrivers: () -> Unit,
    onLogout: () -> Unit,
    viewModel: DashboardViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    LazyColumn(
        modifier = Modifier.fillMaxSize().background(VijdonColors.Background),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
    ) {
        item {
            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                TabHeader(title = "Xush kelibsiz", subtitle = operator.full_name)
                IconButton(onClick = onLogout) {
                    Icon(Icons.Rounded.Logout, contentDescription = "Chiqish", tint = VijdonColors.TextSecondary)
                }
            }
        }
        when {
            state.loading && state.dashboard == null -> item { CenteredLoading(modifier = Modifier.height(200.dp)) }
            state.error != null && state.dashboard == null -> item { ErrorBanner(state.error!!) }
            else -> {
                val d = state.dashboard
                if (d != null) {
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatCard("Bugungi buyurtmalar", d.today_orders.toString(), VijdonColors.Blue, Modifier.weight(1f)) { onOpenOrders() }
                            StatCard("Bugungi tushum", "${formatMoney(d.today_revenue)} so'm", VijdonColors.Green, Modifier.weight(1f)) { onOpenBalance() }
                        }
                    }
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatCard("Kutilayotgan buyurtmalar", d.pending_orders.toString(), VijdonColors.Yellow, Modifier.weight(1f)) { onOpenOrders() }
                            StatCard("Kechikkan buyurtmalar", d.aging_orders.toString(), VijdonColors.Red, Modifier.weight(1f)) { onOpenOrders() }
                        }
                    }
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatCard("Ish navbatidagi haydovchilar", d.on_duty_drivers.toString(), VijdonColors.Green, Modifier.weight(1f)) { onOpenDrivers() }
                            StatCard("Onlayn haydovchilar", d.online_drivers.toString(), VijdonColors.Cyan, Modifier.weight(1f)) { onOpenDrivers() }
                        }
                    }
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatCard("Tasdiq kutayotgan haydovchilar", d.pending_driver_approvals.toString(), VijdonColors.Yellow, Modifier.weight(1f)) { onOpenDrivers() }
                            StatCard("Balansi kam haydovchilar", d.low_balance_drivers.toString(), VijdonColors.Red, Modifier.weight(1f)) { onOpenDrivers() }
                        }
                    }
                    item {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                            StatCard("Kutilayotgan to'lovlar", d.pending_topups.toString(), VijdonColors.Blue, Modifier.weight(1f)) { onOpenBalance() }
                            StatCard("Eskirgan to'lov so'rovlari", d.aging_topups.toString(), VijdonColors.Red, Modifier.weight(1f)) { onOpenBalance() }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun StatCard(label: String, value: String, accent: androidx.compose.ui.graphics.Color, modifier: Modifier = Modifier, onClick: () -> Unit) {
    Column(
        modifier = modifier
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(16.dp),
    ) {
        Text(value, style = MaterialTheme.typography.headlineMedium.copy(fontWeight = FontWeight.Bold), color = accent)
        Spacer(Modifier.height(4.dp))
        Text(label, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
    }
}
