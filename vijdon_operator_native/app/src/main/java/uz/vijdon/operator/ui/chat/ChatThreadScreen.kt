package uz.vijdon.operator.ui.chat

import androidx.compose.foundation.background
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
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.Send
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.OutlinedTextFieldDefaults
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.collectAsState
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.operator.data.api.ChatMessageDto
import uz.vijdon.operator.ui.theme.CenteredLoading
import uz.vijdon.operator.ui.theme.ChipShape
import uz.vijdon.operator.ui.theme.ErrorBanner
import uz.vijdon.operator.ui.theme.ScreenHeader
import uz.vijdon.operator.ui.theme.VijdonColors

@Composable
fun ChatThreadScreen(driverId: Int, driverName: String, onBack: () -> Unit, viewModel: ChatThreadViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) listState.animateScrollToItem(state.messages.lastIndex)
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        Box(modifier = Modifier.padding(16.dp)) {
            ScreenHeader(title = driverName, subtitle = "Haydovchi bilan suhbat", onBack = onBack)
        }

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            when {
                state.loading && state.messages.isEmpty() -> CenteredLoading()
                state.messages.isEmpty() -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                    Text("Hali xabar yo'q", color = VijdonColors.TextSecondary)
                }
                else -> LazyColumn(
                    state = listState,
                    modifier = Modifier.fillMaxSize(),
                    contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp),
                ) {
                    items(state.messages, key = { it.id }) { msg -> ChatBubble(msg) }
                }
            }
        }

        state.error?.let { ErrorBanner(it, modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp)) }

        ChatInputRow(
            value = input,
            onValueChange = { input = it },
            onSend = { if (input.isNotBlank()) { viewModel.sendMessage(input); input = "" } },
            sending = state.sending,
        )
    }
}

private val BubbleShape = RoundedCornerShape(16.dp)

@Composable
private fun ChatBubble(msg: ChatMessageDto) {
    val isMe = !msg.isFromDriver
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isMe) Arrangement.End else Arrangement.Start) {
        Column(
            modifier = Modifier
                .widthIn(max = 280.dp)
                .background(if (isMe) VijdonColors.Blue else VijdonColors.Surface, BubbleShape)
                .padding(horizontal = 12.dp, vertical = 8.dp),
        ) {
            Text(
                msg.text,
                color = if (isMe) VijdonColors.TextOnBlue else VijdonColors.TextPrimary,
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                formatChatTime(msg.created_at),
                color = if (isMe) VijdonColors.TextOnBlue.copy(alpha = 0.7f) else VijdonColors.TextSecondary,
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                modifier = Modifier.align(Alignment.End),
            )
        }
    }
}

private fun formatChatTime(iso: String): String = if (iso.length >= 16) iso.substring(11, 16) else iso

@Composable
private fun ChatInputRow(value: String, onValueChange: (String) -> Unit, onSend: () -> Unit, sending: Boolean) {
    Row(
        modifier = Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 8.dp),
        verticalAlignment = Alignment.CenterVertically,
    ) {
        OutlinedTextField(
            value = value,
            onValueChange = onValueChange,
            modifier = Modifier.weight(1f),
            placeholder = { Text("Xabar yozing...") },
            maxLines = 4,
            shape = ChipShape,
            colors = OutlinedTextFieldDefaults.colors(
                focusedContainerColor = VijdonColors.Surface, unfocusedContainerColor = VijdonColors.Surface,
                focusedTextColor = VijdonColors.TextPrimary, unfocusedTextColor = VijdonColors.TextPrimary,
            ),
        )
        Spacer(Modifier.width(8.dp))
        val canSend = value.isNotBlank() && !sending
        IconButton(
            onClick = onSend,
            enabled = canSend,
            modifier = Modifier.size(46.dp).background(if (canSend) VijdonColors.Blue else VijdonColors.BadgeNeutral, CircleShape),
        ) {
            if (sending) {
                CircularProgressIndicator(modifier = Modifier.size(18.dp), color = VijdonColors.TextOnBlue, strokeWidth = 2.dp)
            } else {
                Icon(
                    Icons.AutoMirrored.Rounded.Send,
                    contentDescription = "Yuborish",
                    tint = if (canSend) VijdonColors.TextOnBlue else VijdonColors.TextSecondary,
                )
            }
        }
    }
}
