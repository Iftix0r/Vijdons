package uz.vijdon.driver.ui.addresses

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Card
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Scaffold
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto

@Composable
fun AddressesScreen(viewModel: AddressesViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Scaffold { padding ->
        LazyColumn(modifier = Modifier.fillMaxSize().padding(padding).padding(12.dp)) {
            items(state.addresses, key = { it.id }) { address ->
                Card(
                    modifier = Modifier.fillMaxWidth().padding(vertical = 4.dp),
                ) {
                    Column(
                        modifier = Modifier.fillMaxWidth().padding(12.dp),
                    ) {
                        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                            Text(address.name, style = MaterialTheme.typography.titleSmall)
                            Text("Navbat: ${address.queue_count}", style = MaterialTheme.typography.bodySmall)
                        }
                        Text(address.address, style = MaterialTheme.typography.bodySmall)
                        Text("Bugun: ${address.today_orders} buyurtma", style = MaterialTheme.typography.bodySmall)
                        Spacer(Modifier.height(4.dp))
                        TextButton(onClick = { viewModel.openQueue(address) }) { Text("Navbatni ko'rish") }
                    }
                }
            }
        }
    }

    state.selectedAddress?.let { address ->
        AlertDialog(
            onDismissRequest = viewModel::closeQueue,
            title = { Text(address.name) },
            text = {
                Column {
                    state.myPosition?.let { Text("Sizning o'rningiz: $it") } ?: Text("Siz navbatda emassiz")
                    Spacer(Modifier.height(8.dp))
                    state.queueDrivers.forEach { d ->
                        Text("${d.position}. ${d.full_name} — ${d.car_model} (${d.car_number})")
                    }
                }
            },
            confirmButton = { TextButton(onClick = viewModel::closeQueue) { Text("Yopish") } },
        )
    }
}
