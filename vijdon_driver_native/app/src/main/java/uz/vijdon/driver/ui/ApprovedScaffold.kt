package uz.vijdon.driver.ui

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.addresses.AddressesScreen
import uz.vijdon.driver.ui.balance.BalanceHistoryScreen
import uz.vijdon.driver.ui.balance.TopupScreen
import uz.vijdon.driver.ui.contract.ContractScreen
import uz.vijdon.driver.ui.history.HistoryScreen
import uz.vijdon.driver.ui.home.HomeScreen
import uz.vijdon.driver.ui.ordercreate.OrderCreateScreen
import uz.vijdon.driver.ui.profile.ProfileScreen
import uz.vijdon.driver.ui.rating.RatingScreen
import uz.vijdon.driver.ui.sos.SosScreen

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

    Scaffold(
        containerColor = uz.vijdon.driver.ui.theme.VijdonColors.Background,
        bottomBar = {
            if (showBottomBar) {
                VijdonBottomBar(
                    currentRoute = currentRoute,
                    driver = driver,
                    chatBadge = 0,
                    onTabSelected = ::goToTab,
                    onCreateOrder = { navController.navigate(SubRoutes.ORDER_CREATE) },
                )
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Tabs.HOME,
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
        }
    }
}
