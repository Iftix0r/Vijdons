package uz.vijdon.driver.ui.balance

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.ArrowDownward
import androidx.compose.material.icons.rounded.ArrowUpward
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.BalanceEntryDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow
import uz.vijdon.driver.util.formatMoney

@Composable
fun BalanceHistoryScreen(viewModel: BalanceHistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("O'tkazmalar tarixi", subtitle = "Joriy balans: ${formatMoney(state.balance)} so'm")
        Spacer(Modifier.height(12.dp))
        state.error?.let {
            ErrorBanner(it)
            Spacer(Modifier.height(10.dp))
        }
        if (state.loading && state.entries.isEmpty()) {
            CenteredLoading()
        } else if (state.entries.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Hali o'tkazmalar yo'q", color = VijdonColors.TextSecondary)
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.entries) { entry -> BalanceEntryRow(entry) }
            }
        }
    }
}

/** Server "yyyy-MM-ddTHH:mm:ss..." beradi — veb'dagi kabi "kun.oy.yil soat:daqiqa" ko'rinishiga o'giradi. */
private fun formatFullDate(iso: String): String {
    if (iso.length < 16) return iso
    val year = iso.substring(0, 4)
    val month = iso.substring(5, 7)
    val day = iso.substring(8, 10)
    val time = iso.substring(11, 16)
    return "$day.$month.$year $time"
}

@Composable
private fun BalanceEntryRow(entry: BalanceEntryDto) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp).cardShadow().background(VijdonColors.Surface, CardShape).padding(14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            val color = if (entry.is_income) VijdonColors.Green else VijdonColors.Red
            Box(modifier = Modifier.size(32.dp).background(color.copy(alpha = 0.15f), CircleShape), contentAlignment = Alignment.Center) {
                Icon(
                    if (entry.is_income) Icons.Rounded.ArrowDownward else Icons.Rounded.ArrowUpward,
                    contentDescription = null, tint = color, modifier = Modifier.size(16.dp),
                )
            }
            Spacer(Modifier.width(10.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(entry.note, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.bodyMedium)
                Text(formatFullDate(entry.created_at), color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.width(8.dp))
        Text(
            "${if (entry.is_income) "+" else "-"}${formatMoney(entry.amount)}",
            color = if (entry.is_income) VijdonColors.Green else VijdonColors.Red,
            style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold),
            maxLines = 1,
        )
    }
}
