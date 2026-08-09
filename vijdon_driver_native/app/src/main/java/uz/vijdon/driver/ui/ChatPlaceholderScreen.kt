package uz.vijdon.driver.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.size
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun ChatPlaceholderScreen() {
    Box(
        modifier = Modifier.fillMaxSize().background(VijdonColors.Background),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Icon(Icons.Rounded.Forum, contentDescription = null, tint = VijdonColors.Border, modifier = Modifier.size(48.dp))
            Spacer(Modifier.height(8.dp))
            Text("Guruh chat tez orada qo'shiladi", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodyLarge)
        }
    }
}
