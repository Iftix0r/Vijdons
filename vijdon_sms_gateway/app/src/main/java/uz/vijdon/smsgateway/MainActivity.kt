package uz.vijdon.smsgateway

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
import dagger.hilt.android.AndroidEntryPoint
import uz.vijdon.smsgateway.data.service.SmsGatewayService
import uz.vijdon.smsgateway.ui.SessionState
import uz.vijdon.smsgateway.ui.SessionViewModel
import uz.vijdon.smsgateway.ui.login.LoginScreen
import uz.vijdon.smsgateway.ui.status.StatusScreen
import uz.vijdon.smsgateway.ui.theme.VijdonSmsGatewayTheme

@AndroidEntryPoint
class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        enableEdgeToEdge()
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.Q) {
            window.isNavigationBarContrastEnforced = false
            window.isStatusBarContrastEnforced = false
        }
        setContent {
            VijdonSmsGatewayTheme {
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
                        is SessionState.LoggedIn -> StatusScreen(
                            username = s.username,
                            onLogout = {
                                stopService(Intent(this, SmsGatewayService::class.java))
                                sessionViewModel.logout()
                            },
                        )
                    }
                }
            }
        }
    }
}

@Composable
private fun LoadingBox() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        CircularProgressIndicator()
    }
}
