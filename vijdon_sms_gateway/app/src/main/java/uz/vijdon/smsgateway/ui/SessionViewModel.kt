package uz.vijdon.smsgateway.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import uz.vijdon.smsgateway.data.repository.TokenStore
import javax.inject.Inject

sealed class SessionState {
    data object Loading : SessionState()
    data object LoggedOut : SessionState()
    data class LoggedIn(val username: String) : SessionState()
}

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val repository: SmsGatewayRepository,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _state = MutableStateFlow<SessionState>(SessionState.Loading)
    val state: StateFlow<SessionState> = _state.asStateFlow()

    init {
        viewModelScope.launch {
            val token = tokenStore.currentToken()
            _state.value = if (token.isNullOrBlank()) {
                SessionState.LoggedOut
            } else {
                SessionState.LoggedIn(tokenStore.currentUsername() ?: "")
            }
        }
    }

    fun onLoggedIn(username: String) {
        _state.value = SessionState.LoggedIn(username)
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            _state.value = SessionState.LoggedOut
        }
    }
}
