package uz.vijdon.driver.ui.home

import android.Manifest
import android.app.NotificationManager
import android.content.Intent
import android.net.Uri
import android.os.Build
import android.provider.Settings
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.animation.core.RepeatMode
import androidx.compose.animation.core.animateFloat
import androidx.compose.animation.core.infiniteRepeatable
import androidx.compose.animation.core.rememberInfiniteTransition
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.border
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
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
import androidx.compose.material.icons.rounded.Close
import androidx.compose.material.icons.rounded.CreditCard
import androidx.compose.material.icons.rounded.EmojiEvents
import androidx.compose.material.icons.rounded.ExpandLess
import androidx.compose.material.icons.rounded.ExpandMore
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material.icons.rounded.NotificationsActive
import androidx.compose.material.icons.rounded.Pause
import androidx.compose.material.icons.rounded.Phone
import androidx.compose.material.icons.rounded.PlayArrow
import androidx.compose.material.icons.rounded.Route
import androidx.compose.material.icons.rounded.Speed
import androidx.compose.material.icons.rounded.Timer
import androidx.compose.material3.Button
import androidx.compose.material3.ButtonDefaults
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalBottomSheet
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.SwitchDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberModalBottomSheetState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.hapticfeedback.HapticFeedbackType
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.platform.LocalHapticFeedback
import androidx.compose.ui.platform.LocalLifecycleOwner
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import kotlinx.coroutines.delay
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.ui.orders.TaximeterTracker
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.RouteAddresses
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.formatMoney
import java.util.Locale

@OptIn(ExperimentalMaterial3Api::class)
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

    // Faol (qabul qilingan/yo'lda/yetib kelgan) buyurtma(lar) — veb'dagi
    // "#my-orders-btn" bilan bir xil: ro'yxatda to'liq karta sifatida
    // qotib turmasdan, tab-bar ustida suzuvchi Telegram mini-app uslubidagi
    // tugma orqali ko'rsatiladi, bosilganda pastdan karta ochiladi/yopiladi.
    var activeOrderSheetId by remember { mutableStateOf<Int?>(null) }
    var showActiveOrdersChooser by remember { mutableStateOf(false) }

    // Bildirishnomadagi "Qabul qilish" tugmasidan keyin (OpenOrderBus →
    // HomeViewModel.pendingOpenOrderId) — buyurtma `state.orders`da
    // ko'rinishi bilan (server javobi biroz kechikishi mumkin) uning
    // tafsilot oynasi avtomatik ochiladi.
    LaunchedEffect(state.pendingOpenOrderId, state.orders) {
        val pendingId = state.pendingOpenOrderId
        if (pendingId != null && state.orders.any { it.id == pendingId }) {
            activeOrderSheetId = pendingId
            viewModel.clearPendingOpenOrder()
        }
    }

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

    // Android 14+ da "to'liq ekranli bildirishnoma" (yangi buyurtma — ilova
    // fonda yoki ekran qulflangan bo'lsa ham boshqa ilovalar ustidan avtomatik
    // ochiladigan ogohlantirish) endi tizim tomonidan SUKUT BO'YICHA
    // O'CHIRILGAN — oddiy runtime ruxsat so'rovi bilan yoqib bo'lmaydi, faqat
    // qurilma Sozlamalaridan qo'lda yoqiladi. Shu sabab har safar ekranga
    // qaytilganda (masalan Sozlamalardan orqaga qaytgach) tekshirib, o'chiq
    // bo'lsa ogohlantiramiz — aks holda haydovchi ilovadan chiqib ketganda
    // yangi buyurtmalarni umuman ko'rmay qolishi mumkin.
    var fullScreenIntentMissing by remember { mutableStateOf(false) }
    // Bazaviy bildirishnoma ruxsatining o'zi (Android 13+) rad etilgan bo'lsa
    // — yuqoridagi to'liq ekranli sozlamadan ham oldinroq muammo: HECH QANDAY
    // (hatto oddiy) bildirishnoma chiqmaydi, aks holda soundless/sezilmasdan
    // yo'qolib ketardi. Birinchi so'rovda "Rad etish" bosilsa, tizim qayta
    // so'rov oynasini ko'rsatmaydi — shu sabab ekranga qaytilganda tekshirib,
    // hali ham yo'q bo'lsa Sozlamalarga yo'naltiruvchi banner ko'rsatiladi.
    var notificationPermissionMissing by remember { mutableStateOf(false) }
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
        val lifecycleOwner = LocalLifecycleOwner.current
        DisposableEffect(lifecycleOwner) {
            val observer = LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) {
                    notificationPermissionMissing = androidx.core.content.ContextCompat.checkSelfPermission(
                        context, Manifest.permission.POST_NOTIFICATIONS,
                    ) != android.content.pm.PackageManager.PERMISSION_GRANTED
                }
            }
            lifecycleOwner.lifecycle.addObserver(observer)
            onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
        }
    }
    if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.UPSIDE_DOWN_CAKE) {
        val lifecycleOwner = LocalLifecycleOwner.current
        DisposableEffect(lifecycleOwner) {
            val notificationManager = context.getSystemService(NotificationManager::class.java)
            val observer = LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) {
                    fullScreenIntentMissing = !notificationManager.canUseFullScreenIntent()
                }
            }
            lifecycleOwner.lifecycle.addObserver(observer)
            onDispose { lifecycleOwner.lifecycle.removeObserver(observer) }
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

    // Ro'yxat ko'rinadigan holatda ("else" tarmog'i) navbat almashtirgichi
    // endi tepada QOTIB QOLMAYDI — ro'yxat bilan birga LazyColumn ichida
    // birinchi element sifatida suriladi. Boshqa holatlarda (yuklanmoqda,
    // bo'sh, oflayn) suriladigan hech narsa yo'q, shu sabab tepada qoladi.
    val showListBranch = currentDriver.is_on_duty && (state.orders.isNotEmpty() || state.addresses.isNotEmpty())

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        // Vaqtincha OLIB TASHLANDI — status-bar zonasidagi vizual muammoni
        // (Reyting/Balans tugmalari bilan bog'liq) alohida tekshirish uchun.
        // Qayta yoqish uchun quyidagi qatorni oching.
        // TopBar(rank = state.rank, balance = currentDriver.balance, onOpenRating = onOpenRating, onOpenBalance = onOpenBalance)

        if (notificationPermissionMissing) {
            NotificationPermissionBanner(
                onEnable = {
                    context.startActivity(
                        Intent(Settings.ACTION_APP_NOTIFICATION_SETTINGS)
                            .putExtra(Settings.EXTRA_APP_PACKAGE, context.packageName),
                    )
                },
            )
        } else if (fullScreenIntentMissing) {
            FullScreenIntentBanner(
                onEnable = {
                    context.startActivity(
                        Intent(Settings.ACTION_MANAGE_APP_USE_FULL_SCREEN_INTENT, Uri.parse("package:${context.packageName}")),
                    )
                },
            )
        }

        if (!showListBranch) {
            DutyToggleRow(isOnDuty = currentDriver.is_on_duty, onToggle = { viewModel.toggleDuty() })
        }

        state.surgeMultiplier?.let { multiplier ->
            SurgeBanner(multiplier = multiplier, reason = state.surgeReason)
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
            // undovchi chaqiruv ko'rsatiladi.
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
            // Faol buyurtmalar ro'yxatdan olib tashlanadi — ular endi pastdagi
            // suzuvchi tugma orqali ko'rsatiladi (pastga qarang).
            val pendingOrders = remember(state.orders) { state.orders.filter { it.isPending } }
            val activeOrders = remember(state.orders) { state.orders.filter { it.isActive } }

            Box(modifier = Modifier.fillMaxSize()) {
                LazyColumn(modifier = Modifier.fillMaxSize().padding(horizontal = 16.dp)) {
                    item {
                        Column {
                            Spacer(Modifier.height(4.dp))
                            DutyToggleRow(isOnDuty = currentDriver.is_on_duty, onToggle = { viewModel.toggleDuty() }, horizontalPadding = 0.dp)
                            Spacer(Modifier.height(10.dp))
                        }
                    }
                    items(pendingOrders, key = { "order-${it.id}" }) { order ->
                        Column(Modifier.animateItem()) {
                            OrderCard(
                                order = order,
                                distanceM = state.orderDistancesM[order.id],
                                inProgress = order.id in state.actionInProgress,
                                onAccept = { viewModel.acceptOrder(order.id) },
                                onReject = { viewModel.rejectOrder(order.id) },
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
                                modifier = Modifier.padding(top = if (pendingOrders.isNotEmpty()) 4.dp else 0.dp, bottom = 8.dp),
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
                    item { Spacer(Modifier.height(if (activeOrders.isNotEmpty()) 72.dp else 0.dp)) }
                }
                if (activeOrders.isNotEmpty()) {
                    // Yagona faol buyurtma yo'lda/yetib kelgan bo'lsa, tugmada
                    // ham jonli narx ko'rinadi — sheet ochilmasdan turib ham
                    // haydovchi hozirgi taxminiy summa qanchaligini bilib turadi.
                    val liveOrder = activeOrders.singleOrNull()?.takeIf { it.isOnWay || it.isArrived }
                    var barTick by remember(liveOrder?.id) { mutableStateOf(System.currentTimeMillis()) }
                    LaunchedEffect(liveOrder?.id) {
                        if (liveOrder != null) {
                            while (true) {
                                barTick = System.currentTimeMillis()
                                delay(1_000L)
                            }
                        }
                    }
                    val livePriceUzs = liveOrder?.let { viewModel.taximeterFor(it.id)?.priceUzs(barTick) }
                    ActiveOrdersBar(
                        activeOrders = activeOrders,
                        livePriceUzs = livePriceUzs,
                        onClick = {
                            if (activeOrders.size == 1) activeOrderSheetId = activeOrders[0].id
                            else showActiveOrdersChooser = true
                        },
                        modifier = Modifier.align(Alignment.BottomCenter),
                    )
                }
            }
        }
    }

    if (showActiveOrdersChooser) {
        val chooserSheetState = rememberModalBottomSheetState()
        ModalBottomSheet(onDismissRequest = { showActiveOrdersChooser = false }, sheetState = chooserSheetState) {
            Column(modifier = Modifier.padding(horizontal = 16.dp).padding(bottom = 24.dp)) {
                Text(
                    "Faol buyurtmalar",
                    color = VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                )
                Spacer(Modifier.height(12.dp))
                state.orders.filter { it.isActive }.forEach { order ->
                    ActiveOrderChooserRow(order) {
                        showActiveOrdersChooser = false
                        activeOrderSheetId = order.id
                    }
                    Spacer(Modifier.height(8.dp))
                }
            }
        }
    }

    val sheetOrder = state.orders.firstOrNull { it.id == activeOrderSheetId }
    if (sheetOrder != null) {
        // "Faol buyurtma" oynasi bo'sh joy qoldirmasdan butun ekranni
        // egallashi so'ralgan — shu sabab standart (yarim balandlikdagi,
        // kenglikka chegara qo'yadigan) bottom sheet o'rniga to'liq
        // kenglik/balandlikka cho'zilgan holatda ochiladi.
        val orderSheetState = rememberModalBottomSheetState(skipPartiallyExpanded = true)

        // Taximetr (VAQT/MASOFA/NARX) "Yo'lga chiqdim"dan keyin real vaqtda
        // yangilanib turishi kerak — GPS nuqtasi kelishini kutmasdan, har
        // soniyada o'zini qayta chizadi (VAQT sekundomeri GPS'ga bog'liq
        // emas, doim yurishi kerak).
        var meterTick by remember(sheetOrder.id) { mutableStateOf(System.currentTimeMillis()) }
        LaunchedEffect(sheetOrder.id, sheetOrder.status) {
            if (sheetOrder.isOnWay || sheetOrder.isArrived) {
                while (true) {
                    meterTick = System.currentTimeMillis()
                    delay(1_000L)
                }
            }
        }

        ModalBottomSheet(
            onDismissRequest = { activeOrderSheetId = null },
            sheetState = orderSheetState,
            sheetMaxWidth = Dp.Unspecified,
        ) {
            OrderDetailSheetContent(
                order = sheetOrder,
                operatorPhone = state.operatorPhone,
                distanceM = state.orderDistancesM[sheetOrder.id],
                inProgress = sheetOrder.id in state.actionInProgress,
                taximeter = viewModel.taximeterFor(sheetOrder.id),
                meterTick = meterTick,
                onToggleWaiting = { viewModel.toggleWaiting(sheetOrder.id) },
                onClose = { activeOrderSheetId = null },
                onAccept = { viewModel.acceptOrder(sheetOrder.id) },
                onReject = { viewModel.rejectOrder(sheetOrder.id) },
                onWay = { viewModel.orderOnWay(sheetOrder.id) },
                onArrived = { viewModel.orderArrived(sheetOrder.id) },
                onComplete = {
                    viewModel.orderComplete(sheetOrder.id)
                    activeOrderSheetId = null
                },
                onCallOperator = {
                    context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${state.operatorPhone}")))
                },
                onCallClient = {
                    context.startActivity(Intent(Intent.ACTION_DIAL, Uri.parse("tel:${sheetOrder.client_phone}")))
                },
                onQuickMessage = { message ->
                    val intent = Intent(Intent.ACTION_SENDTO, Uri.parse("smsto:${sheetOrder.client_phone}"))
                    intent.putExtra("sms_body", message)
                    context.startActivity(intent)
                },
            )
        }
    }
}

/**
 * Buyurtma tafsiloti — to'liq ekranli sheet uchun. `OrderCard`dan (ro'yxatdagi
 * ixcham karta) farqli — bu yerda ma'lumot (manzil, mijoz, narx) yuqorida
 * SKROLL bo'ladigan qismda, amal tugmalari ("Yo'lga chiqdim"/"Operator"/
 * "Xabar" va h.k.) esa pastda QOTIB turadi (ekran skroll qilinganda ham
 * doim ko'rinadi) — sahifa tarzida.
 */
@Composable
private fun OrderDetailSheetContent(
    order: OrderDto,
    operatorPhone: String,
    distanceM: Double?,
    inProgress: Boolean,
    taximeter: TaximeterTracker?,
    meterTick: Long,
    onToggleWaiting: () -> Unit,
    onClose: () -> Unit,
    onAccept: () -> Unit,
    onReject: () -> Unit,
    onWay: () -> Unit,
    onArrived: () -> Unit,
    onComplete: () -> Unit,
    onCallOperator: () -> Unit,
    onCallClient: () -> Unit,
    onQuickMessage: (String) -> Unit,
) {
    Column(modifier = Modifier.fillMaxSize()) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(start = 20.dp, end = 8.dp, top = 4.dp, bottom = 4.dp),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Text(
                "Buyurtma tafsiloti",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
            )
            IconButton(onClick = onClose) {
                Icon(Icons.Rounded.Close, contentDescription = "Yopish", tint = VijdonColors.TextSecondary)
            }
        }
        HorizontalDivider(color = VijdonColors.Border)

        Column(
            modifier = Modifier
                .weight(1f)
                .verticalScroll(rememberScrollState())
                .padding(horizontal = 20.dp, vertical = 16.dp),
        ) {
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Pill(order.status_label, color = VijdonColors.Green, background = VijdonColors.BadgeNeutral)
                if (distanceM != null && (order.isPending || order.isAccepted)) {
                    Text(formatDistanceEta(distanceM), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
                }
            }
            Spacer(Modifier.height(16.dp))
            RouteAddresses(order.from_address, order.to_address)
            Spacer(Modifier.height(16.dp))
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Rounded.Phone, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(14.dp))
                Spacer(Modifier.width(4.dp))
                Text("${order.client_name} · ${order.client_phone}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodyMedium)
            }

            // Taximetr — "Yo'lga chiqdim"dan "Yakunlash"gacha, real vaqtda
            // yangilanadigan masofa/vaqt/narx. Yakuniy haq shundan olinadi,
            // shu sabab buyurtma yaratilgandagi taxminiy narxdan alohida
            // va aniqroq ko'rinishda ko'rsatiladi.
            if ((order.isOnWay || order.isArrived) && taximeter != null) {
                Spacer(Modifier.height(16.dp))
                TaximeterCard(
                    distanceKm = taximeter.distanceKm,
                    elapsedMs = meterTick - taximeter.startedAtMs,
                    speedKmh = taximeter.speedKmh,
                    hasFix = taximeter.hasFix,
                    priceUzs = taximeter.priceUzs(meterTick),
                    isWaiting = taximeter.isWaiting,
                    waitingMs = taximeter.currentWaitingMs(meterTick),
                    waitingPriceUzs = taximeter.currentWaitingPriceUzs(meterTick),
                    onToggleWaiting = onToggleWaiting,
                )
            }

            Spacer(Modifier.height(16.dp))
            HorizontalDivider(color = VijdonColors.Border)
            Spacer(Modifier.height(16.dp))
            if (order.isOnWay || order.isArrived) {
                Text(
                    "Boshlang'ich taxminiy narx",
                    color = VijdonColors.TextSecondary,
                    style = MaterialTheme.typography.labelSmall,
                )
                Spacer(Modifier.height(4.dp))
            }
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                order.price?.let {
                    Text("${formatMoney(it)} so'm", color = VijdonColors.Green, style = MaterialTheme.typography.headlineSmall.copy(fontWeight = FontWeight.ExtraBold))
                } ?: Spacer(Modifier.width(1.dp))
                Text(
                    "${if (order.payment_type == "cash") "💵" else "💳"} ${order.car_type_display}",
                    color = VijdonColors.TextSecondary,
                    style = MaterialTheme.typography.labelMedium,
                )
            }
        }

        HorizontalDivider(color = VijdonColors.Border)
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 16.dp)) {
            if (inProgress) {
                Box(modifier = Modifier.fillMaxWidth(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator(modifier = Modifier.height(24.dp), color = VijdonColors.Yellow)
                }
            } else {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                    when {
                        order.isPending -> {
                            YellowButton("Qabul qilish", Modifier.weight(1f), onClick = onAccept)
                            OutlineButton("Rad etish", Modifier.weight(1f), onReject)
                        }
                        order.isAccepted -> {
                            YellowButton("Yo'lga chiqdim", Modifier.weight(1f), onClick = onWay)
                            OutlineButton("Operator", Modifier.weight(1f), onCallOperator)
                        }
                        order.isOnWay -> {
                            YellowButton("Yetib keldim", Modifier.weight(1f), onClick = onArrived)
                            OutlineButton("Operator", Modifier.weight(1f), onCallOperator)
                        }
                        order.isArrived -> {
                            YellowButton("Yakunlash", Modifier.weight(1f), onClick = onComplete)
                            OutlineButton("Operator", Modifier.weight(1f), onCallOperator)
                        }
                    }
                }
                if (order.isAccepted || order.isOnWay || order.isArrived) {
                    Spacer(Modifier.height(8.dp))
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp), modifier = Modifier.fillMaxWidth()) {
                        IconTextButton(Icons.Rounded.Phone, "Qo'ng'iroq", Modifier.weight(1f), onCallClient)
                        quickMessageFor(order)?.let { message ->
                            IconTextButton(Icons.AutoMirrored.Rounded.Message, "Xabar", Modifier.weight(1f)) { onQuickMessage(message) }
                        }
                    }
                }
            }
        }
    }
}

/**
 * Taximetr vidjeti — "Yo'lga chiqdim"dan "Yakunlash"gacha real vaqtda
 * yangilanadigan masofa/vaqt/narx (veb paneldagi "Taximetr" panjarasi
 * bilan bir xil g'oyada — quyuq gradient fon, yashil-binafsha-oltin
 * rangdagi metrikalar, jonli nuqta belgisi).
 */
@Composable
private fun TaximeterCard(
    distanceKm: Double,
    elapsedMs: Long,
    speedKmh: Double,
    hasFix: Boolean,
    priceUzs: Double,
    isWaiting: Boolean,
    waitingMs: Long,
    waitingPriceUzs: Double,
    onToggleWaiting: () -> Unit,
) {
    val purple = Color(0xFFAF52DE)
    val orange = Color(0xFFFF9500)
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .background(
                Brush.verticalGradient(listOf(Color(0xFF1C1C1F), Color(0xFF0A0A0B))),
                CardShape,
            )
            .border(1.dp, Color.White.copy(alpha = 0.08f), CardShape)
            .padding(vertical = 14.dp),
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp),
            verticalAlignment = Alignment.CenterVertically,
        ) {
            Box(
                modifier = Modifier.size(20.dp).background(purple.copy(alpha = 0.16f), ChipShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Speed, contentDescription = null, tint = purple, modifier = Modifier.size(11.dp))
            }
            Spacer(Modifier.width(7.dp))
            Text(
                "TAXIMETR",
                color = Color.White.copy(alpha = 0.4f),
                style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold, letterSpacing = 0.6.sp),
            )
            Spacer(Modifier.width(7.dp))
            PulsingDot(color = purple)
        }
        // GPS'dan hali yetarlicha aniq (<=60m) birorta ham nuqta kelmagan
        // bo'lsa — pastdagi 0/0.00 raqamlari "meter ishlamayapti" deb
        // noto'g'ri tushunilmasligi uchun buni aniq aytib qo'yamiz.
        if (!hasFix) {
            Row(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                CircularProgressIndicator(modifier = Modifier.size(14.dp), color = orange, strokeWidth = 2.dp)
                Spacer(Modifier.width(8.dp))
                Text(
                    "GPS signalini qidiryapmiz — ochiq joyda biroz kuting",
                    color = orange,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
        Box(modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 10.dp), contentAlignment = Alignment.Center) {
            Row(verticalAlignment = Alignment.Bottom) {
                Text(
                    formatMoney(priceUzs.toString()),
                    color = VijdonColors.Yellow,
                    style = MaterialTheme.typography.displaySmall.copy(fontWeight = FontWeight.ExtraBold),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis,
                )
                Spacer(Modifier.width(6.dp))
                Text(
                    "so'm",
                    color = VijdonColors.Yellow.copy(alpha = 0.55f),
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                    modifier = Modifier.padding(bottom = 6.dp),
                )
            }
        }
        HorizontalDivider(color = Color.White.copy(alpha = 0.08f), modifier = Modifier.padding(horizontal = 14.dp))
        Row(
            horizontalArrangement = Arrangement.spacedBy(6.dp),
            modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 10.dp),
        ) {
            MetricChip(Icons.Rounded.Timer, purple, formatElapsed(elapsedMs), null, "VAQT", Modifier.weight(1f))
            MetricChip(Icons.Rounded.Route, VijdonColors.Blue, String.format(Locale.US, "%.2f", distanceKm), "km", "MASOFA", Modifier.weight(1f))
            // Faqat masofa/vaqtdan hisoblangan taxminiy emas — GPS chipining
            // o'zi bergan haqiqiy tezlik (Doppler asosida), shu sabab
            // haydovchi harakatsiz bo'lsa 0 km/soat ko'rsatadi.
            MetricChip(Icons.Rounded.Speed, VijdonColors.Green, speedKmh.toInt().toString(), "km/h", "TEZLIK", Modifier.weight(1f))
        }
        Column(modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp)) {
            Row(
                modifier = Modifier
                    .fillMaxWidth()
                    .background(if (isWaiting) orange.copy(alpha = 0.18f) else Color.White.copy(alpha = 0.06f), ChipShape)
                    .clickable(onClick = onToggleWaiting)
                    .padding(vertical = 12.dp),
                horizontalArrangement = Arrangement.Center,
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(
                    if (isWaiting) Icons.Rounded.PlayArrow else Icons.Rounded.Pause,
                    contentDescription = null,
                    tint = if (isWaiting) orange else Color.White.copy(alpha = 0.65f),
                    modifier = Modifier.size(15.dp),
                )
                Spacer(Modifier.width(7.dp))
                Text(
                    if (isWaiting) "Davom etish" else "Kutish (mijoz band)",
                    color = if (isWaiting) orange else Color.White.copy(alpha = 0.65f),
                    style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.Bold),
                )
            }
            if (waitingMs > 500) {
                Spacer(Modifier.height(6.dp))
                Text(
                    "⏱ ${formatElapsed(waitingMs)} (+${formatMoney(waitingPriceUzs.toString())} so'm)",
                    color = orange,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                    textAlign = TextAlign.Center,
                    modifier = Modifier.fillMaxWidth(),
                )
            }
        }
    }
}

/**
 * Uch ustunli qatorda (VAQT/MASOFA/TEZLIK) yon-yonma (Row) tartib tor
 * telefon ekranida matnni siqib, "hunuk" ko'rinishga olib kelardi — shu
 * sabab ikonka TEPADA, qiymat va yorliq pastda, hammasi markazlashtirilgan
 * (Column) tartibga o'tkazildi — har bir chip torroq bo'lsa ham erkin nafas
 * oladi.
 */
@Composable
private fun MetricChip(icon: ImageVector, color: Color, value: String, unit: String?, label: String, modifier: Modifier = Modifier) {
    Column(
        modifier = modifier
            .background(Color.White.copy(alpha = 0.05f), ChipShape)
            .border(1.dp, Color.White.copy(alpha = 0.07f), ChipShape)
            .padding(vertical = 10.dp, horizontal = 4.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(24.dp).background(color.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = color, modifier = Modifier.size(12.dp))
        }
        Spacer(Modifier.height(6.dp))
        Text(
            if (unit != null) "$value $unit" else value,
            color = Color.White,
            style = MaterialTheme.typography.labelLarge.copy(fontWeight = FontWeight.ExtraBold),
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
        )
        Spacer(Modifier.height(2.dp))
        Text(
            label,
            color = Color.White.copy(alpha = 0.4f),
            style = MaterialTheme.typography.labelSmall.copy(fontSize = 9.sp, letterSpacing = 0.3.sp),
            maxLines = 1,
        )
    }
}

/** Jonli GPS/taximetr holatini bildiruvchi pulsatsiyalanuvchi nuqta —
 * veb'dagi `animation:pulse-dot` bilan bir xil g'oya. */
@Composable
private fun PulsingDot(color: Color) {
    val transition = rememberInfiniteTransition(label = "pulseDot")
    val alpha by transition.animateFloat(
        initialValue = 1f, targetValue = 0.25f,
        animationSpec = infiniteRepeatable(animation = tween(700), repeatMode = RepeatMode.Reverse),
        label = "pulseDotAlpha",
    )
    Box(modifier = Modifier.size(6.dp).background(color.copy(alpha = alpha), CircleShape))
}

/** "125000" ms -> "2:05" (soatlik bo'lsa "1:02:05"). */
private fun formatElapsed(ms: Long): String {
    val totalSec = (ms / 1000).coerceAtLeast(0)
    val h = totalSec / 3600
    val m = (totalSec % 3600) / 60
    val s = totalSec % 60
    return if (h > 0) String.format(Locale.US, "%d:%02d:%02d", h, m, s) else String.format(Locale.US, "%d:%02d", m, s)
}

/**
 * Veb'dagi "#my-orders-btn" bilan bir xil — Telegram mini-app'idagi
 * "asosiy tugma" uslubida, tab-bar ustida suzib turadi. Faqat 1 ta faol
 * buyurtma bo'lsa to'g'ridan-to'g'ri o'sha ochiladi, bir nechtasi bo'lsa
 * tanlov ro'yxati (pastga qarang) ochiladi.
 */
@Composable
private fun ActiveOrdersBar(activeOrders: List<OrderDto>, livePriceUzs: Double?, onClick: () -> Unit, modifier: Modifier = Modifier) {
    val label = if (activeOrders.size > 1) {
        "${activeOrders.size} ta faol buyurtma"
    } else {
        "${activeOrders.first().status_label} — buyurtma #${activeOrders.first().id}"
    }
    Row(
        modifier = modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 12.dp)
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 12.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(
            modifier = Modifier.size(36.dp).background(VijdonColors.Blue, CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(Icons.Rounded.LocalTaxi, contentDescription = null, tint = Color.White, modifier = Modifier.size(18.dp))
        }
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                label,
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.SemiBold),
                maxLines = 1,
                overflow = TextOverflow.Ellipsis,
            )
            // Taximetr ishlab turgan bo'lsa — sheet ochmasdan turib ham joriy
            // taxminiy summani ko'rsatadi, jonli (har soniyada yangilanadi).
            if (livePriceUzs != null) {
                Text(
                    "${formatMoney(livePriceUzs.toString())} so'm",
                    color = VijdonColors.Green,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                )
            }
        }
        Icon(Icons.Rounded.ExpandLess, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(18.dp))
    }
}

@Composable
private fun ActiveOrderChooserRow(order: OrderDto, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .background(VijdonColors.BadgeNeutral, CardShape)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Pill(order.status_label, color = VijdonColors.Blue, background = VijdonColors.Blue.copy(alpha = 0.15f))
        Spacer(Modifier.width(10.dp))
        Text(
            order.from_address,
            color = VijdonColors.TextPrimary,
            style = MaterialTheme.typography.bodyMedium,
            maxLines = 1,
            overflow = TextOverflow.Ellipsis,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        Text("#${order.id}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelSmall)
    }
}

/**
 * Onlayn/oflayn almashtirgichi. Ro'yxat bo'lganda LazyColumn ichiga birinchi
 * element sifatida qo'yiladi — shu sabab ro'yxatni yuqoriga surganda bu ham
 * QOTIB QOLMASDAN boshqa qatorlar bilan birga suriladi (avval doim tepada
 * qattiq turardi). Ro'yxat yo'q (yuklanmoqda/bo'sh/oflayn) holatlarda esa
 * suriladigan hech narsa yo'q, shu sabab tepada oddiy sarlavha sifatida qoladi.
 */
@Composable
private fun DutyToggleRow(isOnDuty: Boolean, onToggle: () -> Unit, horizontalPadding: androidx.compose.ui.unit.Dp = 16.dp) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = horizontalPadding, vertical = 4.dp)
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
                    .background(if (isOnDuty) VijdonColors.Green else VijdonColors.TextSecondary, CircleShape),
            )
            Spacer(Modifier.width(8.dp))
            Text(
                if (isOnDuty) "Onlayn" else "Oflayn",
                color = if (isOnDuty) VijdonColors.Green else VijdonColors.TextSecondary,
                style = MaterialTheme.typography.titleSmall,
            )
        }
        Switch(
            checked = isOnDuty,
            onCheckedChange = { onToggle() },
            colors = SwitchDefaults.colors(checkedTrackColor = VijdonColors.Green, checkedThumbColor = VijdonColors.TextPrimary),
        )
    }
}

/** Bildirishnoma ruxsati (Android 13+) umuman berilmagan bo'lsa — yangi
 * buyurtma haqida HECH QANDAY signal kelmaydi (full-screen sozlamasidan
 * ham oldinroq muammo), shu sabab qurilma Sozlamalariga yo'naltiramiz. */
@Composable
private fun NotificationPermissionBanner(onEnable: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .background(VijdonColors.Red.copy(alpha = 0.12f), CardShape)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Rounded.NotificationsActive, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
        Spacer(Modifier.width(8.dp))
        Text(
            "Bildirishnomalar o'chiq — yangi buyurtma haqida hech qanday xabar kelmaydi. Yoqing!",
            color = VijdonColors.Red,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        TextButton(onClick = onEnable) { Text("Yoqish", color = VijdonColors.Red, style = MaterialTheme.typography.labelMedium) }
    }
}

/** Android 14+ da "to'liq ekranli bildirishnoma" ruxsati o'chiq bo'lsa —
 * haydovchi ilovadan chiqib ketganda yangi buyurtmani ko'rmay qolishi mumkin,
 * shu sabab qurilma Sozlamalariga yo'naltiruvchi ogohlantirish ko'rsatiladi. */
@Composable
private fun FullScreenIntentBanner(onEnable: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .background(VijdonColors.Blue.copy(alpha = 0.12f), CardShape)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Icon(Icons.Rounded.NotificationsActive, contentDescription = null, tint = VijdonColors.Blue, modifier = Modifier.size(18.dp))
        Spacer(Modifier.width(8.dp))
        Text(
            "Ilovadan chiqib ketganda yangi buyurtma ogohlantirishi ko'rinishi uchun to'liq ekranli bildirishnomani yoqing",
            color = VijdonColors.Blue,
            style = MaterialTheme.typography.bodySmall,
            modifier = Modifier.weight(1f),
        )
        Spacer(Modifier.width(8.dp))
        TextButton(onClick = onEnable) { Text("Yoqish", color = VijdonColors.Blue, style = MaterialTheme.typography.labelMedium) }
    }
}

/** Talab ko'p bo'lgan payt (masalan yomg'ir/bayram) — narx ko'paytmasi
 * haqida ogohlantirish, veb paneldagi kabi. */
@Composable
private fun SurgeBanner(multiplier: Double, reason: String?) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(horizontal = 16.dp, vertical = 6.dp)
            .background(VijdonColors.Yellow.copy(alpha = 0.14f), CardShape)
            .padding(horizontal = 14.dp, vertical = 10.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Text("🔥", style = MaterialTheme.typography.titleMedium)
        Spacer(Modifier.width(8.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(
                "Talab yuqori — narxlar ${String.format(Locale.US, "%.1f", multiplier)}x oshirilgan",
                color = VijdonColors.Yellow,
                style = MaterialTheme.typography.bodySmall.copy(fontWeight = FontWeight.Bold),
            )
            if (!reason.isNullOrBlank()) {
                Text(reason, color = VijdonColors.Yellow.copy(alpha = 0.8f), style = MaterialTheme.typography.labelSmall)
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
            .let { if (isNearest) it.border(2.5.dp, VijdonColors.Yellow, CardShape) else it }
            .background(VijdonColors.Surface, CardShape)
            // Faol (eng yaqin) karta fonga qo'shimcha sariq tus beriladi —
            // qora fonda ingichka border yolg'iz o'zi yetarlicha ajralib
            // turmaydi, shu sabab butun karta sal "iliqroq" ko'rinadi.
            .let { if (isNearest) it.background(VijdonColors.Yellow.copy(alpha = 0.08f), CardShape) else it }
            .padding(horizontal = 18.dp, vertical = 14.dp),
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
                Spacer(Modifier.width(12.dp))
                Column(modifier = Modifier.weight(1f)) {
                    Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium, maxLines = 1)
                    // "· eng yaqin" matni ortiqcha edi — bu ma'lumot allaqachon
                    // sariq border/badge orqali ko'rinib turibdi, shu sabab
                    // olib tashlandi va masofaning o'zi kattaroq ko'rsatiladi.
                    Text(
                        distanceM?.let { formatDistanceM(it) } ?: "Masofa noma'lum",
                        color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodyMedium,
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
    if (m < 1000) "${m.toInt()} m" else String.format(java.util.Locale.US, "%.1f km", m / 1000)

/** Yandex Pro'dagi "3 km - 5 daqiqa" formatiga o'xshash — shahar ichi
 * o'rtacha tezlik (~28 km/soat) asosida taxminiy vaqt. */
internal fun formatDistanceEta(m: Double): String {
    val etaMin = (m / 1000.0 / 28.0 * 60.0).toInt().coerceAtLeast(1)
    return "${formatDistanceM(m)} · $etaMin daqiqa"
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
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.EmojiEvents, contentDescription = null, tint = rankIconColor(rank), modifier = Modifier.size(19.dp))
                Spacer(Modifier.width(7.dp))
                Text(
                    if (rank != null) "$rank-o'rin" else "—",
                    color = VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
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
                modifier = Modifier.padding(horizontal = 16.dp, vertical = 12.dp),
                verticalAlignment = Alignment.CenterVertically,
            ) {
                Icon(Icons.Rounded.CreditCard, contentDescription = null, tint = VijdonColors.Green, modifier = Modifier.size(19.dp))
                Spacer(Modifier.width(7.dp))
                Text(
                    "${formatMoney(balance)} so'm",
                    color = VijdonColors.TextPrimary,
                    style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
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

/**
 * Ro'yxatdagi ixcham karta — endi FAQAT "kutilmoqda" (hali qabul
 * qilinmagan) buyurtmalar uchun ishlatiladi, chunki qabul qilingan/yo'lda/
 * yetib kelgan buyurtmalar pastdagi suzuvchi tugma + to'liq ekranli
 * tafsilot oynasiga ko'chirilgan (`OrderDetailSheetContent`). Shu sabab
 * bu yerda faqat "Qabul qilish"/"Rad etish" harakati bor — boshqa
 * holatlar (Yo'lga chiqdim va h.k.) uchun kod endi keraksiz edi.
 */
@Composable
private fun OrderCard(
    order: OrderDto,
    distanceM: Double?,
    inProgress: Boolean,
    onAccept: () -> Unit,
    onReject: () -> Unit,
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
            // masofa va taxminiy vaqt.
            if (distanceM != null) {
                Text(formatDistanceEta(distanceM), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.labelMedium)
            }
        }
        Spacer(Modifier.height(10.dp))
        RouteAddresses(order.from_address, order.to_address)
        Spacer(Modifier.height(8.dp))
        Row(verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Rounded.Phone, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(14.dp))
            Spacer(Modifier.width(4.dp))
            Text("${order.client_name} · ${order.client_phone}", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
        }

        // Veb'dagi buyurtma kartasidagi kabi — narx (katta, yashil) va
        // masofa/to'lov turi bir qatorda, ajratuvchi chiziqdan pastda.
        Spacer(Modifier.height(10.dp))
        HorizontalDivider(color = VijdonColors.Border)
        Spacer(Modifier.height(10.dp))
        Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
            order.price?.let {
                Text("${formatMoney(it)} so'm", color = VijdonColors.Green, style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.ExtraBold))
            } ?: Spacer(Modifier.width(1.dp))
            Text(
                "${if (order.payment_type == "cash") "💵" else "💳"} ${order.car_type_display}",
                color = VijdonColors.TextSecondary,
                style = MaterialTheme.typography.labelSmall,
            )
        }

        Spacer(Modifier.height(12.dp))
        if (inProgress) {
            CircularProgressIndicator(modifier = Modifier.height(20.dp), color = VijdonColors.Yellow)
            return@Column
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            YellowButton("Qabul qilish", onClick = onAccept)
            OutlineButton("Rad etish", onClick = onReject)
        }
    }
}

@Composable
private fun IconTextButton(icon: ImageVector, text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextSecondary),
    ) {
        Icon(icon, contentDescription = null, modifier = Modifier.size(16.dp))
        Spacer(Modifier.width(6.dp))
        Text(text, style = MaterialTheme.typography.labelMedium)
    }
}

/** Har doim asosiy ("tasdiqlovchi") harakat — Qabul qilish, Yo'lga chiqdim,
 * Yetib keldim, Yakunlash — shu sabab bosilganda ozgina titrash bilan
 * (haptic feedback) tasdiqlanadi, zamonaviy ilovalardagi kabi. */
@Composable
private fun YellowButton(text: String, modifier: Modifier = Modifier, haptic: Boolean = true, onClick: () -> Unit) {
    val hapticFeedback = LocalHapticFeedback.current
    Button(
        onClick = {
            if (haptic) hapticFeedback.performHapticFeedback(HapticFeedbackType.LongPress)
            onClick()
        },
        modifier = modifier,
        colors = ButtonDefaults.buttonColors(containerColor = VijdonColors.Yellow, contentColor = VijdonColors.TextOnYellow),
    ) { Text(text) }
}

@Composable
private fun OutlineButton(text: String, modifier: Modifier = Modifier, onClick: () -> Unit) {
    OutlinedButton(
        onClick = onClick,
        modifier = modifier,
        colors = ButtonDefaults.outlinedButtonColors(contentColor = VijdonColors.TextPrimary),
    ) { Text(text) }
}
