package uz.vijdon.driver.ui.auth

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp

@Composable
fun PendingScreen(onLogout: () -> Unit) {
    StatusScreen(
        title = "Hisobingiz tekshirilmoqda",
        message = "Admin sizning ma'lumotlaringizni tasdiqlagach, ilovadan foydalana olasiz.",
        onLogout = onLogout,
    )
}

@Composable
fun FrozenScreen(onLogout: () -> Unit) {
    StatusScreen(
        title = "Hisobingiz muzlatilgan",
        message = "Uzoq vaqt faol bo'lmaganingiz sababli hisobingiz muzlatildi. Admin bilan bog'laning.",
        onLogout = onLogout,
    )
}

@Composable
private fun StatusScreen(title: String, message: String, onLogout: () -> Unit) {
    Scaffold { padding ->
        Column(
            modifier = Modifier.fillMaxSize().padding(padding).padding(24.dp),
            verticalArrangement = Arrangement.Center,
            horizontalAlignment = Alignment.CenterHorizontally,
        ) {
            Text(title, style = MaterialTheme.typography.headlineSmall, textAlign = TextAlign.Center)
            Spacer(Modifier.height(12.dp))
            Text(message, style = MaterialTheme.typography.bodyMedium, textAlign = TextAlign.Center)
            Spacer(Modifier.height(24.dp))
            TextButton(onClick = onLogout) { Text("Chiqish") }
        }
    }
}
