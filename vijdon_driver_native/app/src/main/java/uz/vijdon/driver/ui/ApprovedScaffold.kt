package uz.vijdon.driver.ui

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.addresses.AddressesScreen
import uz.vijdon.driver.ui.balance.BalanceHistoryScreen
import uz.vijdon.driver.ui.balance.TopupScreen
import uz.vijdon.driver.ui.chat.ChatBadgeViewModel
import uz.vijdon.driver.ui.chat.ChatScreen
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

@Composable
fun ApprovedScaffold(driver: DriverDto, onLogout: () -> Unit) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute == null || currentRoute in bottomBarRoutes

    fun goToTab(route: String) {
        navController.navigate(route) {
            popUpTo(Tabs.HOME) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    // Chat bo'limi ochiq-yopiqligidan qat'i nazar (masalan Asosiy sahifada
    // turgan payt ham) o'qilmagan xabarlar soni ko'rinishi kerak, shu sabab
    // bu ViewModel ApprovedScaffold darajasida — butun sessiya davomida.
    val chatBadgeViewModel: ChatBadgeViewModel = hiltViewModel()
    val chatUnread by chatBadgeViewModel.unread.collectAsState()

    Scaffold(
        containerColor = VijdonColors.Background,
        bottomBar = {
            if (showBottomBar) {
                VijdonBottomBar(
                    currentRoute = currentRoute,
                    chatBadge = chatUnread,
                    onTabSelected = ::goToTab,
                    onCreateOrder = { navController.navigate(SubRoutes.ORDER_CREATE) },
                )
            }
        },
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            NavHost(
                navController = navController,
                startDestination = Tabs.HOME,
                // Diqqat: `Scaffold`ning o'zi (topBar yo'qligi sabab)
                // `padding`ning ICHIDA status-bar balandligini ALLAQACHON
                // hisobga oladi (`contentWindowInsets` sukut bo'yicha
                // systemBars) — shu ustiga yana `.statusBarsPadding()`
                // qo'shish bo'shliqni IKKI MARTA qo'shib, "Xush kelibsiz"
                // sarlavhasini keraksiz pastga tushirib yuborardi.
                modifier = Modifier.padding(padding),
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
                        onOpenAddresses = { navController.navigate(SubRoutes.ADDRESSES) },
                    )
                }
                composable(Tabs.HISTORY) { HistoryScreen() }
                composable(Tabs.CHAT) { ChatScreen() }
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
        }
    }
}
