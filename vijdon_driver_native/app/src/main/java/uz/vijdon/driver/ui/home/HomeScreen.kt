package uz.vijdon.driver.ui.home

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
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
import androidx.compose.material.icons.rounded.LocationOn
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
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

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

    val locationPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
        if (granted) viewModel.onLocationPermissionGranted()
    }
    // POST_NOTIFICATIONS Android 13+ da runtime ruxsat — bu so'ralmasa, yangi
    // buyurtma push xabari kabi muhim bildirishnomalar hech qanday xato
    // bermasdan, sezilmasdan ko'rsatilmay qoladi.
    val notificationPermissionLauncher = rememberLauncherForActivityResult(ActivityResultContracts.RequestPermission()) {}
    LaunchedEffect(Unit) {
        locationPermissionLauncher.launch(Manifest.permission.ACCESS_FINE_LOCATION)
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            notificationPermissionLauncher.launch(Manifest.permission.POST_NOTIFICATIONS)
        }
    }

    val currentDriver = state.driver ?: driver

    val alertOrder = state.alertOrder
    if (alertOrder != null) {
        IncomingOrderOverlay(
            order = alertOrder,
            totalSec = state.alertTotalSec,
            onAccept = { viewModel.acceptOrder(alertOrder.id) },
            onReject = { viewModel.rejectOrder(alertOrder.id) },
        )
        return
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        TopBar(rank = state.rank, balance = currentDriver.balance, onOpenRating = onOpenRating)

        Row(
            modifier = Modifier
                .fillMaxWidth()
                .padding(horizontal = 16.dp, vertical = 4.dp)
                .cardShadow()
                .background(VijdonColors.Surface, CardShape)
                .padding(horizontal = 16.dp, vertical = 14.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier
                        .size(10.dp)
                        .background(if (currentDriver.is_on_duty) VijdonColors.Green else VijdonColors.TextSecondary, CircleShape),
                )
                Spacer(Modifier.width(8.dp))
                Text(
                    if (currentDriver.is_on_duty) "Onlayn" else "Oflayn",
                    color = if (currentDriver.is_on_duty) VijdonColors.Green else VijdonColors.TextSecondary,
                    style = MaterialTheme.typography.titleSmall,
                )
            }
            Switch(
                checked = currentDriver.is_on_duty,
                onCheckedChange = { viewModel.toggleDuty() },
                colors = SwitchDefaults.colors(checkedTrackColor = VijdonColors.Green, checkedThumbColor = VijdonColors.TextPrimary),
            )
        }

        if (state.lowBalance) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .padding(horizontal = 16.dp, vertical = 6.dp)
                    .background(VijdonColors.Red.copy(alpha = 0.12f), CardShape)
                    .padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.CreditCard, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
                Spacer(Modifier.width(8.dp))
                Text(
                    "Balansingiz kam — buyurtma qabul qilish uchun to'ldiring",
                    color = VijdonColors.Red,
                    style = MaterialTheme.typography.bodySmall,
                )
            }
        }
        state.error?.let {
            Text(it, color = VijdonColors.Red, modifier = Modifier.padding(horizontal = 16.dp))
        }

        if (state.orders.isEmpty() && state.addresses.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Column(horizontalAlignment = Alignment.CenterHorizontally) {
                    Box(
                        modifier = Modifier.size(72.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                        contentAlignment = Alignment.Center,
                    ) {
                        Icon(Icons.Rounded.LocalTaxi, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(32.dp))
                    }
                    Spacer(Modifier.height(12.dp))
                    Text("Hozircha buyurtma yo'q", color = VijdonColors.TextSecondary)
                }
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                items(state.orders, key = { "order-${it.id}" }) { order ->
                    Column(Modifier.animateItem()) {
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
                // Veb panelda "Asosiy" sahifaning fon kontenti — qaysi
                // manzillarda hozir talab (navbatdagi haydovchilar, bugungi
                // buyurtmalar) borligini ko'rsatadi, buyurtma bo'lmaganda ham.
                if (state.addresses.isNotEmpty()) {
                    item {
                        Text(
                            "Yaqin manzillar",
                            color = VijdonColors.TextSecondary,
                            style = MaterialTheme.typography.labelLarge,
                            modifier = Modifier.padding(top = if (state.orders.isNotEmpty()) 4.dp else 0.dp, bottom = 8.dp),
                        )
                    }
                    items(state.addresses, key = { "addr-${it.id}" }) { address ->
                        Column(Modifier.animateItem()) {
                            HomeAddressRow(address)
                            Spacer(Modifier.height(10.dp))
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun HomeAddressRow(address: AddressDto) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(36.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.LocationOn, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(10.dp))
            Column {
                Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall)
                Text("Bugun: ${address.today_orders} buyurtma", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        Pill(
            "${address.queue_count} navbatda",
            color = if (address.queue_count > 0) VijdonColors.Green else VijdonColors.TextSecondary,
        )
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
                .cardShadow(shape = CircleShape, elevation = 4.dp)
                .background(VijdonColors.BadgeNeutral.copy(alpha = 0.92f), CircleShape)
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
                .cardShadow(shape = CircleShape, elevation = 4.dp)
                .background(VijdonColors.BadgeNeutral.copy(alpha = 0.92f), CircleShape)
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
            .cardShadow()
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
