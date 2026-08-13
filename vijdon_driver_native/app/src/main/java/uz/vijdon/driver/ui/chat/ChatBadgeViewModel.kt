package uz.vijdon.driver.ui.chat

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.driver.data.repository.ApiResult
import uz.vijdon.driver.data.repository.DriverRepository
import javax.inject.Inject

/**
 * Pastki panelning "Chat" tugmasidagi o'qilmagan xabarlar belgisi (badge)
 * uchun — `ApprovedScaffold` darajasida (Chat bo'limi ochiq-yopiqligidan
 * qat'i nazar, butun sessiya davomida) yashaydi. `ChatViewModel`ning o'zi
 * (Chat bo'limi ochilganda) har so'rovda serverda "o'qilgan" deb belgilaydi
 * — shu sabab bu yerda tez-tez emas, vaqti-vaqti bilan (12s) so'raladi.
 */
@HiltViewModel
class ChatBadgeViewModel @Inject constructor(private val repository: DriverRepository) : ViewModel() {
    private val _unread = MutableStateFlow(0)
    val unread: StateFlow<Int> = _unread.asStateFlow()

    init {
        viewModelScope.launch {
            while (true) {
                val result = repository.chatUnread()
                if (result is ApiResult.Success) _unread.value = result.data.count
                delay(12_000)
            }
        }
    }
}
