package uz.vijdon.driver.ui.starttrip

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.ui.theme.DispatchLoadingMark
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * "+" tugmasi endi forma o'rniga to'g'ridan-to'g'ri shu ekranni ochadi —
 * hech qanday kiritish maydoni yo'q, faqat "boshlanmoqda" holati (bir
 * necha soniya) va xato bo'lsa qayta urinish. Muvaffaqiyatli bo'lsa,
 * ekran o'zi darhol yopiladi (`onDone`) — haydovchi Bosh sahifada
 * taksimetr ishlab turganini ko'radi.
 */
@Composable
fun StartTripScreen(onDone: () -> Unit, onBack: () -> Unit, viewModel: StartTripViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    LaunchedEffect(state.success) {
        if (state.success) onDone()
    }

    Column(
        modifier = Modifier.fillMaxSize().padding(24.dp),
        horizontalAlignment = Alignment.CenterHorizontally,
        verticalArrangement = Arrangement.Center,
    ) {
        if (state.error == null) {
            DispatchLoadingMark(modifier = Modifier.width(110.dp))
            Spacer(Modifier.height(20.dp))
            Text(
                "Safar boshlanmoqda...",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
            )
            Spacer(Modifier.height(6.dp))
            Text(
                "Taksimetr hozir ishga tushadi — yo'lovchini olib, safarni davom ettiraverasiz.",
                color = VijdonColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
        } else {
            Text(
                "Boshlab bo'lmadi",
                color = VijdonColors.TextPrimary,
                style = MaterialTheme.typography.titleMedium.copy(fontWeight = FontWeight.Bold),
            )
            Spacer(Modifier.height(6.dp))
            Text(
                state.error ?: "",
                color = VijdonColors.Red,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
            Spacer(Modifier.height(20.dp))
            Button(onClick = { viewModel.start() }, modifier = Modifier.fillMaxWidth()) {
                Text("Qayta urinish")
            }
            Spacer(Modifier.height(10.dp))
            OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth()) {
                Text("Ortga")
            }
        }
    }
}
