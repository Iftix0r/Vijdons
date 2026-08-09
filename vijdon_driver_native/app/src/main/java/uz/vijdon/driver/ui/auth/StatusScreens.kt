package uz.vijdon.driver.ui.auth

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.AcUnit
import androidx.compose.material.icons.rounded.HourglassTop
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun PendingScreen(onLogout: () -> Unit) {
    StatusScreen(
        icon = Icons.Rounded.HourglassTop,
        accentColor = VijdonColors.Yellow,
        title = "Hisobingiz tekshirilmoqda",
        message = "Admin sizning ma'lumotlaringizni tasdiqlagach, ilovadan foydalana olasiz.",
        onLogout = onLogout,
    )
}

@Composable
fun FrozenScreen(onLogout: () -> Unit) {
    StatusScreen(
        icon = Icons.Rounded.AcUnit,
        accentColor = VijdonColors.Blue,
        title = "Hisobingiz muzlatilgan",
        message = "Uzoq vaqt faol bo'lmaganingiz sababli hisobingiz muzlatildi. Admin bilan bog'laning.",
        onLogout = onLogout,
    )
}

@Composable
private fun StatusScreen(icon: ImageVector, accentColor: Color, title: String, message: String, onLogout: () -> Unit) {
    Column(
        modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(24.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally,
    ) {
        Box(
            modifier = Modifier.size(88.dp).background(accentColor.copy(alpha = 0.15f), CircleShape),
            contentAlignment = Alignment.Center,
        ) {
            Icon(icon, contentDescription = null, tint = accentColor, modifier = Modifier.size(44.dp))
        }
        Spacer(Modifier.height(20.dp))
        Text(title, style = MaterialTheme.typography.headlineSmall, color = VijdonColors.TextPrimary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(12.dp))
        Text(message, style = MaterialTheme.typography.bodyMedium, color = VijdonColors.TextSecondary, textAlign = TextAlign.Center)
        Spacer(Modifier.height(24.dp))
        TextButton(onClick = onLogout) { Text("Chiqish", color = VijdonColors.Yellow) }
    }
}
