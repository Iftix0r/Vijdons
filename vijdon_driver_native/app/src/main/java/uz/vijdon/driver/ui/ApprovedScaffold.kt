package uz.vijdon.driver.ui

import androidx.compose.foundation.layout.padding
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.Icon
import androidx.compose.material3.NavigationBar
import androidx.compose.material3.NavigationBarItem
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TopAppBar
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.navigation.NavDestination.Companion.hierarchy
import androidx.navigation.NavGraph.Companion.findStartDestination
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
import uz.vijdon.driver.ui.profile.ProfileScreen
import uz.vijdon.driver.ui.rating.RatingScreen
import uz.vijdon.driver.ui.sos.SosScreen

private object Tabs {
    const val HOME = "home"
    const val HISTORY = "history"
    const val RATING = "rating"
    const val PROFILE = "profile"
}

private object SubRoutes {
    const val BALANCE_HISTORY = "balance_history"
    const val TOPUP = "topup"
    const val CONTRACT = "contract"
    const val ADDRESSES = "addresses"
    const val SOS = "sos"
}

private val bottomTabs = listOf(
    Triple(Tabs.HOME, "Asosiy", "🚗"),
    Triple(Tabs.HISTORY, "Tarix", "📋"),
    Triple(Tabs.RATING, "Reyting", "🏆"),
    Triple(Tabs.PROFILE, "Profil", "👤"),
)

@OptIn(ExperimentalMaterial3Api::class)
@Composable
fun ApprovedScaffold(driver: DriverDto, onLogout: () -> Unit) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute == null || bottomTabs.any { it.first == currentRoute }

    Scaffold(
        bottomBar = {
            if (showBottomBar) {
                NavigationBar {
                    bottomTabs.forEach { (route, label, emoji) ->
                        NavigationBarItem(
                            selected = backStackEntry?.destination?.hierarchy?.any { it.route == route } == true,
                            onClick = {
                                navController.navigate(route) {
                                    popUpTo(navController.graph.findStartDestination().id) { saveState = true }
                                    launchSingleTop = true
                                    restoreState = true
                                }
                            },
                            icon = { Text(emoji) },
                            label = { Text(label) },
                        )
                    }
                }
            }
        },
    ) { padding ->
        NavHost(
            navController = navController,
            startDestination = Tabs.HOME,
            modifier = Modifier.padding(padding),
        ) {
            composable(Tabs.HOME) { HomeScreen(driver = driver, onLogout = onLogout) }
            composable(Tabs.HISTORY) { HistoryScreen() }
            composable(Tabs.RATING) { RatingScreen() }
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
        }
    }
}
