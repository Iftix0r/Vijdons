package uz.vijdon.driver.ui

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
import uz.vijdon.driver.BuildConfig
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

    // `refresh()` bir nechta joydan mustaqil chaqirilishi mumkin (init,
    // statusPollJob'ning har 15s'dagi tikilishi, "Qayta tekshirish" tugmasi)
    // — agar shu payt allaqachon (xato sabab) qayta urinish davom etayotgan
    // bo'lsa, YANA bir mustaqil urinish zanjiri boshlamaslik uchun.
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
            // Diqqat: token haqiqiy bo'lishi mumkin, lekin so'rov vaqtinchalik
            // sabab (tarmoq, WAF tekshiruvi hali "yechilmoqda") bilan
            // muvaffaqiyatsiz bo'lishi mumkin — bunday holda haydovchini
            // BEKORGA tizimdan chiqarib yubormaslik uchun, faqat aniq 401
            // (token haqiqatan noto'g'ri/eskirgan) javobida chiqariladi.
            //
            // Ilgari bu yerda HAR QANDAY (401 bo'lmagan) xatoda ham darhol
            // LoggedOut'ga o'tkazilardi — bu esa tarmoq bir martalik
            // "tepki"si (WAF, 5xx) sababli ham haydovchini qo'lda qayta
            // kirishga majburlardi, garchi tokeni hali amal qilsa ham. Endi
            // bir nechta marta (chegaralangan holda) fonda qayta uriniladi;
            // hammasi muvaffaqiyatsiz tugasa — OXIRGI chorasi sifatida
            // baribir LoggedOut'ga o'tadi (aks holda uzilish uzoq davom
            // etganda haydovchi hech qanday tugmasiz abadiy "Loading"
            // aylanmasida qolib ketardi).
            //
            // Diqqat: `repository.me()`ning O'ZI (safeCall ichida, sof
            // ulanish xatosida) bitta chaqiruvda ~45s gacha (3 urinish X
            // OkHttp 15s timeout) cho'zilishi mumkin — shu sabab tashqi
            // qayta urinish SONI bilan bir qatorda umumiy VAQT chegarasi
            // ham qo'yiladi: aks holda (masalan ulanish butunlay yo'q
            // holatda) 6 marta X ~45s ustma-ust qo'shilib, aynan shu
            // kodning oldini olmoqchi bo'lgan "uzoq osilib qolish"
            // holatini o'zi qayta yaratardi.
            //
            // MUHIM: `REFRESH_DEADLINE_MS` (20s) ATAYLAB bitta chaqiruvning
            // eng yomon holatidan (~45s) QISQA — bu qasddan shunday: sof
            // ulanish xatosida (`isConnectivity`) BITTA chaqiruvning o'zi
            // allaqachon shu 20s'dan oshib ketadi, shu sabab bunday holda
            // amalda faqat 1 marta urinilib (aynan shu kod YOZILISHIDAN
            // OLDINGI xatti-harakat — bitta so'rov, keyin LoggedOut), tashqi
            // qayta urinish darhol to'xtaydi. `MAX_REFRESH_ATTEMPTS = 6`ning
            // asosiy foydasi esa TEZ tugaydigan xatolar uchun (WAF/5xx —
            // safeCall bularni ICHKARIDA umuman qayta urinmaydi, har biri
            // soniya ichida qaytadi) — bunday holatlarda 20s ichida bir
            // necha marta tez urinib ko'rish imkoniyati beriladi.
            val deadline = System.currentTimeMillis() + REFRESH_DEADLINE_MS
            var attempt = 0
            while (true) {
                when (val result = repository.me()) {
                    is ApiResult.Success -> {
                        applyState(toState(result.data))
                        return@launch
                    }
                    is ApiResult.Error -> {
                        if (result.httpCode == 401) {
                            tokenStore.clear()
                            applyState(SessionState.LoggedOut)
                            return@launch
                        }
                        attempt++
                        if (attempt >= MAX_REFRESH_ATTEMPTS || System.currentTimeMillis() >= deadline) {
                            applyState(SessionState.LoggedOut)
                            return@launch
                        }
                        delay(if (result.isConnectivity) 4_000 else 2_000)
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
            if (BuildConfig.HAS_FCM) FirebaseCrashlytics.getInstance().setUserId("")
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

    private companion object {
        const val MAX_REFRESH_ATTEMPTS = 6
        // `repository.me()`ning O'ZI sof ulanish xatosida ~45s gacha
        // cho'zilishi mumkin (safeCall.kt izohiga qarang) — shu sabab
        // urinishlar SONI emas, umumiy VAQT asosiy chegara bo'lib xizmat
        // qiladi (aks holda uzoq uzilishda 6 marta X 45s ustma-ust qo'shilib
        // ketardi).
        const val REFRESH_DEADLINE_MS = 20_000L
    }

    private fun toState(driver: DriverDto): SessionState {
        // Crash hisobotida qaysi haydovchida xato chiqqanini bilish uchun —
        // shaxsiy ma'lumot (ism/telefon) emas, faqat ID yoziladi.
        if (BuildConfig.HAS_FCM) {
            FirebaseCrashlytics.getInstance().setUserId(driver.id.toString())
        }
        return when {
            driver.is_frozen -> SessionState.Frozen(driver)
            driver.isApproved -> SessionState.Approved(driver)
            else -> SessionState.Pending(driver)
        }
    }
}
