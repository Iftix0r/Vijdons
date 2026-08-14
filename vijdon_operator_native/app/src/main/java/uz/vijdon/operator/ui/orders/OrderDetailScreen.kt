package uz.vijdon.operator.ui.orders

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.data.api.OrderDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.Pill
import uz.vijdon.operator.ui.theme.RouteAddresses
import uz.vijdon.operator.ui.theme.ScreenHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

@Composable
fun OrderDetailScreen(orderId: Int, onBack: () -> Unit, viewModel: OrderDetailViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    if (state.deleted) {
        onBack()
        return
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Column(modifier = Modifier.padding(16.dp)) {
            ScreenHeader(title = "Buyurtma #$orderId", onBack = onBack)
        }
        when {
            state.loading && state.order == null -> CenteredLoading()
            state.error != null && state.order == null -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
            state.order != null -> OrderDetailContent(state, viewModel)
        }
    }
}

@Composable
private fun OrderDetailContent(state: OrderDetailUiState, viewModel: OrderDetailViewModel) {
    val order = state.order!!
    LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
        item {
            Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
                Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                    Text(order.client_name, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
                    Pill(order.status_label, color = statusColor(order.status))
                }
                Text(order.client_phone, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
                if (order.client_is_blocked) {
                    Spacer(Modifier.height(6.dp))
                    Pill("Bloklangan mijoz", color = VijdonColors.Red)
                }
                Spacer(Modifier.height(12.dp))
                RouteAddresses(order.from_address, order.to_address)
                Spacer(Modifier.height(12.dp))
                InfoRow("Narx", order.price?.let { "${formatMoney(it)} so'm" } ?: "—")
                InfoRow("Komissiya", "${formatMoney(order.commission)} so'm")
                InfoRow("To'lov turi", order.payment_type_display)
                InfoRow("Mashina turi", order.car_type_display)
                if (order.is_delivery) InfoRow("Turi", "Yetkazib berish")
                if (order.note.isNotBlank()) InfoRow("Izoh", order.note)
                if (order.cancel_reason.isNotBlank()) InfoRow("Bekor sababi", order.cancel_reason)
            }
        }

        item {
            Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
                Text("Haydovchi", style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
                Spacer(Modifier.height(8.dp))
                when {
                    order.driver_name != null -> {
                        InfoRow("Tayinlangan", order.driver_name)
                        order.driver_phone?.let { InfoRow("Telefon", it) }
                    }
                    order.dispatched_to_name != null -> InfoRow("Yuborilgan", order.dispatched_to_name)
                    else -> Text("Haydovchi tayinlanmagan", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
                }
                if (order.isPending) {
                    Spacer(Modifier.height(12.dp))
                    DriverPicker(drivers = state.drivers, onSelect = { viewModel.assignDriver(it) })
                }
            }
        }

        if (order.rejected_by.isNotEmpty() || order.dispatch_attempts.isNotEmpty()) {
            item {
                Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
                    Text("Dispetcherlash tarixi", style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
                    Spacer(Modifier.height(8.dp))
                    order.dispatch_attempts.forEach { a ->
                        Text("${a.attempt_number}. ${a.driver_name} — ${a.result_label}" + (a.distance_km?.let { " (%.1f km)".format(it) } ?: ""), style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
                    }
                    if (order.rejected_by.isNotEmpty()) {
                        Spacer(Modifier.height(8.dp))
                        Text("Rad etganlar: " + order.rejected_by.joinToString(", ") { it.full_name }, style = MaterialTheme.typography.bodySmall, color = VijdonColors.Red)
                    }
                }
            }
        }

        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                if (order.isPending) {
                    Button(
                        onClick = { viewModel.dispatch() },
                        enabled = !state.actionLoading,
                        colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Blue, contentColor = VijdonColors.TextOnBlue),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Dispetcherlash") }
                }
                if (order.status == "accepted") {
                    OutlinedButton(onClick = { viewModel.setStatus("on_way") }, modifier = Modifier.fillMaxWidth(), enabled = !state.actionLoading) { Text("Yo'lda deb belgilash") }
                }
                if (order.status == "on_way") {
                    OutlinedButton(onClick = { viewModel.setStatus("arrived") }, modifier = Modifier.fillMaxWidth(), enabled = !state.actionLoading) { Text("Yetib keldi deb belgilash") }
                }
                if (order.isActive) {
                    OutlinedButton(onClick = { viewModel.setStatus("completed") }, modifier = Modifier.fillMaxWidth(), enabled = !state.actionLoading) { Text("Yakunlash") }
                    Button(
                        onClick = { viewModel.cancelAndReopen() },
                        enabled = !state.actionLoading,
                        colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Red.copy(alpha = 0.12f), contentColor = VijdonColors.Red),
                        modifier = Modifier.fillMaxWidth(),
                    ) { Text("Bekor qilish (komissiya qaytariladi)") }
                }
                var confirmDelete by remember { mutableStateOf(false) }
                if (!confirmDelete) {
                    TextButton(onClick = { confirmDelete = true }, modifier = Modifier.fillMaxWidth()) {
                        Text("Buyurtmani o'chirish", color = VijdonColors.Red)
                    }
                } else {
                    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        TextButton(onClick = { confirmDelete = false }) { Text("Bekor qilish") }
                        TextButton(onClick = { viewModel.delete() }) { Text("Ha, o'chirish", color = VijdonColors.Red) }
                    }
                }
                state.error?.let { Spacer(Modifier.height(4.dp)); ErrorBanner(it) }
            }
        }
        item { Spacer(Modifier.height(40.dp)) }
    }
}

@Composable
private fun DriverPicker(drivers: List<uz.vijdon.operator.data.api.DriverDto>, onSelect: (Int) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    Box {
        OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
            Text("Haydovchi tayinlash")
        }
        DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            drivers.forEach { d ->
                DropdownMenuItem(text = { Text("${d.full_name} (${d.car_number})") }, onClick = { expanded = false; onSelect(d.id) })
            }
        }
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
        Text(value, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextPrimary)
    }
}
