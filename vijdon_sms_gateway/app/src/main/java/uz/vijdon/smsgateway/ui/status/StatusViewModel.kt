package uz.vijdon.smsgateway.ui.status

import androidx.lifecycle.ViewModel
import androidx.lifecycle.viewModelScope
import com.google.firebase.messaging.FirebaseMessaging
import dagger.hilt.android.lifecycle.HiltViewModel
import kotlinx.coroutines.flow.StateFlow
import kotlinx.coroutines.launch
import uz.vijdon.smsgateway.BuildConfig
import uz.vijdon.smsgateway.data.repository.SmsGatewayRepository
import uz.vijdon.smsgateway.data.service.SentLogBus
import uz.vijdon.smsgateway.data.service.SentLogEntry
import javax.inject.Inject

@HiltViewModel
class StatusViewModel @Inject constructor(private val repository: SmsGatewayRepository) : ViewModel() {
    val logEntries: StateFlow<List<SentLogEntry>> = SentLogBus.entries

    /** google-services.json qo'shilmagan muhitda (BuildConfig.HAS_FCM=false)
     * jim o'tkazib yuboriladi — bu holda ilova faqat fon xizmatining
     * muntazam so'rovi (polling) orqali ishlaydi, push tezlashtirishisiz. */
    fun syncFcmToken() {
        if (!BuildConfig.HAS_FCM) return
        FirebaseMessaging.getInstance().token.addOnCompleteListener { task ->
            if (!task.isSuccessful) return@addOnCompleteListener
            val token = task.result ?: return@addOnCompleteListener
            viewModelScope.launch { repository.syncFcmToken(token) }
        }
    }
}
