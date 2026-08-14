package uz.vijdon.operator.ui.dashboard

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.DashboardDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class DashboardUiState(
    val dashboard: DashboardDto? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class DashboardViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(DashboardUiState())
    val uiState: StateFlow<DashboardUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            while (true) {
                load()
                delay(20_000)
            }
        }
    }

    fun refresh() {
        viewModelScope.launch { load() }
    }

    private suspend fun load() {
        when (val r = repository.dashboard()) {
            is ApiResult.Success -> _uiState.value = DashboardUiState(dashboard = r.data, loading = false)
            is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
        }
    }
}
