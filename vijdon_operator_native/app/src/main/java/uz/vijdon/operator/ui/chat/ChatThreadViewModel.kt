package uz.vijdon.operator.ui.chat

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.ChatMessageDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class ChatThreadUiState(
    val messages: List<ChatMessageDto> = emptyList(),
    val loading: Boolean = true,
    val sending: Boolean = false,
    val error: String? = null,
)

/** Haydovchi bilan operator o'rtasidagi XUSUSIY suhbat — `taxi/views.py:
 * operator_chat` va driverapp'dagi `ChatMessage` modeli bilan bir xil,
 * 4 soniyalik polling (driverapp'dagi ChatViewModel bilan bir xil naqsh). */
@HiltViewModel
class ChatThreadViewModel @Inject constructor(
    private val repository: OperatorRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val driverId: Int = checkNotNull(savedStateHandle["driverId"])

    private val _uiState = MutableStateFlow(ChatThreadUiState())
    val uiState: StateFlow<ChatThreadUiState> = _uiState.asStateFlow()

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
        when (val result = repository.chatMessages(driverId)) {
            is ApiResult.Success -> _uiState.value = _uiState.value.copy(messages = result.data, loading = false, error = null)
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _uiState.value.sending) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(sending = true, error = null)
            when (val result = repository.chatSend(driverId, trimmed)) {
                is ApiResult.Success -> {
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
