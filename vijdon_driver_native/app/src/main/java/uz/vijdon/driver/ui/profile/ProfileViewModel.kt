package uz.vijdon.driver.ui.profile

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.Job
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.push.BalanceChangedBus
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import java.io.File
import javax.inject.Inject

data class ProfileUiState(
    val driver: DriverDto? = null,
    val uploadingPhoto: Boolean = false,
    val passwordMessage: String? = null,
    val passwordError: String? = null,
    val error: String? = null,
)

@HiltViewModel
class ProfileViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(ProfileUiState())
    val uiState: StateFlow<ProfileUiState> = _uiState.asStateFlow()

    init {
        // Balans o'zgarganda (admin to'ldirdi/ayirdi) server FCM push
        // yuboradi — shu orqali Profil ekrani ochiq bo'lsa, darhol yangi
        // balansni ko'rsatadi (ilovani qayta ochishni kutmasdan). `silent`
        // — bu HAYDOVCHI so'ramagan, FONDA sodir bo'ladigan yangilanish,
        // shu sabab (masalan) shu payt ekranda ko'rinib turgan, hali
        // haydovchi o'qib ulgurmagan boshqa xatoni (masalan rasm yuklash
        // muvaffaqiyatsiz bo'lgani) bekorga o'chirib/bosib yozib
        // yubormasligi kerak.
        viewModelScope.launch {
            BalanceChangedBus.events.collect { refresh(silent = true) }
        }
    }

    fun setDriver(driver: DriverDto) {
        _uiState.value = _uiState.value.copy(driver = driver)
    }

    // Bir nechta balans o'zgarishi yaqin vaqt ichida ketma-ket push
    // yuborishi mumkin — tarmoq javoblarning TARTIBINI kafolatlamaydi,
    // shu sabab faqat ENG SO'NGGI chaqiruv natijasi qo'llanishi uchun
    // oldingi (hali tugallanmagan) so'rov bekor qilinadi.
    private var refreshJob: Job? = null

    fun refresh(silent: Boolean = false) {
        refreshJob?.cancel()
        refreshJob = viewModelScope.launch {
            when (val result = repository.me()) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(
                    driver = result.data,
                    error = if (silent) _uiState.value.error else null,
                )
                is ApiResult.Error -> if (!silent) _uiState.value = _uiState.value.copy(error = result.message)
            }
        }
    }

    fun uploadPhoto(file: File) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(uploadingPhoto = true)
            when (val result = repository.uploadPhoto(file)) {
                is ApiResult.Success -> {
                    _uiState.value = _uiState.value.copy(uploadingPhoto = false)
                    refresh()
                }
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(uploadingPhoto = false, error = result.message)
            }
        }
    }

    fun changePassword(oldPassword: String, newPassword: String) {
        viewModelScope.launch {
            _uiState.value = _uiState.value.copy(passwordMessage = null, passwordError = null)
            when (val result = repository.changePassword(oldPassword, newPassword)) {
                is ApiResult.Success -> _uiState.value = _uiState.value.copy(passwordMessage = result.data.detail)
                is ApiResult.Error -> _uiState.value = _uiState.value.copy(passwordError = result.message)
            }
        }
    }
}
