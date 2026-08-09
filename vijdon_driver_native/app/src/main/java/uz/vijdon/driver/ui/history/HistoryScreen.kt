package uz.vijdon.driver.ui.history

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Card
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.OrderDto

@Composable
fun HistoryScreen(viewModel: HistoryViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Scaffold { padding ->
        Column(modifier = Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                HISTORY_PERIODS.forEach { (value, label) ->
                    FilterChip(
                        selected = state.period == value,
                        onClick = { viewModel.onPeriodChange(value) },
                        label = { Text(label) },
                    )
                }
            }
            Text(
                "Jami: ${state.totalEarned.toInt()} so'm · ${state.completed} ta safar",
                style = MaterialTheme.typography.bodyMedium,
                modifier = Modifier.padding(vertical = 8.dp),
            )
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.orders, key = { it.id }) { order -> HistoryRow(order) }
            }
        }
    }
}

@Composable
private fun HistoryRow(order: OrderDto) {
    Card(modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp)) {
        Column(modifier = Modifier.padding(12.dp)) {
            Text(order.status_label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
            Text("${order.from_address} → ${order.to_address}", style = MaterialTheme.typography.bodyMedium)
            Row(horizontalArrangement = Arrangement.SpaceBetween, modifier = Modifier.fillMaxWidth()) {
                Text(order.price?.let { "$it so'm" } ?: "—", style = MaterialTheme.typography.bodySmall)
                Text(order.created_at.take(10), style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}
