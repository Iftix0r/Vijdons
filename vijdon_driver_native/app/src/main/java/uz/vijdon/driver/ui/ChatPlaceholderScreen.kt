package uz.vijdon.driver.ui

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Forum
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import uz.vijdon.driver.ui.theme.VijdonColors

@Composable
fun ChatPlaceholderScreen() {
    Box(
        modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(32.dp),
        contentAlignment = Alignment.Center,
    ) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            // Yandex'ning o'z rang tili: ko'k — xabar/chat funksiyalari uchun
            // (sariq faqat asosiy CTA/aksent uchun qoladi).
            Box(
                modifier = Modifier.size(88.dp).background(VijdonColors.Blue.copy(alpha = 0.15f), CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Forum, contentDescription = null, tint = VijdonColors.Blue, modifier = Modifier.size(40.dp))
            }
            Spacer(Modifier.height(20.dp))
            Text(
                "Guruh chat tez orada qo'shiladi",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(8.dp))
            Text(
                "Haydovchilar bilan yozishma va operatorga murojaat shu bo'limdan bo'ladi.",
                color = VijdonColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
        }
    }
}
