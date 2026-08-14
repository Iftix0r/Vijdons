package uz.vijdon.operator.ui.orders

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.api.OrderDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

data class OrdersUiState(
    val orders: List<OrderDto> = emptyList(),
    val q: String = "",
    val status: String? = null,
    val page: Int = 1,
    val hasNext: Boolean = false,
    val totalCount: Int = 0,
    val loading: Boolean = true,
    val loadingMore: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class OrdersViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(OrdersUiState())
    val uiState: StateFlow<OrdersUiState> = _uiState.asStateFlow()

    init {
        load()
    }

    fun onQueryChange(q: String) {
        _uiState.value = _uiState.value.copy(q = q)
    }

    fun onStatusChange(status: String?) {
        _uiState.value = _uiState.value.copy(status = status)
        load()
    }

    fun search() = load()

    fun refresh() = load()

    fun loadMore() {
        val s = _uiState.value
        if (!s.hasNext || s.loadingMore) return
        viewModelScope.launch {
            _uiState.value = s.copy(loadingMore = true)
            when (val r = repository.orders(q = s.q.ifBlank { null }, status = s.status, page = s.page + 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    orders = _uiState.value.orders + r.data.orders,
                    page = r.data.page, hasNext = r.data.has_next, totalCount = r.data.total_count, loadingMore = false,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loadingMore = false, error = r.message)
            }
        }
    }

    private fun load() {
        val s = _uiState.value
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            when (val r = repository.orders(q = s.q.ifBlank { null }, status = s.status, page = 1)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    orders = r.data.orders, page = r.data.page, hasNext = r.data.has_next,
                    totalCount = r.data.total_count, loading = false,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = r.message)
            }
        }
    }
}
