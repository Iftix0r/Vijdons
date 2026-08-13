package uz.vijdon.driver.ui.chat

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.PaddingValues
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
import androidx.compose.material.icons.rounded.Forum
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
import androidx.compose.ui.text.style.TextAlign
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import androidx.hilt.navigation.compose.hiltViewModel
import uz.vijdon.driver.data.api.ChatMessageDto
import uz.vijdon.driver.ui.theme.CenteredLoading
import uz.vijdon.driver.ui.theme.ChipShape
import uz.vijdon.driver.ui.theme.ErrorBanner
import uz.vijdon.driver.ui.theme.TabHeader
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Haydovchi bilan operator o'rtasidagi XUSUSIY suhbat — veb paneldagi
 * operator panelining "Chat" bo'limi bilan bir xil g'oya. Boshqa
 * haydovchilar bu xabarlarni ko'rmaydi.
 */
@Composable
fun ChatScreen(viewModel: ChatViewModel = hiltViewModel()) {
    val state by viewModel.uiState.collectAsState()
    var input by remember { mutableStateOf("") }
    val listState = rememberLazyListState()

    LaunchedEffect(state.messages.size) {
        if (state.messages.isNotEmpty()) listState.animateScrollToItem(state.messages.lastIndex)
    }

    Column(modifier = Modifier.fillMaxSize().background(VijdonColors.Background)) {
        TabHeader(
            "Chat",
            subtitle = "Operator bilan suhbat",
            modifier = Modifier.padding(horizontal = 16.dp, vertical = 16.dp).padding(bottom = 0.dp),
        )

        Box(modifier = Modifier.weight(1f).fillMaxWidth()) {
            when {
                state.loading && state.messages.isEmpty() -> CenteredLoading()
                state.messages.isEmpty() -> EmptyChatState()
                else -> {
                    LazyColumn(
                        state = listState,
                        modifier = Modifier.fillMaxSize(),
                        contentPadding = PaddingValues(horizontal = 16.dp, vertical = 12.dp),
                        verticalArrangement = Arrangement.spacedBy(8.dp),
                    ) {
                        items(state.messages, key = { it.id }) { msg -> ChatBubble(msg) }
                    }
                }
            }
        }

        state.error?.let {
            ErrorBanner(it, modifier = Modifier.padding(horizontal = 16.dp, vertical = 4.dp))
        }

        ChatInputRow(
            value = input,
            onValueChange = { input = it },
            onSend = {
                if (input.isNotBlank()) {
                    viewModel.sendMessage(input)
                    input = ""
                }
            },
            sending = state.sending,
        )
    }
}

@Composable
private fun EmptyChatState() {
    Box(modifier = Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally) {
            Box(
                modifier = Modifier.size(72.dp).background(VijdonColors.BadgeNeutral, CircleShape),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.Rounded.Forum, contentDescription = null, tint = VijdonColors.TextSecondary, modifier = Modifier.size(32.dp))
            }
            Spacer(Modifier.height(12.dp))
            Text("Hali xabar yo'q", color = VijdonColors.TextPrimary, style = MaterialTheme.typography.titleMedium)
            Spacer(Modifier.height(4.dp))
            Text(
                "Operatorga birinchi bo'lib yozing",
                color = VijdonColors.TextSecondary,
                style = MaterialTheme.typography.bodySmall,
                textAlign = TextAlign.Center,
            )
        }
    }
}

private val BubbleShape = RoundedCornerShape(16.dp)

@Composable
private fun ChatBubble(msg: ChatMessageDto) {
    val isMe = msg.isFromDriver
    Row(modifier = Modifier.fillMaxWidth(), horizontalArrangement = if (isMe) Arrangement.End else Arrangement.Start) {
        Column(
            modifier = Modifier
                .widthIn(max = 280.dp)
                .background(if (isMe) VijdonColors.Yellow else VijdonColors.Surface, BubbleShape)
                .padding(horizontal = 12.dp, vertical = 8.dp),
        ) {
            // Operator yozgan xabarda kim yozganini bilish uchun — o'zingizning
            // xabaringizda bu shart emas, u allaqachon o'ngga tekislangan
            // sariq pufakcha bilan ajralib turibdi.
            if (!isMe) {
                Text(
                    "Operator",
                    color = VijdonColors.Blue,
                    style = MaterialTheme.typography.labelSmall.copy(fontWeight = FontWeight.Bold),
                )
                Spacer(Modifier.height(2.dp))
            }
            Text(
                msg.text,
                color = if (isMe) VijdonColors.TextOnYellow else VijdonColors.TextPrimary,
                style = MaterialTheme.typography.bodyMedium,
            )
            Spacer(Modifier.height(2.dp))
            Text(
                formatChatTime(msg.created_at),
                color = if (isMe) VijdonColors.TextOnYellow.copy(alpha = 0.6f) else VijdonColors.TextSecondary,
                style = MaterialTheme.typography.labelSmall.copy(fontSize = 10.sp),
                modifier = Modifier.align(Alignment.End),
            )
        }
    }
}

/** Server "yyyy-MM-ddTHH:mm:ss..." beradi — faqat "soat:daqiqa" kerak. */
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
            modifier = Modifier
                .size(46.dp)
                .background(if (canSend) VijdonColors.Yellow else VijdonColors.BadgeNeutral, CircleShape),
        ) {
            if (sending) {
                CircularProgressIndicator(modifier = Modifier.size(18.dp), color = VijdonColors.TextOnYellow, strokeWidth = 2.dp)
            } else {
                Icon(
                    Icons.AutoMirrored.Rounded.Send,
                    contentDescription = "Yuborish",
                    tint = if (canSend) VijdonColors.TextOnYellow else VijdonColors.TextSecondary,
                )
            }
        }
    }
}
