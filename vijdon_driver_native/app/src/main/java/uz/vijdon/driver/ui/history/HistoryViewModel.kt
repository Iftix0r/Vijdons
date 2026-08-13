package uz.vijdon.driver.ui.history

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

val HISTORY_PERIODS = listOf("all" to "Barchasi", "today" to "Bugun", "week" to "7 kun", "month" to "30 kun")
val STATUS_TABS = listOf("all" to "Hammasi", "completed" to "Yakunlangan", "cancelled" to "Bekor")

data class HistoryUiState(
    val period: String = "all",
    val statusTab: String = "all",
    val orders: List<OrderDto> = emptyList(),
    val totalEarned: Double = 0.0,
    val completed: Int = 0,
    val loading: Boolean = false,
    val error: String? = null,
) {
    val visibleOrders: List<OrderDto>
        get() = when (statusTab) {
            "completed" -> orders.filter { it.status == "completed" }
            "cancelled" -> orders.filter { it.status == "cancelled" }
            else -> orders
        }

    val totalKm: Double
        get() = orders.filter { it.status == "completed" }.sumOf { it.distance_km ?: 0.0 }
}

@HiltViewModel
class HistoryViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(HistoryUiState())
    val uiState: StateFlow<HistoryUiState> = _uiState.asStateFlow()

    init { load() }

    fun onPeriodChange(period: String) {
        _uiState.value = _uiState.value.copy(period = period)
        load()
    }

    fun onStatusTabChange(tab: String) {
        _uiState.value = _uiState.value.copy(statusTab = tab)
    }

    private var loadJob: Job? = null

    fun load() {
        // Diqqat: oldingi so'rov BEKOR qilinadi — aks holda davr tez-tez
        // almashtirilsa (masalan "Bugun" -> "7 kun"), ikkalasi ham parallel
        // so'raladi va agar ESKI davr javobi YANGISIDAN keyin kelib qolsa
        // (tarmoqda tartib kafolatlanmagan), ekranda tanlangan davr bilan
        // mos kelmaydigan (eski) ma'lumot ko'rsatilib qolardi.
        loadJob?.cancel()
        loadJob = viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            when (val result = repository.history(_uiState.value.period)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    loading = false, error = null, orders = result.data.orders,
                    totalEarned = result.data.total_earned, completed = result.data.completed,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
