package uz.vijdon.driver.ui.nearbydrivers

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.NearbyDriverDto
import uz.vijdon.driver.data.location.LocationBus
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject
import kotlin.math.atan2
import kotlin.math.cos
import kotlin.math.sin
import kotlin.math.sqrt

data class NearbyDriversUiState(
    val drivers: List<NearbyDriverDto> = emptyList(),
    val distancesM: Map<Int, Double> = emptyMap(),
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class NearbyDriversViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(NearbyDriversUiState())
    val uiState: StateFlow<NearbyDriversUiState> = _uiState.asStateFlow()

    private var myLat: Double? = null
    private var myLng: Double? = null
    private var pollJob: Job? = null

    init {
        startPolling()
        viewModelScope.launch {
            LocationBus.points.collect { point ->
                myLat = point.lat
                myLng = point.lng
                recomputeDistances()
            }
        }
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                refresh()
                delay(20_000)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch {
            when (val result = repository.nearbyDrivers()) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(drivers = result.data, loading = false, error = null)
                    recomputeDistances()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message, loading = false)
            }
        }
    }

    private fun recomputeDistances() {
        val lat = myLat ?: return
        val lng = myLng ?: return
        val distances = _uiState.value.drivers.associate { it.id to haversineMeters(lat, lng, it.latitude, it.longitude) }
        _uiState.value = _uiState.value.copy(distancesM = distances)
    }

    private fun haversineMeters(lat1: Double, lng1: Double, lat2: Double, lng2: Double): Double {
        val r = 6_371_000.0
        val dLat = Math.toRadians(lat2 - lat1)
        val dLng = Math.toRadians(lng2 - lng1)
        val a = sin(dLat / 2) * sin(dLat / 2) +
            cos(Math.toRadians(lat1)) * cos(Math.toRadians(lat2)) * sin(dLng / 2) * sin(dLng / 2)
        return r * 2 * atan2(sqrt(a), sqrt(1 - a))
    }

    override fun onCleared() {
        pollJob?.cancel()
        super.onCleared()
    }
}
