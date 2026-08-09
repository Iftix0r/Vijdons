package uz.vijdon.driver.ui

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
        ) {
            composable(Tabs.HOME) {
                HomeScreen(
                    driver = driver,
                    onLogout = onLogout,
                    onOpenRating = { navController.navigate(SubRoutes.RATING) },
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
            composable(SubRoutes.BALANCE_HISTORY) { BalanceHistoryScreen() }
            composable(SubRoutes.TOPUP) { TopupScreen(onDone = { navController.popBackStack() }) }
            composable(SubRoutes.CONTRACT) { ContractScreen() }
            composable(SubRoutes.ADDRESSES) { AddressesScreen() }
            composable(SubRoutes.SOS) { SosScreen() }
            composable(SubRoutes.RATING) { RatingScreen() }
            composable(SubRoutes.ORDER_CREATE) {
                OrderCreateScreen(
                    onDone = { navController.popBackStack() },
                    onBack = { navController.popBackStack() },
                )
            }
        }
    }
}
