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
import uz.vijdon.operator.data.api.ChatDriverSummaryDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class ChatDriverListUiState(
    val drivers: List<ChatDriverSummaryDto> = emptyList(),
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class ChatDriverListViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ChatDriverListUiState())
    val uiState: StateFlow<ChatDriverListUiState> = _uiState.asStateFlow()

    private var pollJob: Job? = null

    init {
        pollJob = viewModelScope.launch {
            while (true) {
                poll()
                delay(6_000)
            }
        }
    }

    private suspend fun poll() {
        when (val r = repository.chatDriverList()) {
            is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                drivers = r.data.sortedByDescending { it.last_message?.created_at ?: "" }, loading = false, error = null,
            )
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
        }
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
