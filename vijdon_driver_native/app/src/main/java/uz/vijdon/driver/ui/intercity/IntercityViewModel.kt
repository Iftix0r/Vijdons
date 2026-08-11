package uz.vijdon.driver.ui.intercity

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.IntercityRouteDto
import uz.vijdon.driver.data.api.IntercityTripDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class IntercityUiState(
    val routes: List<IntercityRouteDto> = emptyList(),
    val myTrip: IntercityTripDto? = null,
    val loading: Boolean = true,
    val joiningRouteId: Int? = null,
    val error: String? = null,
)

/**
 * Shahrlararo (viloyatlararo) yo'lovchi tashish — haydovchi bitta
 * yo'nalishga "qo'shiladi" (safar boshlaydi yoki operator ochib qo'ygan
 * haydovchisiz safarga ega chiqadi), mijozlar operator panelidan (hozircha)
 * joy-joy band qiladi. `myTrip` mavjud ekan — 10 soniyada bir yangilanib
 * turadi (yo'lovchilar soni o'zgarib turishi mumkin).
 */
@HiltViewModel
class IntercityViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(IntercityUiState())
    val uiState: StateFlow<IntercityUiState> = _uiState.asStateFlow()

    private var pollJob: Job? = null

    init {
        load()
        startPolling()
    }

    fun load() {
        viewModelScope.launch {
            val routesResult = repository.intercityRoutes()
            val tripResult = repository.intercityMyTrip()
            _uiState.value = _uiState.value.copy(
                routes = (routesResult as? ApiResult.Success)?.data ?: _uiState.value.routes,
                myTrip = (tripResult as? ApiResult.Success)?.data,
                loading = false,
                error = (routesResult as? ApiResult.Error)?.message ?: (tripResult as? ApiResult.Error)?.message,
            )
        }
    }

    private fun startPolling() {
        pollJob?.cancel()
        pollJob = viewModelScope.launch {
            while (true) {
                delay(10_000L)
                val result = repository.intercityMyTrip()
                if (result is ApiResult.Success) _uiState.value = _uiState.value.copy(myTrip = result.data)
            }
        }
    }

    fun join(routeId: Int) {
        if (_uiState.value.joiningRouteId != null) return
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(joiningRouteId = routeId, error = null)
            when (val result = repository.intercityJoin(routeId)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(myTrip = result.data, joiningRouteId = null)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(joiningRouteId = null, error = result.message)
            }
        }
    }

    fun depart() {
        viewModelScope.launch {
            when (val result = repository.intercityDepart()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(myTrip = null)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }

    fun cancel() {
        viewModelScope.launch {
            when (val result = repository.intercityCancel()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(myTrip = null)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }
}
