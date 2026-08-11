package uz.vijdon.driver.ui.addresses

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.data.api.RegionDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class AddressesUiState(
    val addresses: List<AddressDto> = emptyList(),
    val regions: List<RegionDto> = emptyList(),
    val searchQuery: String = "",
    val selectedRegionId: Int? = null,
    val selectedDistrictId: Int? = null,
    val selectedAddress: AddressDto? = null,
    val queueDrivers: List<QueueDriverDto> = emptyList(),
    val myPosition: Int? = null,
    val loading: Boolean = true,
    val error: String? = null,
) {
    // O'zbekiston bo'ylab manzillar ko'payishi bilan — bu ekran endi
    // FAQAT yaqin atrofdagilarni emas, qidiruv/hudud filtri orqali
    // butun ro'yxatni ko'rsata oladi. Filtr faol ekanini ekranda
    // ko'rsatish uchun.
    val hasActiveFilter: Boolean get() = selectedRegionId != null || searchQuery.isNotBlank()
    val selectedRegion: RegionDto? get() = regions.firstOrNull { it.id == selectedRegionId }
}

@HiltViewModel
class AddressesViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(AddressesUiState())
    val uiState: StateFlow<AddressesUiState> = _uiState.asStateFlow()

    private var searchDebounceJob: Job? = null

    init {
        load()
        loadRegions()
    }

    fun load() {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true)
            val state = _uiState.value
            when (
                val result = repository.addresses(
                    region = state.selectedRegionId,
                    district = state.selectedDistrictId,
                    q = state.searchQuery.trim().ifBlank { null },
                )
            ) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(addresses = result.data, loading = false, error = null)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }

    private fun loadRegions() {
        viewModelScope.launch {
            val result = repository.regions()
            if (result is ApiResult.Success) _uiState.value = _uiState.value.copy(regions = result.data)
        }
    }

    /** Har harf terilganda so'rov yubormaslik uchun — yozish to'xtagach
     * (400ms) so'raladi. */
    fun onSearchQueryChange(query: String) {
        _uiState.value = _uiState.value.copy(searchQuery = query)
        searchDebounceJob?.cancel()
        searchDebounceJob = viewModelScope.launch {
            delay(400)
            load()
        }
    }

    fun onRegionSelected(regionId: Int?) {
        if (regionId == _uiState.value.selectedRegionId) return
        _uiState.value = _uiState.value.copy(selectedRegionId = regionId, selectedDistrictId = null)
        load()
    }

    fun onDistrictSelected(districtId: Int?) {
        if (districtId == _uiState.value.selectedDistrictId) return
        _uiState.value = _uiState.value.copy(selectedDistrictId = districtId)
        load()
    }

    fun clearFilters() {
        searchDebounceJob?.cancel()
        _uiState.value = _uiState.value.copy(selectedRegionId = null, selectedDistrictId = null, searchQuery = "")
        load()
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
