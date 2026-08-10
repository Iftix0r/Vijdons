package uz.vijdon.driver.ui.home

import android.Manifest
import android.content.Intent
import android.net.Uri
import android.os.Build
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.background
import androidx.compose.foundation.border
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
import androidx.compose.material.icons.automirrored.rounded.Message
import androidx.compose.material.icons.rounded.CreditCard
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.ExpandLess
import androidx.compose.material.icons.rounded.ExpandMore
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

@Composable
fun HomeScreen(
    driver: DriverDto,
    onLogout: () -> Unit,
    onOpenRating: () -> Unit,
    onOpenBalance: () -> Unit,
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
            distanceM = state.orderDistancesM[alertOrder.id],
            onAccept = { viewModel.acceptOrder(alertOrder.id) },
            onReject = { viewModel.rejectOrder(alertOrder.id) },
        )
        return
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        TopBar(rank = state.rank, balance = currentDriver.balance, onOpenRating = onOpenRating, onOpenBalance = onOpenBalance)

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

        val todayEarned = state.todayEarned
        if (todayEarned != null) {
            TodayStatsBar(
                earned = todayEarned,
                trips = state.todayTrips ?: 0,
                expanded = state.todayStatsExpanded,
                onToggle = { viewModel.toggleTodayStats() },
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
            ErrorBanner(it, modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
        }

        if (!currentDriver.is_on_duty) {
            // Oflaynda haydovchiga buyurtma/manzil ro'yxati emas — chunki
            // ular baribir unga tegishli emas — balki onlayn bo'lishga
            // undovchi chaqiruv ko'rsatiladi. Bugungi statistika (yuqoridagi
            // TodayStatsBar) baribir onlayn/oflaynligidan qat'i nazar ko'rinadi.
            OfflineCallToAction(onGoOnline = { viewModel.toggleDuty() })
        } else if (state.loading && state.orders.isEmpty() && state.addresses.isEmpty()) {
            CenteredLoading()
        } else if (state.orders.isEmpty() && state.addresses.isEmpty()) {
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
            val sortedAddresses = remember(state.addresses, state.addressDistancesM) {
                state.addresses.sortedBy { state.addressDistancesM[it.id] ?: Double.MAX_VALUE }
            }
            val nearestId = sortedAddresses.firstOrNull()?.let { addr ->
                state.addressDistancesM[addr.id]?.takeIf { it <= 1000.0 }?.let { addr.id }
            }
            LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                items(state.orders, key = { "order-${it.id}" }) { order ->
                    Column(Modifier.animateItem()) {
                        OrderCard(
                            order = order,
                            operatorPhone = state.operatorPhone,
                            distanceM = state.orderDistancesM[order.id],
                            inProgress = order.id in state.actionInProgress,
                            onAccept = { viewModel.acceptOrder(order.id) },
                            onReject = { viewModel.rejectOrder(order.id) },
                            onWay = { viewModel.orderOnWay(order.id) },
                            onArrived = { viewModel.orderArrived(order.id) },
                            onComplete = { viewModel.orderComplete(order.id) },
                            onCallOperator = {
                                context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${state.operatorPhone}")))
                            },
                            onCallClient = {
                                context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${order.client_phone}")))
                            },
                            onQuickMessage = { message ->
                                val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:${order.client_phone}"))
                                intent.putExtra("sms_body", message)
                                context.startActivity(intent)
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
                    items(sortedAddresses, key = { "addr-${it.id}" }) { address ->
                        Column(Modifier.animateItem()) {
                            HomeAddressRow(
                                address = address,
                                distanceM = state.addressDistancesM[address.id],
                                isNearest = address.id == nearestId,
                                expanded = state.expandedAddressId == address.id,
                                queuePosition = state.queuePosition,
                                queueDrivers = state.queueDrivers,
                                queueLoading = state.queueLoading,
                                onToggleExpand = { viewModel.toggleAddressExpand(address) },
                            )
                            Spacer(Modifier.height(10.dp))
                        }
                    }
                }
            }
        }
    }
}

/** Haydovchi oflaynda bo'lganda Bosh sahifaning asosiy qismi — buyurtma va
 * manzil ro'yxati o'rniga, onlayn bo'lishga undovchi katta chaqiruv. */
@Composable
private fun OfflineCallToAction(onGoOnline: () -> Unit) {
    Box(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier.size(88.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.LocalTaxi, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(40.dp))
            }
            Spacer(Modifier.height(20.dp))
            Text(
                "Siz hozir oflaynsiz",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Yangi buyurtmalar va yaqin manzillardagi navbatni ko'rish uchun onlayn bo'ling",
                color = VijdonColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(20.dp))
            Button(
                onClick = onGoOnline,
                colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
                modifier = Modifier.height(48.dp),
            ) {
                Text("Onlayn bo'lish")
            }
        }
    }
}

@Composable
private fun HomeAddressRow(
    address: AddressDto,
    distanceM: Double?,
    isNearest: Boolean,
    expanded: Boolean,
    queuePosition: Int?,
    queueDrivers: List<QueueDriverDto>,
    queueLoading: Boolean,
    onToggleExpand: () -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .let { if (isNearest) it.border(2.dp, VijdonColors.Yellow, CardShape) else it }
            .background(VijdonColors.Surface, CardShape)
            .padding(14.dp),
    ) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
                Box(
                    modifier = Modifier.size(36.dp).background(if (isNearest) VijdonColors.Yellow else VijdonColors.BadgeNeutral, CircleShape),
                    contentAlignment = Alignment.Center,
                ) {
                    Icon(
                        Icons.Rounded.LocationOn, contentDescription = null,
                        tint = if (isNearest) VijdonColors.TextOnYellow else VijdonColors.Red,
                        modifier = Modifier.size(18.dp),
                    )
                }
                Spacer(Modifier.width(10.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleSmall, maxLines = 1)
                    Text(
                        if (distanceM != null) formatDistanceM(distanceM) + if (isNearest) " · eng yaqin" else "" else "Masofa noma'lum",
                        color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall,
                    )
                }
            }
            Spacer(Modifier.width(8.dp))
            Column(horizontalAlignment = Alignment.End) {
                if (isNearest && queuePosition != null) {
                    Pill("Siz: $queuePosition-o'rin", color = VijdonColors.TextOnYellow, background = VijdonColors.Yellow)
                    Spacer(Modifier.height(4.dp))
                }
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Pill(
                        "${address.queue_count} navbatda",
                        color = if (address.queue_count > 0) VijdonColors.Green else VijdonColors.TextSecondary,
                    )
                    if (address.queue_count > 0) {
                        IconButton(onClick = onToggleExpand, modifier = Modifier.size(28.dp)) {
                            Icon(
                                if (expanded) Icons.Rounded.ExpandLess else Icons.Rounded.ExpandMore,
                                contentDescription = if (expanded) "Yopish" else "Navbatni ko'rish",
                                tint = VijdonColors.TextSecondary,
                            )
                        }
                    }
                }
                Text("${address.today_orders} ta bugun", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            }
        }

        if (expanded) {
            Spacer(Modifier.height(10.dp))
            HorizontalDivider(color = VijdonColors.Border)
            Spacer(Modifier.height(10.dp))
            if (queueLoading) {
                CircularProgressIndicator(modifier = Modifier.size(20.dp), color = VijdonColors.Yellow, strokeWidth = 2.dp)
            } else if (queueDrivers.isEmpty()) {
                Text("Navbatda hech kim yo'q", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            } else {
                queueDrivers.forEach { d -> QueueDriverRow(d) }
            }
        }
    }
}

@Composable
private fun QueueDriverRow(d: QueueDriverDto) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(
                modifier = Modifier.size(22.dp).background(if (d.is_me) VijdonColors.Yellow else VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(d.position.toString(), color = if (d.is_me) VijdonColors.TextOnYellow else VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
            }
            Spacer(Modifier.width(8.dp))
            Text(
                d.full_name + if (d.is_me) " (Siz)" else "",
                color = if (d.is_me) VijdonColors.Yellow else VijdonColors.TextPrimary,
                style = MaterialTheme.typography.bodySmall,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
                modifier = Modifier.weight(1f, fill = false),
            )
        }
        Text(d.joined_at.takeLastWhile { it != 'T' }.take(5), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
    }
}

internal fun formatDistanceM(m: Double): String =
    if (m < 1000) "${m.toInt()} m" else "%.1f km".format(m / 1000)

/** Yandex Pro'dagi "3 km - 5 daqiqa" formatiga o'xshash — shahar ichi
 * o'rtacha tezlik (~28 km/soat) asosida taxminiy vaqt. */
internal fun formatDistanceEta(m: Double): String {
    val etaMin = (m / 1000.0 / 28.0 * 60.0).toInt().coerceAtLeast(1)
    return "${formatDistanceM(m)} · $etaMin daqiqa"
}

@Composable
private fun TodayStatsBar(earned: Double, trips: Int, expanded: Boolean, onToggle: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 4.dp)
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clip(CardShape)
            .clickable(onClick = onToggle)
            .padding(horizontal = 16.dp, vertical = if (expanded) 14.dp else 10.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("Bugungi daromad", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
            Icon(
                if (expanded) Icons.Rounded.ExpandLess else Icons.Rounded.ExpandMore,
                contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(18.dp),
            )
        }
        if (expanded) {
            Spacer(Modifier.height(6.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(20.dp)) {
                Column {
                    Text("${earned.toInt()} so'm", color = VijdonColors.Green, style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.Bold))
                    Text("Daromad", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
                }
                Column {
                    Text(trips.toString(), color = VijdonColors.Yellow, style = MaterialTheme.typography.headlineSmall)
                    Text("Safar", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
                }
            }
        } else {
            Text("${earned.toInt()} so'm · $trips safar", color = VijdonColors.Green, style = MaterialTheme.typography.titleSmall)
        }
    }
}

/** Web'dagi rangi: 1-o'rin — oltin, 2-3-o'rin — apelsin, qolganlari — kulrang. */
private fun rankIconColor(rank: Int?): Color = when {
    rank == 1 -> VijdonColors.Yellow
    rank != null && rank <= 3 -> Color(0xFFFF9500)
    else -> Color(0xFF8E8E93)
}

@Composable
private fun TopBar(rank: Int?, balance: String, onOpenRating: () -> Unit, onOpenBalance: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(16.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Surface(
            shape = CircleShape,
            color = VijdonColors.Glass,
            shadowElevation = 4.dp,
            onClick = onOpenRating,
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = rankIconColor(rank), modifier = Modifier.size(15.dp))
                Spacer(Modifier.width(6.dp))
                Text(
                    if (rank != null) "$rank-o'rin" else "—",
                    color = VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
        Surface(
            shape = CircleShape,
            color = VijdonColors.Glass,
            shadowElevation = 4.dp,
            onClick = onOpenBalance,
        ) {
            Row(
                modifier = Modifier.padding(horizontal = 14.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.CreditCard, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(15.dp))
                Spacer(Modifier.width(6.dp))
                Text(
                    "$balance so'm",
                    color = VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
    }
}

/** Yandex Pro'dagi tayyor shablon xabarlar — holatga qarab mos xabar. */
private fun quickMessageFor(order: OrderDto): String? = when {
    order.isAccepted -> "Assalomu alaykum, men sizga yo'lga chiqdim."
    order.isOnWay -> "Bir necha daqiqada yetib boraman."
    order.isArrived -> "Men yetib keldim, sizni kutyapman."
    else -> null
}

@Composable
private fun OrderCard(
    order: OrderDto,
    operatorPhone: String,
    distanceM: Double?,
    inProgress: Boolean,
    onAccept: () -> Unit,
    onReject: () -> Unit,
    onWay: () -> Unit,
    onArrived: () -> Unit,
    onComplete: () -> Unit,
    onCallOperator: () -> Unit,
    onCallClient: () -> Unit,
    onQuickMessage: (String) -> Unit,
) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .padding(16.dp),
    ) {
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            Pill(order.status_label, color = VijdonColors.Green, background = VijdonColors.BadgeNeutral)
            // Yandex Pro'dagi "Offer" ekranidagi kabi — mijozgacha bo'lgan
            // masofa va taxminiy vaqt, faqat hali yetib borilmagan bo'lsa.
            if (distanceM != null && (order.isPending || order.isAccepted)) {
                Text(formatDistanceEta(distanceM), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
            }
        }
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
        order.price?.let { Text("$it so'm", color = VijdonColors.Green, style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.ExtraBold)) }

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
        // Mijozga tezkor aloqa — qo'ng'iroq va tayyor shablon xabar
        // (Yandex Pro'dagi "Men yetib keldim" / "Sizni kutyapman" kabi).
        if (order.isAccepted || order.isOnWay || order.isArrived) {
            Spacer(Modifier.height(8.dp))
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                IconTextButton(Icons.Rounded.Phone, "Qo'ng'iroq", onCallClient)
                quickMessageFor(order)?.let { message ->
                    IconTextButton(Icons.AutoMirrored.Rounded.Message, "Xabar") { onQuickMessage(message) }
                }
            }
        }
    }
}

@Composable
private fun IconTextButton(icon: ImageVector, text: String, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextSecondary),
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(6.dp))
        Text(text, style = MaterialTheme.typography.labelMedium)
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
