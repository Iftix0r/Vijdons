package uz.vijdon.driver.ui

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
import uz.vijdon.driver.data.repository.TokenStore
import javax.inject.Inject

sealed class SessionState {
    data object Loading : SessionState()
    data object LoggedOut : SessionState()
    data class Pending(val driver: DriverDto) : SessionState()
    data class Frozen(val driver: DriverDto) : SessionState()
    data class Approved(val driver: DriverDto) : SessionState()
}

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val repository: DriverRepository,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _state = MutableStateFlow<SessionState>(SessionState.Loading)
    val state: StateFlow<SessionState> = _state.asStateFlow()

    init {
        refresh()
    }

    fun refresh() {
        viewModelScope.launch {
            val token = tokenStore.currentToken()
            if (token.isNullOrBlank()) {
                _state.value = SessionState.LoggedOut
                return@launch
            }
            when (val result = repository.me()) {
                is ApiResult.Success -> _state.value = toState(result.data)
                is ApiResult.Error -> {
                    if (result.httpCode == 401) {
                        tokenStore.clear()
                    }
                    _state.value = SessionState.LoggedOut
                }
            }
        }
    }

    fun onLoggedIn(driver: DriverDto) {
        _state.value = toState(driver)
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            _state.value = SessionState.LoggedOut
        }
    }

    private fun toState(driver: DriverDto): SessionState = when {
        driver.is_frozen -> SessionState.Frozen(driver)
        driver.isApproved -> SessionState.Approved(driver)
        else -> SessionState.Pending(driver)
    }
}
