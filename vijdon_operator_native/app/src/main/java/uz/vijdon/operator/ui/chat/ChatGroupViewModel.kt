package uz.vijdon.operator.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.GroupMessageDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class ChatGroupUiState(
    val messages: List<GroupMessageDto> = emptyList(),
    val loading: Boolean = true,
    val sending: Boolean = false,
    val error: String? = null,
)

/** Barcha haydovchilarga umumiy (broadcast) kanal — `GroupMessage` modeli,
 * `taxi/views.py: operator_chat`dagi "Umumiy" bo'limi bilan bir xil. */
@HiltViewModel
class ChatGroupViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatGroupUiState())
    val uiState: StateFlow<ChatGroupUiState> = _uiState.asStateFlow()

    private var pollJob: Job? = null

    init {
        pollJob = viewModelScope.launch {
            while (true) {
                poll()
                delay(5_000)
            }
        }
    }

    private suspend fun poll() {
        when (val r = repository.chatGroupList()) {
            is ApiResult.Success -> _uiState.value = _uiState.value.copy(messages = r.data, loading = false, error = null)
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
        }
    }

    fun sendMessage(text: String) {
        val trimmed = text.trim()
        if (trimmed.isEmpty() || _uiState.value.sending) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(sending = true, error = null)
            when (val r = repository.chatGroupSend(trimmed)) {
                is ApiResult.Success -> {
                    val messages = (_uiState.value.messages + r.data).distinctBy { it.id }.sortedBy { it.id }
                    _uiState.value = _uiState.value.copy(messages = messages, sending = false)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(sending = false, error = r.message)
            }
        }
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
