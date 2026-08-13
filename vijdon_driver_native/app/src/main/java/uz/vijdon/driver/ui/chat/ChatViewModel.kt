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
import uz.vijdon.driver.data.api.ChatMessageDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class ChatUiState(
    val messages: List<ChatMessageDto> = emptyList(),
    val loading: Boolean = true,
    val sending: Boolean = false,
    val error: String? = null,
)

/**
 * Haydovchi bilan operator o'rtasidagi XUSUSIY suhbat — veb paneldagi
 * `operator_chat` (`taxi/views.py`) bilan bir xil `ChatMessage` modeli
 * (Telegram uslubidagi polling, har 4 soniyada). Boshqa haydovchilar bu
 * xabarlarni ko'rmaydi (avval bu bo'lim BARCHA haydovchilar ko'radigan
 * umumiy guruh chati edi — endi faqat operator bilan bitta-bittaga suhbat).
 */
@HiltViewModel
class ChatViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatUiState())
    val uiState: StateFlow<ChatUiState> = _uiState.asStateFlow()

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
        // Diqqat: avvalgi guruh chatidan farqli o'laroq, server har safar
        // BUTUN (so'nggi 100 ta) suhbatni qaytaradi — `since_id` kabi
        // qisman yuklash yo'q, shu sabab natija shunchaki almashtiriladi.
        when (val result = repository.chatList()) {
            is ApiResult.Success -> {
                _uiState.value = _uiState.value.copy(messages = result.data, loading = false, error = null)
            }
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _uiState.value.sending) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(sending = true, error = null)
            when (val result = repository.chatSend(trimmed)) {
                is ApiResult.Success -> {
                    // Keyingi poll (4s ichida) baribir haqiqiy ro'yxatni
                    // qaytaradi — shu oraliqda yuborilgan xabar darhol
                    // ko'rinishi uchun mahalliy ravishda qo'shib qo'yiladi.
                    val messages = (_uiState.value.messages + result.data).distinctBy { it.id }.sortedBy { it.id }
                    _uiState.value = _uiState.value.copy(messages = messages, sending = false)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(sending = false, error = result.message)
            }
        }
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
