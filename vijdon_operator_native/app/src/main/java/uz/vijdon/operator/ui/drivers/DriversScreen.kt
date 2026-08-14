package uz.vijdon.operator.ui.drivers

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.unit.dp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.Pill
import uz.vijdon.operator.ui.theme.TabHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

private val tabs = listOf("approved" to "Tasdiqlangan", "pending" to "Kutilmoqda", "rejected" to "Rad etilgan")

@Composable
fun DriversScreen(onOpenDriver: (Int) -> Unit, viewModel: DriversViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Column(modifier = Modifier.padding(16.dp)) {
            TabHeader(title = "Haydovchilar")
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = state.q,
                onValueChange = viewModel::onQueryChange,
                placeholder = { Text("Qidirish — ism, telefon, mashina") },
                leadingIcon = { Icon(Icons.Rounded.Search, contentDescription = null) },
                singleLine = true,
                keyboardOptions = KeyboardOptions(imeAction = ImeAction.Search),
                keyboardActions = KeyboardActions(onSearch = { viewModel.search() }),
                colors = OutlinedTextFieldDefaults.colors(
                    focusedContainerColor = VijdonColors.Surface,
                    unfocusedContainerColor = VijdonColors.Surface,
                    focusedBorderColor = VijdonColors.Blue,
                    unfocusedBorderColor = VijdonColors.Border,
                ),
                modifier = Modifier.fillMaxWidth(),
            )
            Spacer(Modifier.height(10.dp))
            LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                items(tabs) { (value, label) ->
                    val count = when (value) {
                        "approved" -> state.approvedCount
                        "pending" -> state.pendingCount
                        else -> state.rejectedCount
                    }
                    val selected = state.tab == value
                    Text(
                        "$label ($count)",
                        color = if (selected) VijdonColors.TextOnBlue else VijdonColors.TextSecondary,
                        style = MaterialTheme.typography.labelMedium,
                        modifier = Modifier
                            .background(if (selected) VijdonColors.Blue else VijdonColors.BadgeNeutral, CardShape)
                            .clickable { viewModel.selectTab(value) }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                    )
                }
            }
        }

        when {
            state.loading && state.drivers.isEmpty() -> CenteredLoading()
            state.error != null && state.drivers.isEmpty() -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
            state.drivers.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                Text("Haydovchi topilmadi", color = VijdonColors.TextSecondary)
            }
            else -> LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(state.drivers, key = { it.id }) { d -> DriverCard(d, onClick = { onOpenDriver(d.id) }) }
                if (state.hasNext) {
                    item { TextButton(onClick = viewModel::loadMore, modifier = Modifier.fillMaxWidth()) { Text("Ko'proq yuklash", color = VijdonColors.Blue) } }
                }
                item { Spacer(Modifier.height(80.dp)) }
            }
        }
    }
}

@Composable
private fun DriverCard(d: DriverDto, onClick: () -> Unit) {
    Row(
        modifier = Modifier.fillMaxWidth().cardShadow().background(VijdonColors.Surface, CardShape).clickable(onClick = onClick).padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Box(modifier = Modifier.size(10.dp).background(if (d.is_online) VijdonColors.Green else VijdonColors.TextSecondary.copy(alpha = 0.4f), CircleShape))
        Spacer(Modifier.width(10.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(d.full_name, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
            Text("${d.car_model} • ${d.car_number}", style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
        }
        Column(horizontalAlignment = Alignment.End) {
            Text("${formatMoney(d.balance)} so'm", style = MaterialTheme.typography.bodySmall, color = if (d.balance.toDoubleOrNull() != null && d.balance.toDouble() < 0) VijdonColors.Red else VijdonColors.Green)
            if (d.is_frozen) Pill("Muzlatilgan", color = VijdonColors.Red)
            else if (d.is_on_duty) Pill("Navbatda", color = VijdonColors.Green)
        }
    }
}
