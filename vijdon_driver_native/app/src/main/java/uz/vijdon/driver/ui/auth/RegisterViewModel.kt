package uz.vijdon.driver.ui.auth

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

val CAR_TYPES = listOf("light" to "🚗 Yengil", "cargo" to "🚚 Yuk mashinasi", "minivan" to "🚐 Minivan")

data class RegisterUiState(
    val fullName: String = "",
    val phone: String = "",
    val carModel: String = "",
    val carNumber: String = "",
    val carType: String = "light",
    val password: String = "",
    val loading: Boolean = false,
    val error: String? = null,
    val success: Boolean = false,
)

@HiltViewModel
class RegisterViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(RegisterUiState())
    val uiState: StateFlow<RegisterUiState> = _uiState.asStateFlow()

    fun onFullNameChange(v: String) { _uiState.value = _uiState.value.copy(fullName = v) }
    fun onPhoneChange(v: String) { _uiState.value = _uiState.value.copy(phone = v) }
    fun onCarModelChange(v: String) { _uiState.value = _uiState.value.copy(carModel = v) }
    fun onCarNumberChange(v: String) { _uiState.value = _uiState.value.copy(carNumber = v) }
    fun onCarTypeChange(v: String) { _uiState.value = _uiState.value.copy(carType = v) }
    fun onPasswordChange(v: String) { _uiState.value = _uiState.value.copy(password = v) }

    fun register() {
        val s = _uiState.value
        if (s.fullName.isBlank() || s.phone.isBlank() || s.carModel.isBlank() || s.carNumber.isBlank() || s.password.length < 6) {
            _uiState.value = s.copy(error = "Barcha maydonlarni to'ldiring (parol kamida 6 belgi).")
            return
        }
        viewModelScope.launch {
            _uiState.value = s.copy(loading = true, error = null)
            val result = repository.register(s.fullName.trim(), s.phone.trim(), s.carModel.trim(), s.carNumber.trim(), s.carType, s.password)
            _uiState.value = when (result) {
                is ApiResult.Success -> _uiState.value.copy(loading = false, success = true)
                is ApiResult.Error -> _uiState.value.copy(loading = false, error = result.message)
            }
        }
    }
}
