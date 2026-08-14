package uz.vijdon.operator.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.crashlytics.FirebaseCrashlytics
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.BuildConfig
import uz.vijdon.operator.data.api.OperatorDto
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import uz.vijdon.operator.data.repository.TokenStore
import javax.inject.Inject

// Operatorlar (is_staff) uchun "kutilmoqda"/"muzlatilgan" holati yo'q —
// haydovchi ilovasidagi (vijdon_driver_native) SessionState'dan farqli,
// bu yerda faqat "kirilgan/kirilmagan" bor.
sealed class SessionState {
    data object Loading : SessionState()
    data object LoggedOut : SessionState()
    data class Approved(val operator: OperatorDto) : SessionState()
}

@HiltViewModel
class SessionViewModel @Inject constructor(
    private val repository: OperatorRepository,
    private val tokenStore: TokenStore,
) : ViewModel() {

    private val _state = MutableStateFlow<SessionState>(SessionState.Loading)
    val state: StateFlow<SessionState> = _state.asStateFlow()

    // `refresh()` bir nechta joydan mustaqil chaqirilishi mumkin (init,
    // "Qayta tekshirish" tugmasi) — agar shu payt allaqachon (xato sabab)
    // qayta urinish davom etayotgan bo'lsa, YANA bir mustaqil urinish
    // zanjiri boshlamaslik uchun.
    private var refreshJob: Job? = null

    init {
        refresh()
    }

    fun refresh() {
        if (refreshJob?.isActive == true) return
        refreshJob = viewModelScope.launch {
            val token = tokenStore.currentToken()
            if (token.isNullOrBlank()) {
                _state.value = SessionState.LoggedOut
                return@launch
            }
            // driverapp (vijdon_driver_native) SessionViewModel'dagi bilan
            // bir xil chidamlilik: faqat aniq 401'da chiqariladi, boshqa
            // (tarmoq/WAF) xatolarida chegaralangan vaqt ichida qayta uriniladi.
            val deadline = System.currentTimeMillis() + REFRESH_DEADLINE_MS
            var attempt = 0
            while (true) {
                when (val result = repository.me()) {
                    is ApiResult.Success -> {
                        applyState(result.data)
                        return@launch
                    }
                    is ApiResult.Error -> {
                        if (result.httpCode == 401 || result.httpCode == 403) {
                            tokenStore.clear()
                            _state.value = SessionState.LoggedOut
                            return@launch
                        }
                        attempt++
                        if (attempt >= MAX_REFRESH_ATTEMPTS || System.currentTimeMillis() >= deadline) {
                            _state.value = SessionState.LoggedOut
                            return@launch
                        }
                        delay(if (result.isConnectivity) 4_000 else 2_000)
                    }
                }
            }
        }
    }

    fun onLoggedIn(operator: OperatorDto) {
        applyState(operator)
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            if (BuildConfig.HAS_FCM) FirebaseCrashlytics.getInstance().setUserId("")
            _state.value = SessionState.LoggedOut
        }
    }

    private fun applyState(operator: OperatorDto) {
        // Crash hisobotida qaysi operatorda xato chiqqanini bilish uchun —
        // shaxsiy ma'lumot emas, faqat ID yoziladi.
        if (BuildConfig.HAS_FCM) {
            FirebaseCrashlytics.getInstance().setUserId(operator.id.toString())
        }
        _state.value = SessionState.Approved(operator)
    }

    private companion object {
        const val MAX_REFRESH_ATTEMPTS = 6
        const val REFRESH_DEADLINE_MS = 20_000L
    }
}
