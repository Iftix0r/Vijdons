package uz.vijdon.driver

import android.content.Intent
import android.os.Build
import android.os.Bundle
import android.view.WindowManager
import androidx.activity.ComponentActivity
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
import androidx.activity.compose.setContent
import androidx.compose.animation.core.tween
import androidx.compose.animation.fadeIn
import androidx.compose.animation.fadeOut
import androidx.compose.animation.slideInHorizontally
import androidx.compose.animation.slideOutHorizontally
import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.SideEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalView
import androidx.core.view.WindowCompat
import androidx.hilt.navigation.compose.hiltViewModel
import androidx.navigation.NavHostController
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.rememberNavController
import dagger.hilt.android.AndroidEntryPoint
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.ui.ApprovedScaffold
import uz.vijdon.driver.ui.SessionState
import uz.vijdon.driver.ui.SessionViewModel
import uz.vijdon.driver.ui.auth.FrozenScreen
import uz.vijdon.driver.ui.auth.LoginScreen
import uz.vijdon.driver.ui.auth.PendingScreen
import uz.vijdon.driver.ui.auth.RegisterScreen
import uz.vijdon.driver.ui.theme.VijdonDriverTheme

private object Routes {
    const val LOGIN = "login"
    const val REGISTER = "register"
}

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    // Diqqat: sessiya holatini (hiltViewModel + collectAsState + when-tarmoq)
    // alohida composable funksiyaga chiqarish (masalan `VijdonDriverApp()`)
    // shu loyihaning aniq Kotlin/Compose kompilyator versiyasi ostida bu
    // kompozitsiyani butunlay bo'sh (hech narsa chizilmagan) holga olib
    // keldi — xatosiz, log'da iz qoldirmasdan. Sinovdan o'tgan yagona
    // barqaror shakl — buni to'g'ridan-to'g'ri shu yerda, onCreate/setContent
    // ichida chaqirish (pastdagi yordamchi composable'lar — LoadingBox,
    // AuthNavHost va ekranlarning o'zi — alohida funksiya sifatida muammosiz
    // ishlaydi, faqat aynan shu "ildiz" composable muammoli edi).
    companion object {
        const val EXTRA_NEW_ORDER_ALERT = "extra_new_order_alert"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        showOverLockscreenIfNeeded(intent)
        setContent {
            VijdonDriverTheme {
                // Status-bar/navigatsiya-bar ikonkalari — tizim yorug' rejimda
                // bo'lsa qora, qorong'i rejimda oq bo'lishi kerak, aks holda
                // yorug' rejimda oq ikonkalar yorug' fon ustida ko'rinmay qolardi.
                val darkTheme = isSystemInDarkTheme()
                val view = LocalView.current
                SideEffect {
                    val controller = WindowCompat.getInsetsController(window, view)
                    controller.isAppearanceLightStatusBars = !darkTheme
                    controller.isAppearanceLightNavigationBars = !darkTheme
                }

                val sessionViewModel: SessionViewModel = hiltViewModel()
                val session by sessionViewModel.state.collectAsState()
                val navController = rememberNavController()

                Crossfade(targetState = session, animationSpec = tween(250), label = "session") { s ->
                    when (s) {
                        is SessionState.Loading -> LoadingBox()
                        is SessionState.LoggedOut -> AuthNavHost(navController, onLoggedIn = sessionViewModel::onLoggedIn)
                        is SessionState.Pending -> PendingScreen(onLogout = sessionViewModel::logout, onRefresh = sessionViewModel::refresh)
                        is SessionState.Frozen -> FrozenScreen(onLogout = sessionViewModel::logout, onRefresh = sessionViewModel::refresh)
                        is SessionState.Approved -> ApprovedScaffold(driver = s.driver, onLogout = sessionViewModel::logout)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        showOverLockscreenIfNeeded(intent)
    }

    /**
     * Yangi buyurtma push-bildirishnomasidan "to'liq ekran" sifatida
     * ochilganda — qurilma qulflangan bo'lsa ham ekran ustida ko'rinishi
     * uchun. Oddiy (bildirishnomasiz) ochilishda bu bayroqlar qo'yilmaydi,
     * aks holda ilova doim qulf ekranini chetlab o'tgan bo'lardi.
     */
    private fun showOverLockscreenIfNeeded(intent: Intent?) {
        if (intent?.getBooleanExtra(EXTRA_NEW_ORDER_ALERT, false) != true) return
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O_MR1) {
            setShowWhenLocked(true)
            setTurnScreenOn(true)
        } else {
            @Suppress("DEPRECATION")
            window.addFlags(
                WindowManager.LayoutParams.FLAG_SHOW_WHEN_LOCKED or WindowManager.LayoutParams.FLAG_TURN_SCREEN_ON,
            )
        }
    }
}

@Composable
private fun LoadingBox() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator()
    }
}

@Composable
private fun AuthNavHost(navController: NavHostController, onLoggedIn: (DriverDto) -> Unit) {
    NavHost(
        navController = navController,
        startDestination = Routes.LOGIN,
        enterTransition = { slideInHorizontally(tween(280)) { it } + fadeIn(tween(280)) },
        exitTransition = { slideOutHorizontally(tween(200)) { -it / 4 } + fadeOut(tween(200)) },
        popEnterTransition = { slideInHorizontally(tween(280)) { -it / 4 } + fadeIn(tween(280)) },
        popExitTransition = { slideOutHorizontally(tween(220)) { it } + fadeOut(tween(220)) },
    ) {
        composable(Routes.LOGIN) {
            LoginScreen(
                onLoggedIn = onLoggedIn,
                onGoToRegister = { navController.navigate(Routes.REGISTER) },
            )
        }
        composable(Routes.REGISTER) {
            RegisterScreen(onRegistered = { navController.popBackStack() })
        }
    }
}
