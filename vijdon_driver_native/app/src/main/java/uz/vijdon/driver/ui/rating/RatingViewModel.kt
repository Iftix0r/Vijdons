package uz.vijdon.driver.ui.rating

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.RatingRowDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class RatingUiState(
    val rows: List<RatingRowDto> = emptyList(),
    val myRow: RatingRowDto? = null,
    val gapToNext: Int? = null,
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class RatingViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(RatingUiState())
    val uiState: StateFlow<RatingUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            when (val result = repository.rating()) {
                is ApiResult.Success -> _uiState.value = RatingUiState(result.data.rows, result.data.my_row, result.data.gap_to_next, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
