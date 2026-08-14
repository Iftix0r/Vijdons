package uz.vijdon.operator.ui

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
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import uz.vijdon.operator.data.api.OperatorDto
import uz.vijdon.operator.data.push.OpenTabBus
import uz.vijdon.operator.ui.balance.BalanceScreen
import uz.vijdon.operator.ui.chat.ChatDriverListScreen
import uz.vijdon.operator.ui.chat.ChatGroupScreen
import uz.vijdon.operator.ui.chat.ChatThreadScreen
import uz.vijdon.operator.ui.dashboard.DashboardScreen
import uz.vijdon.operator.ui.drivers.DriverDetailScreen
import uz.vijdon.operator.ui.drivers.DriversScreen
import uz.vijdon.operator.ui.orders.OrderCreateScreen
import uz.vijdon.operator.ui.orders.OrderDetailScreen
import uz.vijdon.operator.ui.orders.OrdersScreen
import uz.vijdon.operator.ui.theme.VijdonColors

private val bottomTabs = setOf(Tabs.DASHBOARD, Tabs.ORDERS, Tabs.CHAT, Tabs.BALANCE, Tabs.DRIVERS)

private val tabEnter = fadeIn(tween(220))
private val tabExit = fadeOut(tween(160))
private val pushEnter = slideInHorizontally(tween(280)) { it } + fadeIn(tween(280))
private val pushExit = slideOutHorizontally(tween(200)) { -it / 4 } + fadeOut(tween(200))
private val popEnter = slideInHorizontally(tween(280)) { -it / 4 } + fadeIn(tween(280))
private val popExit = slideOutHorizontally(tween(220)) { it } + fadeOut(tween(220))

@Composable
fun ApprovedScaffold(operator: OperatorDto, onLogout: () -> Unit) {
    val navController = rememberNavController()
    val backStackEntry by navController.currentBackStackEntryAsState()
    val currentRoute = backStackEntry?.destination?.route
    val showBottomBar = currentRoute == null || currentRoute in bottomTabs

    val badgeViewModel: BadgeViewModel = hiltViewModel()
    val ordersBadge by badgeViewModel.ordersBadge.collectAsState()
    val chatBadge by badgeViewModel.chatBadge.collectAsState()
    val balanceBadge by badgeViewModel.balanceBadge.collectAsState()

    fun goToTab(route: String) {
        navController.navigate(route) {
            popUpTo(navController.graph.findStartDestination().id) { saveState = true }
            launchSingleTop = true
            restoreState = true
        }
    }

    LaunchedEffect(Unit) {
        OpenTabBus.events.collect { tab ->
            if (tab in bottomTabs) goToTab(tab)
        }
    }

    Scaffold(
        containerColor = VijdonColors.Background,
        bottomBar = {
            if (showBottomBar) {
                VijdonBottomBar(
                    currentTab = currentRoute ?: Tabs.DASHBOARD,
                    ordersBadge = ordersBadge,
                    chatBadge = chatBadge,
                    balanceBadge = balanceBadge,
                    onTabSelected = ::goToTab,
                    onCreateOrder = { navController.navigate(SubRoutes.ORDER_CREATE) },
                )
            }
        },
    ) { padding ->
        Box(modifier = Modifier.fillMaxSize()) {
            NavHost(
                navController = navController,
                startDestination = Tabs.DASHBOARD,
                modifier = Modifier.padding(padding),
                enterTransition = { tabEnter }, exitTransition = { tabExit },
                popEnterTransition = { tabEnter }, popExitTransition = { tabExit },
            ) {
                composable(Tabs.DASHBOARD) {
                    DashboardScreen(
                        operator = operator,
                        onOpenOrders = { goToTab(Tabs.ORDERS) },
                        onOpenBalance = { goToTab(Tabs.BALANCE) },
                        onOpenDrivers = { goToTab(Tabs.DRIVERS) },
                        onLogout = onLogout,
                    )
                }
                composable(Tabs.ORDERS) {
                    OrdersScreen(onOpenOrder = { navController.navigate(SubRoutes.orderDetail(it)) })
                }
                composable(Tabs.CHAT) {
                    ChatDriverListScreen(
                        onOpenThread = { id, name -> navController.navigate(SubRoutes.chatThread(id, name)) },
                        onOpenGroup = { navController.navigate(SubRoutes.CHAT_GROUP) },
                    )
                }
                composable(Tabs.BALANCE) {
                    BalanceScreen(onOpenDriver = { navController.navigate(SubRoutes.driverDetail(it)) })
                }
                composable(Tabs.DRIVERS) {
                    DriversScreen(onOpenDriver = { navController.navigate(SubRoutes.driverDetail(it)) })
                }
                composable(
                    SubRoutes.ORDER_CREATE,
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) {
                    OrderCreateScreen(onDone = { navController.popBackStack() }, onBack = { navController.popBackStack() })
                }
                composable(
                    SubRoutes.ORDER_DETAIL,
                    arguments = listOf(navArgument("orderId") { type = NavType.IntType }),
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) { entry ->
                    OrderDetailScreen(orderId = entry.arguments?.getInt("orderId") ?: return@composable, onBack = { navController.popBackStack() })
                }
                composable(
                    SubRoutes.DRIVER_DETAIL,
                    arguments = listOf(navArgument("driverId") { type = NavType.IntType }),
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) { entry ->
                    DriverDetailScreen(driverId = entry.arguments?.getInt("driverId") ?: return@composable, onBack = { navController.popBackStack() })
                }
                composable(
                    SubRoutes.CHAT_THREAD,
                    arguments = listOf(
                        navArgument("driverId") { type = NavType.IntType },
                        navArgument("driverName") { type = NavType.StringType },
                    ),
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) { entry ->
                    val id = entry.arguments?.getInt("driverId") ?: return@composable
                    val name = java.net.URLDecoder.decode(entry.arguments?.getString("driverName") ?: "", "UTF-8")
                    ChatThreadScreen(driverId = id, driverName = name, onBack = { navController.popBackStack() })
                }
                composable(
                    SubRoutes.CHAT_GROUP,
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) {
                    ChatGroupScreen(onBack = { navController.popBackStack() })
                }
            }
        }
    }
}
