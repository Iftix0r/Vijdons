package uz.vijdon.driver.ui.home

import android.Manifest
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun HomeScreen(driver: DriverDto, onLogout: () -> Unit, viewModel: HomeViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(driver) { viewModel.setDriver(driver) }

    val locationPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    Scaffold(
        topBar = {
            TopAppBar(
                title = { Text("Vijdon Taxi") },
                actions = {
                    TextButton(onClick = onLogout) { Text("Chiqish") }
                },
            )
        },
    ) { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding)) {
            DriverStatusBar(state.driver ?: driver, onToggleDuty = viewModel::toggleDuty)

            if (state.lowBalance) {
                Text(
                    "Balansingiz kam — buyurtma qabul qilish uchun to'ldiring",
                    color = MaterialTheme.colorScheme.error,
                    modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
                )
            }
            state.error?.let {
                Text(it, color = MaterialTheme.colorScheme.error, modifier = Modifier.padding(horizontal = 16.dp))
            }

            if (state.orders.isEmpty()) {
                Column(
                    modifier = Modifier.fillMaxSize(),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally,
                ) {
                    Text("Hozircha buyurtma yo'q", style = MaterialTheme.typography.bodyLarge)
                }
            } else {
                LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 12.dp)) {
                    items(state.orders, key = { it.id }) { order ->
                        OrderCard(
                            order = order,
                            operatorPhone = state.operatorPhone,
                            inProgress = order.id in state.actionInProgress,
                            onAccept = { viewModel.acceptOrder(order.id) },
                            onReject = { viewModel.rejectOrder(order.id) },
                            onWay = { viewModel.orderOnWay(order.id) },
                            onArrived = { viewModel.orderArrived(order.id) },
                            onComplete = { viewModel.orderComplete(order.id) },
                            onCallOperator = {
                                context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${state.operatorPhone}")))
                            },
                        )
                        Spacer(Modifier.height(8.dp))
                    }
                }
            }
        }
    }
}

@Composable
private fun DriverStatusBar(driver: DriverDto, onToggleDuty: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Column {
            Text(driver.full_name, style = MaterialTheme.typography.titleMedium)
            Text("Balans: ${driver.balance} so'm", style = MaterialTheme.typography.bodyMedium)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Text(if (driver.is_on_duty) "Onlayn" else "Oflayn")
            Switch(checked = driver.is_on_duty, onCheckedChange = { onToggleDuty() })
        }
    }
}

@Composable
private fun OrderCard(
    order: OrderDto,
    operatorPhone: String,
    inProgress: Boolean,
    onAccept: () -> Unit,
    onReject: () -> Unit,
    onWay: () -> Unit,
    onArrived: () -> Unit,
    onComplete: () -> Unit,
    onCallOperator: () -> Unit,
) {
    Card(modifier = Modifier.fillMaxWidth()) {
        Column(modifier = Modifier.padding(16.dp)) {
            Text(order.status_label, style = MaterialTheme.typography.labelLarge, color = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.height(4.dp))
            Text("Qayerdan: ${order.from_address}", style = MaterialTheme.typography.bodyMedium)
            if (order.to_address.isNotBlank()) {
                Text("Qayerga: ${order.to_address}", style = MaterialTheme.typography.bodyMedium)
            }
            Text("${order.client_name} · ${order.client_phone}", style = MaterialTheme.typography.bodySmall)
            order.price?.let { Text("Narx: $it so'm", style = MaterialTheme.typography.bodySmall) }
            order.timer_sec?.let { Text("Qolgan vaqt: ${it}s", style = MaterialTheme.typography.bodySmall) }

            Spacer(Modifier.height(12.dp))
            if (inProgress) {
                CircularProgressIndicator(modifier = Modifier.height(20.dp))
                return@Column
            }
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                when {
                    order.isPending -> {
                        Button(onClick = onAccept) { Text("Qabul qilish") }
                        OutlinedButton(onClick = onReject) { Text("Rad etish") }
                    }
                    order.isAccepted -> {
                        Button(onClick = onWay) { Text("Yo'lga chiqdim") }
                        OutlinedButton(onClick = onCallOperator) { Text("Operator") }
                    }
                    order.isOnWay -> {
                        Button(onClick = onArrived) { Text("Yetib keldim") }
                        OutlinedButton(onClick = onCallOperator) { Text("Operator") }
                    }
                    order.isArrived -> {
                        Button(onClick = onComplete) { Text("Yakunlash") }
                        OutlinedButton(onClick = onCallOperator) { Text("Operator") }
                    }
                }
            }
        }
    }
}
