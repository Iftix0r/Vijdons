package uz.vijdon.driver.ui

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.automirrored.rounded.Logout
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DrawerValue
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.ModalDrawerSheet
import androidx.compose.material3.ModalNavigationDrawer
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.material3.rememberDrawerState
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.addresses.AddressesScreen
import uz.vijdon.driver.ui.balance.BalanceHistoryScreen
import uz.vijdon.driver.ui.balance.TopupScreen
import uz.vijdon.driver.ui.contract.ContractScreen
import uz.vijdon.driver.ui.destination.DestinationScreen
import uz.vijdon.driver.ui.history.HistoryScreen
import uz.vijdon.driver.ui.home.HomeScreen
import uz.vijdon.driver.ui.nearbydrivers.NearbyDriversScreen
import uz.vijdon.driver.ui.ordercreate.OrderCreateScreen
import uz.vijdon.driver.ui.profile.ProfileScreen
import uz.vijdon.driver.ui.rating.RatingScreen
import uz.vijdon.driver.ui.sos.SosScreen
import uz.vijdon.driver.ui.theme.VijdonColors

private val bottomBarRoutes = setOf(Tabs.HOME, Tabs.HISTORY, Tabs.CHAT, Tabs.PROFILE)

// Pastki tab-bar bo'limlari orasida — iOS/Telegram'dagi kabi yumshoq
// crossfade (chetdan surilib kirish emas, chunki bular teng darajadagi
// bo'limlar, biri ikkinchisining "ustiga" chiqmaydi).
private val tabEnter = fadeIn(tween(220))
private val tabExit = fadeOut(tween(160))

// Profildan ochiladigan ichki (Balans, Shartnoma, Manzillar, SOS, Reyting,
// Buyurtma yaratish) sahifalar — iOS'dagi "push" navigatsiyasi kabi
// o'ngdan kirib, orqaga qaytishda o'ngga chiqib ketadi.
private val pushEnter = slideInHorizontally(tween(280)) { it } + fadeIn(tween(280))
private val pushExit = slideOutHorizontally(tween(200)) { -it / 4 } + fadeOut(tween(200))
private val popEnter = slideInHorizontally(tween(280)) { -it / 4 } + fadeIn(tween(280))
private val popExit = slideOutHorizontally(tween(220)) { it } + fadeOut(tween(220))

private data class MenuItem(val route: String, val label: String, val icon: ImageVector)

private val menuItems = listOf(
    MenuItem(Tabs.HOME, "Asosiy", Icons.Rounded.LocalTaxi),
    MenuItem(Tabs.HISTORY, "Tarix", Icons.Rounded.History),
    MenuItem(SubRoutes.ORDER_CREATE, "Buyurtma yaratish", Icons.Rounded.Add),
    MenuItem(Tabs.CHAT, "Chat", Icons.Rounded.Forum),
    MenuItem(Tabs.PROFILE, "Profil", Icons.Rounded.Person),
)

@Composable
fun ApprovedScaffold(driver: DriverDto, onLogout: () -> Unit) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute == null || currentRoute in bottomBarRoutes
    // claude.ai'dagi kabi — yon tomondan (chapdan) surilib kiruvchi menyu,
    // pastdagi suzuvchi panel o'rniga. Yopiq holatda ekranning qolgan
    // qismi to'liq ko'rinadi, faqat hamburger tugmasi orqali (yoki
    // chetdan suriб) ochiladi.
    val drawerState = rememberDrawerState(initialValue = DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    var showLogoutDialog by remember { mutableStateOf(false) }

    fun goToTab(route: String) {
        navController.navigate(route) {
            popUpTo(Tabs.HOME) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    fun onMenuItemClick(item: MenuItem) {
        scope.launch { drawerState.close() }
        if (item.route == SubRoutes.ORDER_CREATE) {
            navController.navigate(SubRoutes.ORDER_CREATE)
        } else {
            goToTab(item.route)
        }
    }

    ModalNavigationDrawer(
        drawerState = drawerState,
        // Ichki (Balans/Shartnoma/SOS kabi) sahifalarda chetdan surib
        // tortish o'chirilgan — u yerda gorizontal "push" o'tish animatsiyasi
        // bilan chalkashib ketmasin deb.
        gesturesEnabled = showBottomBar,
        drawerContent = {
            ModalDrawerSheet(drawerContainerColor = VijdonColors.Surface) {
                Column(modifier = Modifier.fillMaxSize().statusBarsPadding()) {
                    // Profil bloki — avatar + ism, tepada alohida ajratilgan
                    // "karta" ko'rinishida, keyin ajratuvchi chiziq bilan
                    // menyu ro'yxatidan bo'linadi.
                    Row(
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 20.dp),
                        verticalAlignment = Alignment.CenterVertically,
                    ) {
                        Box(
                            modifier = Modifier.size(52.dp).background(VijdonColors.Yellow, CircleShape),
                            contentAlignment = Alignment.Center,
                        ) {
                            Text(
                                driver.full_name.trim().firstOrNull()?.uppercase() ?: "?",
                                color = VijdonColors.TextOnYellow,
                                style = MaterialTheme.typography.titleLarge.copy(fontWeight = FontWeight.Bold),
                            )
                        }
                        Spacer(Modifier.width(14.dp))
                        Column(modifier = Modifier.weight(1f)) {
                            Text(
                                driver.full_name,
                                color = VijdonColors.TextPrimary,
                                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
                                maxLines = 1,
                            )
                            Text(
                                driver.phone_number,
                                color = VijdonColors.TextSecondary,
                                style = MaterialTheme.typography.bodySmall,
                                maxLines = 1,
                            )
                        }
                    }
                    HorizontalDivider(color = VijdonColors.Border)
                    Spacer(Modifier.height(8.dp))
                    menuItems.forEach { item ->
                        val selected = currentRoute == item.route
                        NavigationDrawerItem(
                            label = { Text(item.label, style = MaterialTheme.typography.bodyLarge.copy(fontWeight = if (selected) FontWeight.Bold else FontWeight.Normal)) },
                            icon = { Icon(item.icon, contentDescription = null) },
                            selected = selected,
                            onClick = { onMenuItemClick(item) },
                            colors = NavigationDrawerItemDefaults.colors(
                                // Diqqat: avval yarim-shaffof sariq fon ustiga sariq
                                // matn/ikonka ishlatilgan edi — kontrasti WCAG'ga
                                // to'g'ri kelmasdan, quyoshda deyarli o'qilmas edi.
                                // Endi TO'LIQ to'yingan sariq fon + QORA matn/ikonka
                                // (ilovadagi asosiy sariq tugmalar bilan bir xil
                                // uslub) — yuqori kontrast.
                                selectedContainerColor = VijdonColors.Yellow,
                                selectedTextColor = VijdonColors.TextOnYellow,
                                selectedIconColor = VijdonColors.TextOnYellow,
                                unselectedTextColor = VijdonColors.TextPrimary,
                                unselectedIconColor = VijdonColors.TextSecondary,
                            ),
                            modifier = Modifier.padding(horizontal = 12.dp, vertical = 3.dp),
                        )
                    }

                    Spacer(Modifier.weight(1f))

                    HorizontalDivider(color = VijdonColors.Border)
                    NavigationDrawerItem(
                        label = { Text("Tizimdan chiqish", style = MaterialTheme.typography.bodyLarge) },
                        icon = { Icon(Icons.AutoMirrored.Rounded.Logout, contentDescription = null) },
                        selected = false,
                        onClick = { showLogoutDialog = true },
                        colors = NavigationDrawerItemDefaults.colors(
                            unselectedTextColor = VijdonColors.Red,
                            unselectedIconColor = VijdonColors.Red,
                        ),
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                    )
                }
            }
        },
    ) {
        Scaffold(
            containerColor = VijdonColors.Background,
            bottomBar = {},
        ) { padding ->
            Box(modifier = Modifier.fillMaxSize()) {
                NavHost(
                    navController = navController,
                    startDestination = Tabs.HOME,
                    // Edge-to-edge (enableEdgeToEdge()) yoqilgach, Scaffold'ning
                    // o'zi bergan `padding` status-bar zonasini yetarlicha hisobga
                    // olmadi — TopBar (reyting/balans) status-bar bilan ustma-ust
                    // tushib qolgan edi. Shu sabab bu yerda ANIQ ravishda ham
                    // qo'shiladi.
                    modifier = Modifier.padding(padding).statusBarsPadding(),
                    enterTransition = { tabEnter },
                    exitTransition = { tabExit },
                    popEnterTransition = { tabEnter },
                    popExitTransition = { tabExit },
                ) {
                    composable(Tabs.HOME) {
                        HomeScreen(
                            driver = driver,
                            onLogout = onLogout,
                            onOpenRating = { navController.navigate(SubRoutes.RATING) },
                            onOpenBalance = { navController.navigate(SubRoutes.BALANCE_HISTORY) },
                        )
                    }
                    composable(Tabs.HISTORY) { HistoryScreen() }
                    composable(Tabs.CHAT) { ChatPlaceholderScreen() }
                    composable(Tabs.PROFILE) {
                        ProfileScreen(
                            driver = driver,
                            onOpenBalanceHistory = { navController.navigate(SubRoutes.BALANCE_HISTORY) },
                            onOpenTopup = { navController.navigate(SubRoutes.TOPUP) },
                            onOpenContract = { navController.navigate(SubRoutes.CONTRACT) },
                            onOpenAddresses = { navController.navigate(SubRoutes.ADDRESSES) },
                            onOpenSos = { navController.navigate(SubRoutes.SOS) },
                            onOpenDestination = { navController.navigate(SubRoutes.DESTINATION) },
                            onOpenNearbyDrivers = { navController.navigate(SubRoutes.NEARBY_DRIVERS) },
                            onLogout = onLogout,
                        )
                    }
                    composable(
                        SubRoutes.BALANCE_HISTORY,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { BalanceHistoryScreen() }
                    composable(
                        SubRoutes.TOPUP,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { TopupScreen(onDone = { navController.popBackStack() }) }
                    composable(
                        SubRoutes.CONTRACT,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { ContractScreen() }
                    composable(
                        SubRoutes.ADDRESSES,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { AddressesScreen() }
                    composable(
                        SubRoutes.SOS,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { SosScreen() }
                    composable(
                        SubRoutes.RATING,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { RatingScreen() }
                    composable(
                        SubRoutes.ORDER_CREATE,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) {
                        OrderCreateScreen(
                            onDone = { navController.popBackStack() },
                            onBack = { navController.popBackStack() },
                        )
                    }
                    composable(
                        SubRoutes.DESTINATION,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { DestinationScreen(onBack = { navController.popBackStack() }) }
                    composable(
                        SubRoutes.NEARBY_DRIVERS,
                        enterTransition = { pushEnter }, exitTransition = { pushExit },
                        popEnterTransition = { popEnter }, popExitTransition = { popExit },
                    ) { NearbyDriversScreen(onBack = { navController.popBackStack() }) }
                }

                // Hamburger tugmasi — faqat asosiy (pastki panel bo'lgan)
                // bo'limlarda ko'rinadi, ichki sahifalarda o'zining "orqaga"
                // tugmasi bor, shu yerda kerak emas. Diqqat: Balans tugmasi
                // (HomeScreen'dagi BalanceBar) bilan AYNAN bir xil "shisha"
                // uslubi (Glass fon + 4dp soya + doira shakl) ishlatiladi —
                // avval ikkalasi har xil balandlik/vazn bilan chizilib,
                // vizual muvozanat yo'qolgan edi.
                if (showBottomBar) {
                    Surface(
                        shape = CircleShape,
                        color = VijdonColors.Glass,
                        shadowElevation = 4.dp,
                        onClick = { scope.launch { drawerState.open() } },
                        modifier = Modifier
                            .statusBarsPadding()
                            .padding(start = 16.dp, top = 16.dp)
                            .align(Alignment.TopStart),
                    ) {
                        Box(modifier = Modifier.size(48.dp), contentAlignment = Alignment.Center) {
                            Icon(Icons.Rounded.Menu, contentDescription = "Menyu", tint = VijdonColors.TextPrimary, modifier = Modifier.size(22.dp))
                        }
                    }
                }
            }
        }
    }

    // Bitta noto'g'ri bosish bilan darhol chiqib ketmasin — qayta kirish
    // uchun telefon+parol kerak bo'ladi, shu sabab tasdiqlash so'raladi
    // (ProfileScreen'dagi "Tizimdan chiqish" bilan bir xil UX).
    if (showLogoutDialog) {
        AlertDialog(
            onDismissRequest = { showLogoutDialog = false },
            title = { Text("Tizimdan chiqasizmi?") },
            text = { Text("Qayta kirish uchun telefon raqami va parolingiz kerak bo'ladi.") },
            confirmButton = {
                TextButton(onClick = { showLogoutDialog = false; onLogout() }) {
                    Text("Chiqish", color = VijdonColors.Red)
                }
            },
            dismissButton = { TextButton(onClick = { showLogoutDialog = false }) { Text("Bekor qilish") } },
            containerColor = VijdonColors.Surface,
        )
    }
}
