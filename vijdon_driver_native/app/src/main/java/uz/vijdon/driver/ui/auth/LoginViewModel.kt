package uz.vijdon.driver.ui.auth

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

data class LoginUiState(
    val phone: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun onPhoneChange(v: String) { _uiState.value = _uiState.value.copy(phone = v, error = null) }
    fun onPasswordChange(v: String) { _uiState.value = _uiState.value.copy(password = v, error = null) }

    fun login(onSuccess: (DriverDto) -> Unit) {
        val s = _uiState.value
        if (s.phone.isBlank() || s.password.isBlank()) {
            _uiState.value = s.copy(error = "Telefon raqami va parolni kiriting.")
            return
        }
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            when (val result = repository.login(s.phone.trim(), s.password)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(loading = false)
                    onSuccess(result.data)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
