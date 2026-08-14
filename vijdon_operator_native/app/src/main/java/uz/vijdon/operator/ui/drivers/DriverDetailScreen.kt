package uz.vijdon.operator.ui.drivers

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
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
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
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
import uz.vijdon.operator.ui.orders.OrderCard
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.Pill
import uz.vijdon.operator.ui.theme.ScreenHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

@Composable
fun DriverDetailScreen(driverId: Int, onBack: () -> Unit, viewModel: DriverDetailViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var showRecharge by remember { mutableStateOf(false) }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Column(modifier = Modifier.padding(16.dp)) {
            ScreenHeader(title = "Haydovchi", onBack = onBack)
        }
        when {
            state.loading && state.driver == null -> CenteredLoading()
            state.error != null && state.driver == null -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
            state.driver != null -> {
                val d = state.driver!!
                LazyColumn(contentPadding = PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    item {
                        Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(16.dp)) {
                            Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Text(d.full_name, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
                                Pill(if (d.is_online) "Onlayn" else "Offlayn", color = if (d.is_online) VijdonColors.Green else VijdonColors.TextSecondary)
                            }
                            Text(d.phone_number, style = MaterialTheme.typography.bodyMedium, color = VijdonColors.TextSecondary)
                            Spacer(Modifier.height(10.dp))
                            InfoRow("Mashina", "${d.car_model} — ${d.car_number} (${d.car_type_display})")
                            InfoRow("Balans", "${formatMoney(d.balance)} so'm")
                            InfoRow("Reyting", d.rating)
                            InfoRow("Safarlar soni", d.trips_count.toString())
                            InfoRow("Holati", d.approval_status_display)
                            if (d.is_qarzdor) InfoRow("Qarzdor", d.qarz_note.ifBlank { "Ha" })
                        }
                    }

                    if (d.isPending) {
                        item {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                Button(
                                    onClick = { viewModel.approve(true) },
                                    enabled = !state.actionLoading,
                                    colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Green, contentColor = androidx.compose.ui.graphics.Color.White),
                                    modifier = Modifier.weight(1f),
                                ) { Text("Tasdiqlash") }
                                OutlinedButton(onClick = { viewModel.approve(false) }, enabled = !state.actionLoading, modifier = Modifier.weight(1f)) { Text("Rad etish") }
                            }
                        }
                    } else {
                        item {
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedButton(onClick = viewModel::toggleActive, enabled = !state.actionLoading, modifier = Modifier.weight(1f)) {
                                    Text(if (d.is_active) "Bloklash" else "Blokdan chiqarish")
                                }
                                OutlinedButton(onClick = viewModel::toggleFrozen, enabled = !state.actionLoading, modifier = Modifier.weight(1f)) {
                                    Text(if (d.is_frozen) "Muzlashni bekor qilish" else "Muzlatish")
                                }
                            }
                        }
                        item {
                            Button(
                                onClick = { showRecharge = true },
                                enabled = !state.actionLoading,
                                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Blue, contentColor = VijdonColors.TextOnBlue),
                                modifier = Modifier.fillMaxWidth(),
                            ) { Text("Balans qo'shish/ayirish") }
                        }
                    }

                    state.error?.let { item { ErrorBanner(it) } }

                    if (state.recentOrders.isNotEmpty()) {
                        item { Text("So'nggi buyurtmalar", style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary) }
                        items(state.recentOrders) { order -> OrderCard(order, onClick = {}) }
                    }
                    item { Spacer(Modifier.height(40.dp)) }
                }
            }
        }
    }

    if (showRecharge) {
        DriverRechargeDialog(
            loading = state.actionLoading,
            onDismiss = { showRecharge = false },
            onConfirm = { amount, deduct, note -> viewModel.recharge(amount, deduct, note) { showRecharge = false } },
        )
    }
}

@Composable
private fun InfoRow(label: String, value: String) {
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
        Text(value, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextPrimary)
    }
}

@Composable
private fun DriverRechargeDialog(loading: Boolean, onDismiss: () -> Unit, onConfirm: (String, Boolean, String) -> Unit) {
    var amount by remember { mutableStateOf("") }
    var deduct by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf("") }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Balans qo'shish/ayirish") },
        text = {
            Column {
                OutlinedTextField(value = amount, onValueChange = { amount = it }, label = { Text("Summa") }, modifier = Modifier.fillMaxWidth())
                Spacer(Modifier.height(10.dp))
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = deduct, onCheckedChange = { deduct = it })
                    Text(if (deduct) "Ayirish" else "Qo'shish")
                }
                OutlinedTextField(value = note, onValueChange = { note = it }, label = { Text("Izoh (ixtiyoriy)") }, modifier = Modifier.fillMaxWidth())
            }
        },
        confirmButton = {
            TextButton(onClick = { onConfirm(amount, deduct, note) }, enabled = !loading && amount.isNotBlank()) { Text("Saqlash") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}
