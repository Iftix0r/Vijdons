package uz.vijdon.operator.ui.drivers

import androidx.lifecycle.SavedStateHandle
import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.data.api.OrderDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class DriverDetailUiState(
    val driver: DriverDto? = null,
    val recentOrders: List<OrderDto> = emptyList(),
    val loading: Boolean = true,
    val actionLoading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class DriverDetailViewModel @Inject constructor(
    private val repository: OperatorRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val driverId: Int = checkNotNull(savedStateHandle["driverId"])

    private val _uiState = MutableStateFlow(DriverDetailUiState())
    val uiState: StateFlow<DriverDetailUiState> = _uiState.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val r = repository.driverDetail(driverId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(driver = r.data.driver, recentOrders = r.data.recent_orders, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
            }
        }
    }

    fun approve(approve: Boolean) = runAction { repository.driverApprove(driverId, approve) }

    fun toggleActive() = runAction { repository.driverToggleActive(driverId) }

    fun toggleFrozen() = runAction { repository.driverToggleFrozen(driverId) }

    fun recharge(amount: String, deduct: Boolean, note: String, onDone: () -> Unit) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true, error = null)
            when (val r = repository.driverRecharge(driverId, amount, deduct, note)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(driver = r.data, actionLoading = false)
                    onDone()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }

    private fun runAction(block: suspend () -> ApiResult<DriverDto>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true, error = null)
            when (val r = block()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(driver = r.data, actionLoading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }
}
