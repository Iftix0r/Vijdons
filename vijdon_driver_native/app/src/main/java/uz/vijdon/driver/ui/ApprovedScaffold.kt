package uz.vijdon.driver.ui

import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.pager.HorizontalPager
import androidx.compose.foundation.pager.rememberPagerState
import androidx.compose.material3.Scaffold
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.ui.Modifier
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.addresses.AddressesScreen
import uz.vijdon.driver.ui.balance.BalanceHistoryScreen
import uz.vijdon.driver.ui.chat.ChatBadgeViewModel
import uz.vijdon.driver.ui.chat.ChatScreen
import uz.vijdon.driver.ui.contract.ContractScreen
import uz.vijdon.driver.ui.history.HistoryScreen
import uz.vijdon.driver.ui.home.HomeScreen
import uz.vijdon.driver.ui.ordercreate.OrderCreateScreen
import uz.vijdon.driver.ui.profile.ProfileScreen
import uz.vijdon.driver.ui.rating.RatingScreen
import uz.vijdon.driver.ui.sos.SosScreen
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.webview.WebAppScreen

// Diqqat: avval Bosh/Tarix/Chat/Profil har biri ALOHIDA NavHost destination
// edi (tugma bosilganda navController.navigate() bilan almashtirilardi).
// Endi Telegram'dagi kabi ENGARMA (chapga/o'ngga surish) bilan ham
// almashtiriladi — shu sabab bu to'rttasi endi BITTA NavHost destination
// (Tabs.HOME) ichidagi HorizontalPager'ning sahifalari. Pastki tab-bar
// tugmasi bosilganda ham pager shu sahifaga siljiydi (navigate emas).
//
// Reyting, YouTube va SOS ham ATAYLAB shu YAGONA pager'ga, eng CHETLARIGA
// qo'shilgan: shu orqali "Bosh sahifadan o'ngga surish -> Reyting" va
// "Profildan chapga surish -> YouTube -> SOS" XUDDI tab-bar svaypi bilan
// bir xil, haqiqiy HorizontalPager mexanizmi orqali ishlaydi — alohida
// (nested) surish detektori kerak emas, shu sabab pastki tab-bar svaypi
// bilan HECH QACHON to'qnashmaydi.
//
// Reyting — Bosh tomonga qo'shilgan: "Bosh sahifadan o'ngga surish ->
// Reyting" (avval bu yerda YouTube edi, foydalanuvchi so'rovi bilan
// Reytingga almashtirildi). YouTube va SOS Profil tomonida ("Profildan
// chapga surish -> YouTube -> SOS", avval shu yo'nalishda Reyting bor edi).
// Bosh sahifaning indeksi endi 1.
private val pagerPages = listOf(SubRoutes.RATING, Tabs.HOME, Tabs.HISTORY, Tabs.CHAT, Tabs.PROFILE, SubRoutes.YOUTUBE, SubRoutes.SOS)

// Reyting/YouTube/SOS sahifalarida ham pastki tab-bar o'zining "uy"
// bo'limini (mos ravishda Bosh/Profil) yoritib turishi uchun.
private fun tabForPage(page: Int) = when (pagerPages.getOrNull(page)) {
    Tabs.HISTORY -> Tabs.HISTORY
    Tabs.CHAT -> Tabs.CHAT
    Tabs.PROFILE, SubRoutes.SOS, SubRoutes.RATING -> Tabs.PROFILE
    else -> Tabs.HOME
}
private fun pageForTab(route: String) = pagerPages.indexOf(route).takeIf { it >= 0 } ?: 1

private val bottomBarRoutes = setOf(Tabs.HOME)

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

    // To'rtta asosiy bo'lim (Bosh/Tarix/Chat/Profil) + Reyting/YouTube/SOS
    // (eng chetlarida) — barchasi ALOHIDA NavHost destination emas,
    // Telegram'dagi kabi bitta HorizontalPager'ning sahifalari, shu sabab
    // tab-bar bosilganda HAM, ekranni chapga/o'ngga surganda HAM shu
    // YAGONA `pagerState` orqali almashadi. Bosh sahifa (indeks 1) — boshlang'ich.
    val pagerState = rememberPagerState(initialPage = 1, pageCount = { pagerPages.size })
    val pagerScope = rememberCoroutineScope()

    // YouTube sahifasida pastki tugmalar qatori (foydalanuvchi so'rovi
    // bo'yicha) yashiriladi — ko'proq joy YouTube uchun qoladi. Diqqat:
    // `WebAppScreen`dagi teginish-ushlab-qolish tuzatishi (Shorts uchun)
    // sabab bu sahifada endi gorizontal svayp bilan ham chiqib bo'lmaydi —
    // shu sabab pastki tugmalar o'rniga WebAppScreen'ning o'zida suzuvchi
    // "Ortga" tugmasi bor (pastga qarang), aks holda haydovchi bu
    // sahifada "qamalib" qolardi.
    val showBottomBar = (currentRoute == null || currentRoute in bottomBarRoutes) &&
        pagerPages.getOrNull(pagerState.currentPage) != SubRoutes.YOUTUBE

    fun goToTab(route: String) {
        pagerScope.launch { pagerState.animateScrollToPage(pageForTab(route)) }
    }
    fun goToPage(page: Int) {
        pagerScope.launch { pagerState.animateScrollToPage(page) }
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
                    currentRoute = tabForPage(pagerState.currentPage),
                    chatBadge = chatUnread,
                    profilePhotoUrl = driver.photo_url,
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
                    HorizontalPager(state = pagerState, modifier = Modifier.fillMaxSize()) { page ->
                        when (pagerPages.getOrNull(page)) {
                            SubRoutes.RATING -> RatingScreen()
                            SubRoutes.YOUTUBE -> WebAppScreen(
                                url = "https://m.youtube.com",
                                onBackToHome = { goToPage(pagerPages.indexOf(Tabs.HOME)) },
                            )
                            Tabs.HISTORY -> HistoryScreen()
                            Tabs.CHAT -> ChatScreen()
                            Tabs.PROFILE -> ProfileScreen(
                                driver = driver,
                                onOpenBalanceHistory = { navController.navigate(SubRoutes.BALANCE_HISTORY) },
                                onOpenContract = { navController.navigate(SubRoutes.CONTRACT) },
                                onLogout = onLogout,
                            )
                            SubRoutes.SOS -> SosScreen()
                            else -> HomeScreen(
                                driver = driver,
                                onLogout = onLogout,
                                onOpenRating = { goToPage(pagerPages.indexOf(SubRoutes.RATING)) },
                                onOpenBalance = { navController.navigate(SubRoutes.BALANCE_HISTORY) },
                                onOpenAddresses = { navController.navigate(SubRoutes.ADDRESSES) },
                            )
                        }
                    }
                }
                composable(
                    SubRoutes.BALANCE_HISTORY,
                    enterTransition = { pushEnter }, exitTransition = { pushExit },
                    popEnterTransition = { popEnter }, popExitTransition = { popExit },
                ) { BalanceHistoryScreen() }
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
}
