package uz.vijdon.driver.ui.ordercreate

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class OrderCreateUiState(
    val phone: String = "",
    val toAddress: String = "",
    val savedAddresses: List<AddressDto> = emptyList(),
    val selectedAddressName: String? = null,
    val customFromAddress: String = "",
    val useCustomAddress: Boolean = false,
    val assignToSelf: Boolean = true,
    val loading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
)

@HiltViewModel
class OrderCreateViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(OrderCreateUiState())
    val uiState: StateFlow<OrderCreateUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            val result = repository.addresses()
            if (result is ApiResult.Success) {
                _uiState.value = _uiState.value.copy(savedAddresses = result.data)
            }
        }
    }

    fun onPhoneChange(v: String) { _uiState.value = _uiState.value.copy(phone = v) }
    fun onToAddressChange(v: String) { _uiState.value = _uiState.value.copy(toAddress = v) }
    fun onCustomFromAddressChange(v: String) { _uiState.value = _uiState.value.copy(customFromAddress = v) }
    fun selectAddress(name: String) { _uiState.value = _uiState.value.copy(selectedAddressName = name, useCustomAddress = false) }
    fun selectCustom() { _uiState.value = _uiState.value.copy(useCustomAddress = true, selectedAddressName = null) }
    fun setAssignToSelf(self: Boolean) { _uiState.value = _uiState.value.copy(assignToSelf = self) }

    fun submit() {
        val s = _uiState.value
        val fromAddress = if (s.useCustomAddress) s.customFromAddress else s.selectedAddressName
        if (s.phone.isBlank() || fromAddress.isNullOrBlank()) {
            _uiState.value = s.copy(error = "Mijoz raqami va manzilni to'ldiring.")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            val result = repository.createOrder(
                phone = s.phone.trim(),
                customerName = "",
                toAddress = s.toAddress.trim(),
                fromAddress = fromAddress,
                assignTo = if (s.assignToSelf) "self" else "others",
            )
            _uiState.value = when (result) {
                is ApiResult.Success -> _uiState.value.copy(loading = false, success = true)
                is ApiResult.Error -> _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
