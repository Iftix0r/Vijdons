package uz.vijdon.driver.ui.addresses

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
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
import androidx.compose.material.icons.rounded.LocationOn
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.ui.theme.CardShape
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.Pill
import uz.vijdon.driver.ui.theme.ScreenHeader
import uz.vijdon.driver.ui.theme.VijdonColors
import uz.vijdon.driver.ui.theme.cardShadow

@Composable
fun AddressesScreen(viewModel: AddressesViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background).padding(16.dp)) {
        ScreenHeader("Yaqin manzillar")
        Spacer(Modifier.height(12.dp))

        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(bottom = 10.dp))
        }

        if (state.loading && state.addresses.isEmpty()) {
            CenteredLoading()
        } else if (state.addresses.isEmpty()) {
            Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Saqlangan manzillar yo'q", color = VijdonColors.TextSecondary)
            }
        } else {
            LazyColumn(modifier = Modifier.fillMaxSize()) {
                items(state.addresses, key = { it.id }) { address ->
                    Column(Modifier.animateItem()) { AddressRow(address) { viewModel.openQueue(address) } }
                }
            }
        }
    }

    state.selectedAddress?.let { address ->
        AlertDialog(
            onDismissRequest = viewModel::closeQueue,
            title = { Text(address.name, color = VijdonColors.TextPrimary) },
            text = {
                Column {
                    state.myPosition?.let {
                        Text("Sizning o'rningiz: $it", color = VijdonColors.Yellow)
                    } ?: Text("Siz navbatda emassiz", color = VijdonColors.TextSecondary)
                    Spacer(Modifier.height(8.dp))
                    state.queueDrivers.forEach { d ->
                        Text("${d.position}. ${d.full_name} — ${d.car_model} (${d.car_number})", color = VijdonColors.TextPrimary)
                    }
                }
            },
            confirmButton = { TextButton(onClick = viewModel::closeQueue) { Text("Yopish", color = VijdonColors.Yellow) } },
            containerColor = VijdonColors.Surface,
        )
    }
}

@Composable
private fun AddressRow(address: AddressDto, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .padding(vertical = 4.dp)
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(horizontal = 18.dp, vertical = 14.dp),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Row(modifier = Modifier.weight(1f), verticalAlignment = Alignment.CenterVertically) {
            Box(modifier = Modifier.size(36.dp).background(VijdonColors.BadgeNeutral, CircleShape), contentAlignment = Alignment.Center) {
                Icon(Icons.Rounded.LocationOn, contentDescription = null, tint = VijdonColors.Red, modifier = Modifier.size(18.dp))
            }
            Spacer(Modifier.width(12.dp))
            Column(modifier = Modifier.weight(1f)) {
                Text(address.name, color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium, maxLines = 1)
                Text("Bugun: ${address.today_orders} buyurtma", color = VijdonColors.TextSecondary, style = MaterialTheme.typography.bodySmall)
            }
        }
        Spacer(Modifier.width(8.dp))
        Pill(
            "${address.queue_count} navbatda",
            color = if (address.queue_count > 0) VijdonColors.Green else VijdonColors.TextSecondary,
        )
    }
}
