package uz.vijdon.operator

import android.content.Intent
import android.os.Build
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.activity.enableEdgeToEdge
import androidx.compose.animation.Crossfade
import androidx.compose.animation.core.tween
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
import androidx.lifecycle.lifecycleScope
import dagger.hilt.android.AndroidEntryPoint
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.push.OpenTabBus
import uz.vijdon.operator.ui.ApprovedScaffold
import uz.vijdon.operator.ui.SessionState
import uz.vijdon.operator.ui.SessionViewModel
import uz.vijdon.operator.ui.login.LoginScreen
import uz.vijdon.operator.ui.theme.VijdonOperatorTheme

// Diqqat: ildiz composable'ni alohida funksiyaga chiqarish (masalan
// `VijdonOperatorApp()`) vijdon_driver_native loyihasida shu aniq
// Kotlin/Compose kompilyator versiyasi ostida bo'sh ekranga olib kelgan —
// shu sabab bu yerda ham xavfsizlik uchun to'g'ridan-to'g'ri onCreate/
// setContent ichida chaqiriladi.
@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    companion object {
        const val EXTRA_OPEN_TAB = "extra_open_tab"
    }

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        handleOpenTabIfNeeded(intent)
        enableEdgeToEdge()
        window.navigationBarColor = android.graphics.Color.TRANSPARENT
        window.statusBarColor = android.graphics.Color.TRANSPARENT
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            window.isNavigationBarContrastEnforced = false
            window.isStatusBarContrastEnforced = false
        }
        setContent {
            VijdonOperatorTheme {
                val darkTheme = isSystemInDarkTheme()
                val view = LocalView.current
                SideEffect {
                    val controller = WindowCompat.getInsetsController(window, view)
                    controller.isAppearanceLightStatusBars = !darkTheme
                    controller.isAppearanceLightNavigationBars = !darkTheme
                }

                val sessionViewModel: SessionViewModel = hiltViewModel()
                val session by sessionViewModel.state.collectAsState()

                Crossfade(targetState = session, animationSpec = tween(250), label = "session") { s ->
                    when (s) {
                        is SessionState.Loading -> LoadingBox()
                        is SessionState.LoggedOut -> LoginScreen(onLoggedIn = sessionViewModel::onLoggedIn)
                        is SessionState.Approved -> ApprovedScaffold(operator = s.operator, onLogout = sessionViewModel::logout)
                    }
                }
            }
        }
    }

    override fun onNewIntent(intent: Intent) {
        super.onNewIntent(intent)
        setIntent(intent)
        handleOpenTabIfNeeded(intent)
    }

    /** Push-bildirishnoma bosilib ilova (qayta) ochilganda — tegishli
     * bo'limga o'tish uchun `OpenTabBus`ga signal beradi (`ApprovedScaffold`
     * shuni tinglab navigatsiya qiladi). */
    private fun handleOpenTabIfNeeded(intent: Intent?) {
        val tab = intent?.getStringExtra(EXTRA_OPEN_TAB) ?: return
        intent.removeExtra(EXTRA_OPEN_TAB)
        lifecycleScope.launch { OpenTabBus.trigger(tab) }
    }
}

@Composable
private fun LoadingBox() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator()
    }
}
