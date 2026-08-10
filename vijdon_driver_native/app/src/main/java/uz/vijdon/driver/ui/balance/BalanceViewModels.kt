package uz.vijdon.driver.ui.balance

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.BalanceEntryDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import java.io.File
import javax.inject.Inject

data class BalanceHistoryUiState(
    val entries: List<BalanceEntryDto> = emptyList(),
    val balance: String = "0",
    val loading: Boolean = true,
    val error: String? = null,
)

@HiltViewModel
class BalanceHistoryViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(BalanceHistoryUiState())
    val uiState: StateFlow<BalanceHistoryUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            when (val result = repository.balanceHistory()) {
                is ApiResult.Success -> _uiState.value = BalanceHistoryUiState(result.data.entries, result.data.balance, loading = false)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}

data class TopupUiState(val amount: String = "", val loading: Boolean = false, val error: String? = null, val success: Boolean = false)

@HiltViewModel
class TopupViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(TopupUiState())
    val uiState: StateFlow<TopupUiState> = _uiState.asStateFlow()

    fun onAmountChange(v: String) { _uiState.value = _uiState.value.copy(amount = v) }

    fun submit(receiptFile: File) {
        val amount = _uiState.value.amount
        if (amount.isBlank()) {
            _uiState.value = _uiState.value.copy(error = "Summani kiriting.")
            return
        }
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val result = repository.requestTopup(receiptFile, amount)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(loading = false, success = true)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
