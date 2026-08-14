package uz.vijdon.operator.ui.balance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.launch
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import uz.vijdon.operator.data.api.BalanceLogEntryDto
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.data.api.TopupDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class BalanceUiState(
    val tab: Int = 0, // 0 = so'rovlar, 1 = tarix
    val topups: List<TopupDto> = emptyList(),
    val pendingCount: Int = 0,
    val log: List<BalanceLogEntryDto> = emptyList(),
    val logHasNext: Boolean = false,
    val logPage: Int = 1,
    val drivers: List<DriverDto> = emptyList(),
    val loading: Boolean = true,
    val actionLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class BalanceViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(BalanceUiState())
    val uiState: StateFlow<BalanceUiState> = _uiState.asStateFlow()

    init {
        loadTopups()
        loadLog()
        loadDrivers()
    }

    fun selectTab(tab: Int) {
        _uiState.value = _uiState.value.copy(tab = tab)
    }

    fun refresh() {
        loadTopups()
        loadLog()
    }

    private fun loadDrivers() {
        viewModelScope.launch {
            when (val r = repository.drivers(tab = "approved", page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(drivers = r.data.drivers)
                is ApiResult.Error -> Unit
            }
        }
    }

    private fun loadTopups() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val r = repository.topups(status = "pending")) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(topups = r.data.requests, pendingCount = r.data.pending_count, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
            }
        }
    }

    private fun loadLog() {
        viewModelScope.launch {
            when (val r = repository.balanceLog(page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(log = r.data.entries, logPage = r.data.page, logHasNext = r.data.has_next)
                is ApiResult.Error -> Unit
            }
        }
    }

    fun loadMoreLog() {
        val s = _uiState.value
        if (!s.logHasNext) return
        viewModelScope.launch {
            when (val r = repository.balanceLog(page = s.logPage + 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(log = _uiState.value.log + r.data.entries, logPage = r.data.page, logHasNext = r.data.has_next)
                is ApiResult.Error -> Unit
            }
        }
    }

    fun resolveTopup(id: Int, approve: Boolean, reason: String = "") {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true)
            when (val r = repository.topupResolve(id, approve, reason)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(actionLoading = false, topups = _uiState.value.topups.filterNot { it.id == id })
                    loadLog()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }

    fun recharge(driverId: Int, amount: String, deduct: Boolean, note: String, onDone: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true, error = null)
            when (val r = repository.driverRecharge(driverId, amount, deduct, note)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(actionLoading = false)
                    loadLog()
                    onDone()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }
}
