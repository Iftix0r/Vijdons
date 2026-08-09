package uz.vijdon.driver.ui.home

import android.Manifest
import android.content.Intent
import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
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
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.CreditCard
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
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
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun HomeScreen(
    driver: DriverDto,
    onLogout: () -> Unit,
    onOpenRating: () -> Unit,
    viewModel: HomeViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()
    val context = LocalContext.current

    LaunchedEffect(driver) { viewModel.setDriver(driver) }

    val locationPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
    }

    val currentDriver = state.driver ?: driver

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        TopBar(rank = state.rank, balance = currentDriver.balance, onOpenRating = onOpenRating)

        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                if (currentDriver.is_on_duty) "Onlayn" else "Oflayn",
                color = if (currentDriver.is_on_duty) VijdonColors.Green else VijdonColors.TextSecondary,
            )
            Switch(
                checked = currentDriver.is_on_duty,
                onCheckedChange = { viewModel.toggleDuty() },
                colors = SwitchDefaults.colors(checkedTrackColor = VijdonColors.Green, checkedThumbColor = VijdonColors.TextPrimary),
            )
        }

        if (state.lowBalance) {
            Text(
                "Balansingiz kam — buyurtma qabul qilish uchun to'ldiring",
                color = VijdonColors.Red,
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 4.dp),
            )
        }
        state.error?.let {
            Text(it, color = VijdonColors.Red, modifier = Modifier.padding(horizontal = 16.dp))
        }

        if (state.orders.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Icon(Icons.Rounded.LocalTaxi, contentDescription = null, tint = VijdonColors.Border, modifier = Modifier.size(48.dp))
                    Spacer(Modifier.height(8.dp))
                    Text("Hozircha buyurtma yo'q", color = VijdonColors.TextSecondary)
                }
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
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
                    Spacer(Modifier.height(10.dp))
                }
            }
        }
    }
}

@Composable
private fun TopBar(rank: Int?, balance: String, onOpenRating: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(
            modifier = Modifier
                .background(VijdonColors.BadgeNeutral, CircleShape)
                .clickable(onClick = onOpenRating)
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = VijdonColors.Yellow, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(6.dp))
            Text(if (rank != null) "$rank-o'rin" else "—", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.labelLarge)
        }
        Row(
            modifier = Modifier
                .background(VijdonColors.BadgeNeutral, CircleShape)
                .padding(horizontal = 14.dp, vertical = 10.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Icon(Icons.Rounded.CreditCard, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(18.dp))
            Spacer(Modifier.width(6.dp))
            Text("$balance so'm", color = VijdonColors.Green, style = MaterialTheme.typography.labelLarge)
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
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.Surface, CardShape)
            .padding(16.dp),
    ) {
        Pill(order.status_label, color = VijdonColors.Green, background = VijdonColors.BadgeNeutral)
        Spacer(Modifier.height(8.dp))
        Text("Qayerdan: ${order.from_address}", color = VijdonColors.TextPrimary)
        if (order.to_address.isNotBlank()) {
            Text("Qayerga: ${order.to_address}", color = VijdonColors.TextPrimary)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.Phone, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text("${order.client_name} · ${order.client_phone}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }
        order.price?.let { Text("$it so'm", color = VijdonColors.Green, style = MaterialTheme.typography.titleMedium) }
        order.timer_sec?.let { Text("Qolgan vaqt: ${it}s", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall) }

        Spacer(Modifier.height(12.dp))
        if (inProgress) {
            CircularProgressIndicator(modifier = Modifier.height(20.dp), color = VijdonColors.Yellow)
            return@Column
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            when {
                order.isPending -> {
                    YellowButton("Qabul qilish", onAccept)
                    OutlineButton("Rad etish", onReject)
                }
                order.isAccepted -> {
                    YellowButton("Yo'lga chiqdim", onWay)
                    OutlineButton("Operator", onCallOperator)
                }
                order.isOnWay -> {
                    YellowButton("Yetib keldim", onArrived)
                    OutlineButton("Operator", onCallOperator)
                }
                order.isArrived -> {
                    YellowButton("Yakunlash", onComplete)
                    OutlineButton("Operator", onCallOperator)
                }
            }
        }
    }
}

@Composable
private fun YellowButton(text: String, onClick: () -> Unit) {
    Button(
        onClick = onClick,
        colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
    ) { Text(text) }
}

@Composable
private fun OutlineButton(text: String, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextPrimary),
    ) { Text(text) }
}
