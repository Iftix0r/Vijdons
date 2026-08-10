package uz.vijdon.driver.ui.destination

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class DestinationUiState(
    val driver: DriverDto? = null,
    val savedAddresses: List<AddressDto> = emptyList(),
    val loading: Boolean = true,
    val submitting: Boolean = false,
    val error: String? = null,
)

/**
 * "Yo'nalish rejimi" — haydovchi masalan uyiga qaytayotganda yoqib qo'ysa,
 * faqat o'sha yo'nalishdagi (server: 5km radius, `_visible_orders_qs` /
 * `driver_views.py`) buyurtmalar ko'rsatiladi. Xarita bo'yicha erkin nuqta
 * tanlash hozircha yo'q (native ilovada xarita ulanmagan) — shu sabab
 * saqlangan manzillardan biri "yo'nalish" sifatida tanlanadi, bu ham
 * aniq koordinata (lat/lng) berib, serverga yetarli.
 */
@HiltViewModel
class DestinationViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(DestinationUiState())
    val uiState: StateFlow<DestinationUiState> = _uiState.asStateFlow()

    init {
        refresh()
        viewModelScope.launch {
            val result = repository.addresses()
            if (result is ApiResult.Success) {
                _uiState.value = _uiState.value.copy(savedAddresses = result.data)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            when (val result = repository.me()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(driver = result.data, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message, loading = false)
            }
        }
    }

    fun activate(address: AddressDto) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(submitting = true, error = null)
            when (val result = repository.setDestination(address.lat, address.lng, address.name)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        submitting = false,
                        driver = _uiState.value.driver?.copy(
                            destination_mode = true, destination_lat = address.lat,
                            destination_lng = address.lng, destination_address = address.name,
                        ),
                    )
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(submitting = false, error = result.message)
            }
        }
    }

    fun clear() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(submitting = true, error = null)
            when (val result = repository.clearDestination()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(
                        submitting = false,
                        driver = _uiState.value.driver?.copy(
                            destination_mode = false, destination_lat = null,
                            destination_lng = null, destination_address = "",
                        ),
                    )
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(submitting = false, error = result.message)
            }
        }
    }
}
