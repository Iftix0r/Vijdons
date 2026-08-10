package uz.vijdon.driver.ui.addresses

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class AddressesUiState(
    val addresses: List<AddressDto> = emptyList(),
    val selectedAddress: AddressDto? = null,
    val queueDrivers: List<QueueDriverDto> = emptyList(),
    val myPosition: Int? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class AddressesViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(AddressesUiState())
    val uiState: StateFlow<AddressesUiState> = _uiState.asStateFlow()

    init { load() }

    fun load() {
        viewModelScope.launch {
            when (val result = repository.addresses()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(addresses = result.data, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }

    fun openQueue(address: AddressDto) {
        _uiState.value = _uiState.value.copy(selectedAddress = address)
        viewModelScope.launch {
            val posResult = repository.addressQueuePosition(address.id, null, null)
            val driversResult = repository.addressQueueDrivers(address.id)
            _uiState.value = _uiState.value.copy(
                myPosition = (posResult as? ApiResult.Success)?.data?.position,
                queueDrivers = (driversResult as? ApiResult.Success)?.data ?: emptyList(),
            )
        }
    }

    fun closeQueue() {
        _uiState.value = _uiState.value.copy(selectedAddress = null, queueDrivers = emptyList(), myPosition = null)
    }
}
