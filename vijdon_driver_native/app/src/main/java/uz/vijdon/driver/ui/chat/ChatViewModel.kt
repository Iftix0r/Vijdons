package uz.vijdon.driver.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.GroupMessageDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class ChatUiState(
    val messages: List<GroupMessageDto> = emptyList(),
    val loading: Boolean = true,
    val sending: Boolean = false,
    val error: String? = null,
)

/**
 * Haydovchilarning umumiy guruh chati — veb paneldagi `driver_group_chat_list`/
 * `driver_group_chat_send` bilan bir xil g'oya (Telegram uslubidagi polling,
 * har 4 soniyada). `sinceId` orqali faqat YANGI xabarlar so'raladi — butun
 * tarix qayta yuklanmaydi.
 */
@HiltViewModel
class ChatViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

    private var sinceId = 0
    private var pollJob: Job? = null

    init { startPolling() }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                poll()
                delay(4_000)
            }
        }
    }

    private suspend fun poll() {
        when (val result = repository.chatGroupList(sinceId)) {
            is ApiResult.Success -> {
                _uiState.value = _uiState.value.copy(messages = merge(_uiState.value.messages, result.data), loading = false)
            }
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _uiState.value.sending) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(sending = true, error = null)
            when (val result = repository.chatGroupSend(trimmed)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(messages = merge(_uiState.value.messages, listOf(result.data)), sending = false)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(sending = false, error = result.message)
            }
        }
    }

    // Bir xil xabar ikki marta ko'rinib qolmasligi uchun (masalan xabar
    // yuborilgach, keyingi poll ham aynan o'sha xabarni qaytarib yuborishi
    // mumkin edi — id bo'yicha noyoblashtirilib, vaqt tartibida saqlanadi.
    private fun merge(current: List<GroupMessageDto>, incoming: List<GroupMessageDto>): List<GroupMessageDto> {
        if (incoming.isEmpty()) return current
        sinceId = maxOf(sinceId, incoming.maxOf { it.id })
        return (current + incoming).distinctBy { it.id }.sortedBy { it.id }
    }
}
