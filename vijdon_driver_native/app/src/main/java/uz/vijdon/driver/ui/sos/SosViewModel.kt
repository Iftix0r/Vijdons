package uz.vijdon.driver.ui.sos

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class SosUiState(val note: String = "", val loading: Boolean = false, val sent: Boolean = false, val error: String? = null)

@HiltViewModel
class SosViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(SosUiState())
    val uiState: StateFlow<SosUiState> = _uiState.asStateFlow()

    fun onNoteChange(v: String) { _uiState.value = _uiState.value.copy(note = v) }

    fun send(lat: Double?, lng: Double?) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(loading = true, error = null)
            when (val result = repository.sendSos(lat, lng, _uiState.value.note)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(loading = false, sent = true)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
