package uz.vijdon.driver.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

val HISTORY_PERIODS = listOf("all" to "Barchasi", "today" to "Bugun", "week" to "7 kun", "month" to "30 kun")

data class HistoryUiState(
    val period: String = "all",
    val orders: List<OrderDto> = emptyList(),
    val totalEarned: Double = 0.0,
    val completed: Int = 0,
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class HistoryViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState: StateFlow<HistoryUiState> = _uiState.asStateFlow()

    init { load() }

    fun onPeriodChange(period: String) {
        _uiState.value = _uiState.value.copy(period = period)
        load()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            when (val result = repository.history(_uiState.value.period)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    loading = false, orders = result.data.orders,
                    totalEarned = result.data.total_earned, completed = result.data.completed,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
