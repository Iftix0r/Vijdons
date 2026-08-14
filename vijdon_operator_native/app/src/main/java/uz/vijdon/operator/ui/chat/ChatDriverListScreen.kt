package uz.vijdon.operator.ui.chat

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
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Chat
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
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.data.api.ChatDriverSummaryDto
import uz.vijdon.operator.ui.theme.CardShape
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.TabHeader
import uz.vijdon.operator.ui.theme.VijdonColors
import uz.vijdon.operator.ui.theme.cardShadow

@Composable
fun ChatDriverListScreen(
    onOpenThread: (Int, String) -> Unit,
    onOpenGroup: () -> Unit,
    viewModel: ChatDriverListViewModel = hiltViewModel(),
) {
    val state by viewModel.uiState.collectAsState()

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Column(modifier = Modifier.padding(16.dp)) {
            TabHeader(title = "Chat", subtitle = "Haydovchilar bilan suhbat")
        }
        when {
            state.loading && state.drivers.isEmpty() -> CenteredLoading()
            state.error != null && state.drivers.isEmpty() -> Column(Modifier.padding(16.dp)) { ErrorBanner(state.error!!) }
            else -> LazyColumn(
                contentPadding = PaddingValues(horizontal = 16.dp, vertical = 8.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp),
            ) {
                item { GroupChatRow(onClick = onOpenGroup) }
                items(state.drivers, key = { it.driver_id }) { d ->
                    DriverChatRow(d, onClick = { onOpenThread(d.driver_id, d.full_name) })
                }
                item { Spacer(Modifier.height(60.dp)) }
            }
        }
    }
}

@Composable
private fun GroupChatRow(onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Avatar(icon = true)
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text("Barcha haydovchilar", style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
            Text("Umumiy e'lon/xabar yuborish", style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary)
        }
    }
}

@Composable
private fun DriverChatRow(d: ChatDriverSummaryDto, onClick: () -> Unit) {
    Row(
        modifier = Modifier
            .fillMaxWidth()
            .cardShadow()
            .background(VijdonColors.Surface, CardShape)
            .clickable(onClick = onClick)
            .padding(14.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        Avatar(icon = false)
        Spacer(Modifier.width(12.dp))
        Column(modifier = Modifier.weight(1f)) {
            Text(d.full_name, style = MaterialTheme.typography.titleSmall.copy(fontWeight = FontWeight.Bold), color = VijdonColors.TextPrimary)
            Text(
                d.last_message?.text?.ifBlank { "Hali xabar yo'q" } ?: "Hali xabar yo'q",
                style = MaterialTheme.typography.bodySmall, color = VijdonColors.TextSecondary, maxLines = 1,
            )
        }
        if (d.unread > 0) {
            Box(
                modifier = Modifier.size(22.dp).background(VijdonColors.Red, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Text(
                    if (d.unread > 99) "99+" else d.unread.toString(),
                    color = androidx.compose.ui.graphics.Color.White,
                    fontSize = 10.sp,
                )
            }
        }
    }
}

@Composable
private fun Avatar(icon: Boolean) {
    Box(
        modifier = Modifier.size(44.dp).background(VijdonColors.Blue.copy(alpha = 0.15f), CircleShape),
        contentAlignment = Alignment.Center,
    ) {
        Icon(Icons.AutoMirrored.Rounded.Chat, contentDescription = null, tint = VijdonColors.Blue, modifier = Modifier.padding(10.dp))
    }
}
