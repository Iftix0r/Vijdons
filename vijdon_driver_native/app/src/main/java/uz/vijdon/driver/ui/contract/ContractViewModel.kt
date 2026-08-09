package uz.vijdon.driver.ui.contract

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import java.io.File
import javax.inject.Inject

data class ContractUiState(
    val title: String = "",
    val content: String = "",
    val version: Int = 1,
    val signed: Boolean = false,
    val loading: Boolean = true,
    val submitting: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class ContractViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ContractUiState())
    val uiState: StateFlow<ContractUiState> = _uiState.asStateFlow()

    init {
        viewModelScope.launch {
            when (val result = repository.contract()) {
                is ApiResult.Success -> _uiState.value = ContractUiState(
                    title = result.data.title, content = result.data.content,
                    version = result.data.version, signed = result.data.signed, loading = false,
                )
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }

    fun sign(signatureFile: File) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(submitting = true, error = null)
            when (val result = repository.signContract(signatureFile)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(submitting = false, signed = true)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(submitting = false, error = result.message)
            }
        }
    }
}
