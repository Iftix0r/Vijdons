package uz.vijdon.operator.ui.drivers

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

data class DriversUiState(
    val drivers: List<DriverDto> = emptyList(),
    val tab: String = "approved",
    val q: String = "",
    val sort: String? = null,
    val page: Int = 1,
    val hasNext: Boolean = false,
    val pendingCount: Int = 0,
    val approvedCount: Int = 0,
    val rejectedCount: Int = 0,
    val loading: Boolean = true,
    val loadingMore: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class DriversViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(DriversUiState())
    val uiState: StateFlow<DriversUiState> = _uiState.asStateFlow()

    init { load() }

    fun onQueryChange(q: String) {
        _uiState.value = _uiState.value.copy(q = q)
    }

    fun search() = load()

    fun selectTab(tab: String) {
        _uiState.value = _uiState.value.copy(tab = tab)
        load()
    }

    fun refresh() = load()

    fun loadMore() {
        val s = _uiState.value
        if (!s.hasNext || s.loadingMore) return
        viewModelScope.launch {
            _uiState.value = s.copy(loadingMore = true)
            when (val r = repository.drivers(tab = s.tab, q = s.q.ifBlank { null }, sort = s.sort, page = s.page + 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    drivers = _uiState.value.drivers + r.data.drivers, page = r.data.page, hasNext = r.data.has_next, loadingMore = false,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loadingMore = false, error = r.message)
            }
        }
    }

    private fun load() {
        val s = _uiState.value
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            when (val r = repository.drivers(tab = s.tab, q = s.q.ifBlank { null }, sort = s.sort, page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    drivers = r.data.drivers, page = r.data.page, hasNext = r.data.has_next,
                    pendingCount = r.data.pending_count, approvedCount = r.data.approved_count, rejectedCount = r.data.rejected_count,
                    loading = false,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
            }
        }
    }
}
