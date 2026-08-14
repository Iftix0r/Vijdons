package uz.vijdon.operator.ui.balance

import androidx.compose.foundation.Image
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.Checkbox
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FloatingActionButton
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Scaffold
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
import uz.vijdon.operator.data.api.BalanceLogEntryDto
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.data.api.TopupDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.Pill
import uz.vijdon.operator.ui.theme.TabHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

@Composable
fun BalanceScreen(onOpenDriver: (Int) -> Unit, viewModel: BalanceViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var showRecharge by remember { mutableStateOf(false) }

    Scaffold(
        containerColor = VijdonColors.Background,
        floatingActionButton = {
            FloatingActionButton(onClick = { showRecharge = true }, containerColor = VijdonColors.Blue, contentColor = VijdonColors.TextOnBlue) {
                Icon(Icons.Rounded.Add, contentDescription = "Balans qo'shish/ayirish")
            }
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).background(VijdonColors.Background)) {
            Column(modifier = Modifier.padding(16.dp)) {
                TabHeader(title = "Balans")
                Spacer(Modifier.height(12.dp))
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    SegChip("So'rovlar (${state.pendingCount})", selected = state.tab == 0) { viewModel.selectTab(0) }
                    SegChip("Tarix", selected = state.tab == 1) { viewModel.selectTab(1) }
                }
            }

            when {
                state.loading && state.topups.isEmpty() && state.tab == 0 -> CenteredLoading()
                state.error != null -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
                state.tab == 0 -> TopupsList(state.topups, onResolve = viewModel::resolveTopup, onOpenDriver = onOpenDriver)
                else -> LogList(state.log, hasNext = state.logHasNext, onLoadMore = viewModel::loadMoreLog, onOpenDriver = onOpenDriver)
            }
        }
    }

    if (showRecharge) {
        RechargeDialog(
            drivers = state.drivers,
            loading = state.actionLoading,
            onDismiss = { showRecharge = false },
            onConfirm = { driverId, amount, deduct, note -> viewModel.recharge(driverId, amount, deduct, note) { showRecharge = false } },
        )
    }
}

@Composable
private fun SegChip(label: String, selected: Boolean, onClick: () -> Unit) {
    Text(
        label,
        color = if (selected) VijdonColors.TextOnBlue else VijdonColors.TextSecondary,
        style = MaterialTheme.typography.labelMedium,
        modifier = Modifier
            .background(if (selected) VijdonColors.Blue else VijdonColors.BadgeNeutral, CardShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 16.dp, vertical = 8.dp),
    )
}

@Composable
private fun TopupsList(topups: List<TopupDto>, onResolve: (Int, Boolean, String) -> Unit, onOpenDriver: (Int) -> Unit) {
    if (topups.isEmpty()) {
        Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
            Text("Kutilayotgan to'lov so'rovi yo'q", color = VijdonColors.TextSecondary)
        }
        return
    }
    LazyColumn(contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        items(topups, key = { it.id }) { t -> TopupCard(t, onResolve, onOpenDriver) }
        item { Spacer(Modifier.height(80.dp)) }
    }
}

@Composable
private fun TopupCard(t: TopupDto, onResolve: (Int, Boolean, String) -> Unit, onOpenDriver: (Int) -> Unit) {
    var rejecting by remember { mutableStateOf(false) }
    var reason by remember { mutableStateOf("") }

    Column(modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).padding(14.dp)) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text(t.driver_name, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary, modifier = Modifier.clickable { onOpenDriver(t.driver_id) })
            Text("${formatMoney(t.amount)} so'm", color = VijdonColors.Green, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold))
        }
        Text(t.driver_phone, style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
        if (!rejecting) {
            Spacer(Modifier.height(10.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Button(
                    onClick = { onResolve(t.id, true, "") },
                    colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Green, contentColor = androidx.compose.ui.graphics.Color.White),
                    modifier = Modifier.weight(1f),
                ) { Text("Tasdiqlash") }
                OutlinedButton(onClick = { rejecting = true }, modifier = Modifier.weight(1f)) { Text("Rad etish") }
            }
        } else {
            Spacer(Modifier.height(10.dp))
            OutlinedTextField(value = reason, onValueChange = { reason = it }, placeholder = { Text("Rad etish sababi (ixtiyoriy)") }, modifier = Modifier.fillMaxWidth())
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { rejecting = false }, modifier = Modifier.weight(1f)) { Text("Bekor qilish") }
                Button(
                    onClick = { onResolve(t.id, false, reason) },
                    colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Red),
                    modifier = Modifier.weight(1f),
                ) { Text("Rad etish", color = androidx.compose.ui.graphics.Color.White) }
            }
        }
    }
}

@Composable
private fun LogList(log: List<BalanceLogEntryDto>, hasNext: Boolean, onLoadMore: () -> Unit, onOpenDriver: (Int) -> Unit) {
    LazyColumn(contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
        items(log, key = { it.id }) { entry ->
            Row(
                modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).clickable { onOpenDriver(entry.driver_id) }.padding(12.dp),
                horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically,
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(entry.driver_name, style = MaterialTheme.typography.bodyMedium, color = VijdonColors.TextPrimary)
                    if (entry.note.isNotBlank()) Text(entry.note, style = MaterialTheme.typography.labelSmall, color = VijdonColors.TextSecondary, maxLines = 1)
                }
                Text(
                    "${if (entry.isIncome) "+" else "-"}${formatMoney(entry.amount)}",
                    color = if (entry.isIncome) VijdonColors.Green else VijdonColors.Red,
                    style = MaterialTheme.typography.bodyMedium.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
        if (hasNext) {
            item {
                TextButton(onClick = onLoadMore, modifier = Modifier.fillMaxWidth()) { Text("Ko'proq yuklash", color = VijdonColors.Blue) }
            }
        }
        item { Spacer(Modifier.height(80.dp)) }
    }
}

@Composable
private fun RechargeDialog(
    drivers: List<DriverDto>,
    loading: Boolean,
    onDismiss: () -> Unit,
    onConfirm: (Int, String, Boolean, String) -> Unit,
) {
    var driverId by remember { mutableStateOf<Int?>(null) }
    var amount by remember { mutableStateOf("") }
    var deduct by remember { mutableStateOf(false) }
    var note by remember { mutableStateOf("") }
    var expanded by remember { mutableStateOf(false) }

    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Balans qo'shish/ayirish") },
        text = {
            Column {
                Box {
                    OutlinedButton(onClick = { expanded = true }, modifier = Modifier.fillMaxWidth()) {
                        Text(drivers.find { it.id == driverId }?.full_name ?: "Haydovchini tanlang")
                    }
                    DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                        drivers.forEach { d ->
                            DropdownMenuItem(text = { Text(d.full_name) }, onClick = { driverId = d.id; expanded = false })
                        }
                    }
                }
                Spacer(Modifier.height(10.dp))
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
            TextButton(
                onClick = { driverId?.let { onConfirm(it, amount, deduct, note) } },
                enabled = !loading && driverId != null && amount.isNotBlank(),
            ) { Text("Saqlash") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Bekor qilish") } },
    )
}
