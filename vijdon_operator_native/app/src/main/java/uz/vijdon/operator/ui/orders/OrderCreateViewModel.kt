package uz.vijdon.operator.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class OrderCreateUiState(
    val phone: String = "",
    val customerName: String = "",
    val fromAddress: String = "",
    val toAddress: String = "",
    val note: String = "",
    val isDelivery: Boolean = false,
    val paymentType: String = "cash",
    val carType: String = "light",
    val driverId: Int? = null,
    val drivers: List<DriverDto> = emptyList(),
    val loading: Boolean = false,
    val error: String? = null,
    val created: Boolean = false,
)

@HiltViewModel
class OrderCreateViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(OrderCreateUiState())
    val uiState: StateFlow<OrderCreateUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            when (val r = repository.drivers(tab = "approved", page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(drivers = r.data.drivers)
                is ApiResult.Error -> Unit
            }
        }
    }

    fun update(block: (OrderCreateUiState) -> OrderCreateUiState) {
        _uiState.value = block(_uiState.value)
    }

    fun submit() {
        val s = _uiState.value
        if (s.phone.isBlank() || s.fromAddress.isBlank()) {
            _uiState.value = s.copy(error = "Mijoz raqami va manzil kiritilishi shart.")
            return
        }
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            val result = repository.createOrder(
                phone = s.phone.trim(), customerName = s.customerName.trim(),
                fromAddress = s.fromAddress.trim(), toAddress = s.toAddress.trim(),
                fromLat = null, fromLng = null, toLat = null, toLng = null,
                driverId = s.driverId, paymentType = s.paymentType, carType = s.carType,
                isDelivery = s.isDelivery, note = s.note.trim(),
            )
            when (result) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(loading = false, created = true)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
