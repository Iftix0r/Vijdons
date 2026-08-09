package uz.vijdon.driver

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
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
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            VijdonDriverTheme {
                val sessionViewModel: SessionViewModel = hiltViewModel()
                val session by sessionViewModel.state.collectAsState()
                val navController = rememberNavController()

                when (val s = session) {
                    is SessionState.Loading -> LoadingBox()
                    is SessionState.LoggedOut -> AuthNavHost(navController, onLoggedIn = sessionViewModel::onLoggedIn)
                    is SessionState.Pending -> PendingScreen(onLogout = sessionViewModel::logout)
                    is SessionState.Frozen -> FrozenScreen(onLogout = sessionViewModel::logout)
                    is SessionState.Approved -> ApprovedScaffold(driver = s.driver, onLogout = sessionViewModel::logout)
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

@Composable
private fun AuthNavHost(navController: NavHostController, onLoggedIn: (DriverDto) -> Unit) {
    NavHost(navController = navController, startDestination = Routes.LOGIN) {
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
