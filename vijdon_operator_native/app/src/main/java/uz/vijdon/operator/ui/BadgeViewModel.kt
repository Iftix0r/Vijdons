package uz.vijdon.operator.ui

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.delay
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.launch
import uz.vijdon.operator.data.repository.ApiResult
import uz.vijdon.operator.data.repository.OperatorRepository
import javax.inject.Inject

/** Pastki tab-bardagi nishonlar (ogohlantirilishi kerak bo'lgan buyurtmalar,
 * o'qilmagan chat, kutilayotgan to'lovlar) — chat/ekran ochiq-yopiqligidan
 * qat'i nazar butun sessiya davomida fonda yangilanib turadi
 * (`ApprovedScaffold` darajasida yaratiladi, driverapp'dagi
 * `ChatBadgeViewModel` bilan bir xil g'oya). */
@HiltViewModel
class BadgeViewModel @Inject constructor(private val repository: OperatorRepository) : ViewModel() {
    private val _ordersBadge = MutableStateFlow(0)
    val ordersBadge: StateFlow<Int> = _ordersBadge.asStateFlow()

    private val _chatBadge = MutableStateFlow(0)
    val chatBadge: StateFlow<Int> = _chatBadge.asStateFlow()

    private val _balanceBadge = MutableStateFlow(0)
    val balanceBadge: StateFlow<Int> = _balanceBadge.asStateFlow()

    init {
        viewModelScope.launch { while (true) { pollDashboard(); delay(15_000) } }
        viewModelScope.launch { while (true) { pollChat(); delay(12_000) } }
    }

    private suspend fun pollDashboard() {
        when (val r = repository.dashboard()) {
            is ApiResult.Success -> {
                _ordersBadge.value = r.data.aging_orders
                _balanceBadge.value = r.data.pending_topups
            }
            is ApiResult.Error -> Unit
        }
    }

    private suspend fun pollChat() {
        when (val r = repository.chatUnread()) {
            is ApiResult.Success -> _chatBadge.value = r.data.count
            is ApiResult.Error -> Unit
        }
    }
}
