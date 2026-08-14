package uz.vijdon.operator.ui.orders

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.rounded.Search
import androidx.compose.material3.CircularProgressIndicator
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
import uz.vijdon.operator.data.api.OrderDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.Pill
import uz.vijdon.operator.ui.theme.RouteAddresses
import uz.vijdon.operator.ui.theme.TabHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow
import uz.vijdon.operator.util.formatMoney

private val statusFilters = listOf(
    null to "Barchasi",
    "pending" to "Kutilmoqda",
    "accepted" to "Qabul qilindi",
    "on_way" to "Yo'lda",
    "arrived" to "Yetib keldi",
    "completed" to "Yakunlandi",
    "cancelled" to "Bekor qilindi",
)

fun statusColor(status: String): androidx.compose.ui.graphics.Color = when (status) {
    "pending" -> VijdonColors.Yellow
    "accepted", "on_way", "arrived" -> VijdonColors.Blue
    "completed" -> VijdonColors.Green
    "cancelled" -> VijdonColors.Red
    else -> VijdonColors.TextSecondary
}

@Composable
fun OrdersScreen(onOpenOrder: (Int) -> Unit, viewModel: OrdersViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Column(modifier = Modifier.padding(16.dp)) {
            TabHeader(title = "Buyurtmalar", subtitle = "${state.totalCount} ta")
            Spacer(Modifier.height(12.dp))
            OutlinedTextField(
                value = state.q,
                onValueChange = viewModel::onQueryChange,
                placeholder = { Text("Qidirish — mijoz, manzil, haydovchi") },
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
                items(statusFilters) { (value, label) ->
                    val selected = state.status == value
                    Text(
                        label,
                        color = if (selected) VijdonColors.TextOnBlue else VijdonColors.TextSecondary,
                        style = MaterialTheme.typography.labelMedium,
                        modifier = Modifier
                            .background(if (selected) VijdonColors.Blue else VijdonColors.BadgeNeutral, CardShape)
                            .clickable { viewModel.onStatusChange(value) }
                            .padding(horizontal = 14.dp, vertical = 8.dp),
                    )
                }
            }
        }

        when {
            state.loading && state.orders.isEmpty() -> CenteredLoading()
            state.error != null && state.orders.isEmpty() -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
            state.orders.isEmpty() -> Column(Modifier.padding(16.dp)) { Text("Buyurtmalar topilmadi", color = VijdonColors.TextSecondary) }
            else -> LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                items(state.orders, key = { it.id }) { order ->
                    OrderCard(order, onClick = { onOpenOrder(order.id) })
                }
                if (state.hasNext) {
                    item {
                        if (state.loadingMore) {
                            CenteredLoading(modifier = Modifier.height(60.dp))
                        } else {
                            TextButton(onClick = viewModel::loadMore, modifier = Modifier.fillMaxWidth()) {
                                Text("Ko'proq yuklash", color = VijdonColors.Blue)
                            }
                        }
                    }
                }
                item { Spacer(Modifier.height(80.dp)) }
            }
        }
    }
}

@Composable
fun OrderCard(order: OrderDto, onClick: () -> Unit) {
    Column(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(14.dp),
    ) {
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
            Text("#${order.id} — ${order.client_name}", style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
            Pill(order.status_label, color = statusColor(order.status))
        }
        Spacer(Modifier.height(8.dp))
        RouteAddresses(order.from_address, order.to_address)
        Spacer(Modifier.height(8.dp))
        Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
            Text(
                order.driver_name?.let { "Haydovchi: $it" } ?: (order.dispatched_to_name?.let { "Yuborilgan: $it" } ?: "Haydovchi tayinlanmagan"),
                style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary,
            )
            if (order.price != null) {
                Text("${formatMoney(order.price)} so'm", style = MaterialTheme.typography.bodySmall, color = VijdonColors.Green)
            }
        }
    }
}
