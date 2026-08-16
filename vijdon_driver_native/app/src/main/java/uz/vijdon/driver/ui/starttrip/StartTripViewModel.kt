package uz.vijdon.driver.ui.starttrip

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

data class StartTripUiState(
    val loading: Boolean = true,
    val error: String? = null,
    val success: Boolean = false,
)

/** "+" tugmasi bosilganda — hech qanday forma so'ramasdan, darhol
 * taksimetrni ishga tushiradi (`repository.startTaximeterOrder()`,
 * `lat`/`lng` berilmaydi — server haydovchining so'nggi ma'lum GPS
 * joylashuvini o'zi ishlatadi). Muvaffaqiyatli bo'lsa, ekran darhol
 * yopiladi (`StartTripScreen`dagi `onDone`) — yaratilgan 'on_way'
 * buyurtma Bosh sahifaning keyingi pollingida (4s ichida) o'zi paydo
 * bo'lib, taksimetri avtomatik ishga tushadi (`HomeViewModel.ensureTaximeter`
 * har qanday on_way/arrived buyurtma uchun chaqiriladi, bu buyurtma
 * qanday yaratilganidan qat'i nazar). */
@HiltViewModel
class StartTripViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _uiState = MutableStateFlow(StartTripUiState())
    val uiState: StateFlow<StartTripUiState> = _uiState.asStateFlow()

    init {
        start()
    }

    fun start() {
        viewModelScope.launch {
            _uiState.value = StartTripUiState(loading = true, error = null)
            _uiState.value = when (val result = repository.startTaximeterOrder()) {
                is ApiResult.Success -> StartTripUiState(loading = false, success = true)
                is ApiResult.Error -> StartTripUiState(loading = false, error = result.message)
            }
        }
    }
}
