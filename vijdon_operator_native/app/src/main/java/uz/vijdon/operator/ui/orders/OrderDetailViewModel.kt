package uz.vijdon.operator.ui.orders

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

data class OrderDetailUiState(
    val order: OrderDto? = null,
    val drivers: List<DriverDto> = emptyList(),
    val loading: Boolean = true,
    val actionLoading: Boolean = false,
    val error: String? = null,
    val deleted: Boolean = false,
)

@HiltViewModel
class OrderDetailViewModel @Inject constructor(
    private val repository: OperatorRepository,
    savedStateHandle: SavedStateHandle,
) : ViewModel() {
    private val orderId: Int = checkNotNull(savedStateHandle["orderId"])

    private val _uiState = MutableStateFlow(OrderDetailUiState())
    val uiState: StateFlow<OrderDetailUiState> = _uiState.asStateFlow()

    init {
        load()
        loadDrivers()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val r = repository.orderDetail(orderId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(order = r.data, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
            }
        }
    }

    private fun loadDrivers() {
        viewModelScope.launch {
            when (val r = repository.drivers(tab = "approved", page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(drivers = r.data.drivers)
                is ApiResult.Error -> Unit
            }
        }
    }

    fun dispatch() = runAction { repository.dispatchOrder(orderId) }

    fun assignDriver(driverId: Int) = runAction { repository.updateOrderStatus(orderId, driverId = driverId) }

    fun setStatus(status: String) = runAction { repository.updateOrderStatus(orderId, status = status) }

    fun cancelAndReopen() = runAction { repository.cancelOrder(orderId) }

    fun delete() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true, error = null)
            when (val r = repository.deleteOrder(orderId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(actionLoading = false, deleted = true)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }

    private fun runAction(block: suspend () -> ApiResult<OrderDto>) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(actionLoading = true, error = null)
            when (val r = block()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(order = r.data, actionLoading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(actionLoading = false, error = r.message)
            }
        }
    }
}
