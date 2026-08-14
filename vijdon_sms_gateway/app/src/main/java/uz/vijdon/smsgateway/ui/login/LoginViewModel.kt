package uz.vijdon.smsgateway.ui.login

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.data.repository.ApiResult
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import javax.inject.Inject

data class LoginUiState(
    val username: String = "",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
)

@HiltViewModel
class LoginViewModel @Inject constructor(private val repository: SmsGatewayRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(LoginUiState())
    val uiState: StateFlow<LoginUiState> = _uiState.asStateFlow()

    fun onUsernameChange(v: String) { _uiState.value = _uiState.value.copy(username = v, error = null) }
    fun onPasswordChange(v: String) { _uiState.value = _uiState.value.copy(password = v, error = null) }

    fun login(onSuccess: (String) -> Unit) {
        val s = _uiState.value
        if (s.username.isBlank() || s.password.isBlank()) {
            _uiState.value = s.copy(error = "Login va parolni kiriting.")
            return
        }
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            when (val result = repository.login(s.username.trim(), s.password)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(loading = false)
                    onSuccess(result.data)
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
