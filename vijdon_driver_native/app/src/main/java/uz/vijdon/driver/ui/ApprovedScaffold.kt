package uz.vijdon.driver.ui

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Add
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material.icons.rounded.History
import androidx.compose.material.icons.rounded.LocalTaxi
import androidx.compose.material.icons.rounded.Menu
import androidx.compose.material.icons.rounded.Person
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
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
import uz.vijdon.driver.ui.theme.cardShadow

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
    var showMenu by remember { mutableStateOf(false) }

    fun goToTab(route: String) {
        navController.navigate(route) {
            popUpTo(Tabs.HOME) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    Scaffold(
        containerColor = VijdonColors.Background,
        // Pastki suzuvchi panel o'rniga — yuqori chap burchakdagi hamburger
        // tugmasi orqali ochiladigan menyu (pastga qarang).
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

            // Hamburger tugmasi — faqat asosiy (pastki panel bo'lgan) bo'limlarda
            // ko'rinadi, ichki (Balans/Shartnoma/SOS kabi) sahifalarda o'zining
            // "orqaga" tugmasi bor, shu yerda kerak emas.
            if (showBottomBar) {
                Box(
                    modifier = Modifier
                        .statusBarsPadding()
                        .padding(start = 16.dp, top = 8.dp)
                        .align(Alignment.TopStart),
                ) {
                    IconButton(
                        onClick = { showMenu = true },
                        modifier = Modifier
                            .size(44.dp)
                            .cardShadow()
                            .background(VijdonColors.Surface, CircleShape),
                    ) {
                        Icon(Icons.Rounded.Menu, contentDescription = "Menyu", tint = VijdonColors.TextPrimary)
                    }
                    DropdownMenu(
                        expanded = showMenu,
                        onDismissRequest = { showMenu = false },
                        containerColor = VijdonColors.Surface,
                    ) {
                        menuItems.forEach { item ->
                            val selected = currentRoute == item.route
                            DropdownMenuItem(
                                text = {
                                    Text(
                                        item.label,
                                        color = if (selected) VijdonColors.Yellow else VijdonColors.TextPrimary,
                                        style = if (selected) {
                                            MaterialTheme.typography.bodyLarge.copy(fontWeight = FontWeight.Bold)
                                        } else {
                                            MaterialTheme.typography.bodyLarge
                                        },
                                    )
                                },
                                leadingIcon = {
                                    Icon(
                                        item.icon, contentDescription = null,
                                        tint = if (selected) VijdonColors.Yellow else VijdonColors.TextSecondary,
                                    )
                                },
                                onClick = {
                                    showMenu = false
                                    if (item.route == SubRoutes.ORDER_CREATE) {
                                        navController.navigate(SubRoutes.ORDER_CREATE)
                                    } else {
                                        goToTab(item.route)
                                    }
                                },
                            )
                        }
                    }
                }
            }
        }
    }
}
