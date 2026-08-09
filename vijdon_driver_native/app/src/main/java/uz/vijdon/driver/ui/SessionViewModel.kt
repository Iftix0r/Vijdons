package uz.vijdon.driver.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.delay
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

    // Haydovchi "kutilmoqda"/"muzlatilgan" ekranida qolib ketganda, admin
    // uni tasdiqlasa ham ilova buni bilib olishning boshqa yo'li yo'q edi
    // (faqat chiqib qayta kirish orqali) — shu sabab shu holatlarda avtomatik
    // muntazam qayta tekshirib turadi.
    private var statusPollJob: Job? = null

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
            // Diqqat: token haqiqiy bo'lishi mumkin, lekin so'rov vaqtinchalik
            // sabab (tarmoq, WAF tekshiruvi hali "yechilmoqda") bilan
            // muvaffaqiyatsiz bo'lishi mumkin — bunday holda haydovchini
            // BEKORGA tizimdan chiqarib yubormaslik uchun, faqat aniq 401
            // (token haqiqatan noto'g'ri/eskirgan) javobida chiqariladi;
            // boshqa xatolarda bir marta qayta urinib ko'riladi.
            when (val result = repository.me()) {
                is ApiResult.Success -> applyState(toState(result.data))
                is ApiResult.Error -> {
                    if (result.httpCode == 401) {
                        tokenStore.clear()
                        applyState(SessionState.LoggedOut)
                        return@launch
                    }
                    delay(3_000)
                    when (val retryResult = repository.me()) {
                        is ApiResult.Success -> applyState(toState(retryResult.data))
                        is ApiResult.Error -> {
                            if (retryResult.httpCode == 401) tokenStore.clear()
                            applyState(SessionState.LoggedOut)
                        }
                    }
                }
            }
        }
    }

    fun onLoggedIn(driver: DriverDto) {
        applyState(toState(driver))
    }

    fun logout() {
        viewModelScope.launch {
            repository.logout()
            applyState(SessionState.LoggedOut)
        }
    }

    private fun applyState(newState: SessionState) {
        _state.value = newState
        val needsPolling = newState is SessionState.Pending || newState is SessionState.Frozen
        if (needsPolling && statusPollJob == null) {
            statusPollJob = viewModelScope.launch {
                while (true) {
                    delay(15_000)
                    refresh()
                }
            }
        } else if (!needsPolling) {
            statusPollJob?.cancel()
            statusPollJob = null
        }
    }

    private fun toState(driver: DriverDto): SessionState = when {
        driver.is_frozen -> SessionState.Frozen(driver)
        driver.isApproved -> SessionState.Approved(driver)
        else -> SessionState.Pending(driver)
    }
}
