package uz.vijdon.driver.data.repository

import android.content.Context
import androidx.security.crypto.EncryptedSharedPreferences
import androidx.security.crypto.MasterKey
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.MutableStateFlow
import kotlinx.coroutines.flow.asStateFlow
import kotlinx.coroutines.withContext
import javax.inject.Inject
import javax.inject.Singleton

@Singleton
class TokenStore @Inject constructor(@ApplicationContext private val context: Context) {

    // EncryptedSharedPreferences — token ochiq matn sifatida emas,
    // qurilmaning AES-256 kaliti bilan shifrlangan holda saqlanadi.
    private val prefs by lazy {
        val masterKey = MasterKey.Builder(context)
            .setKeyScheme(MasterKey.KeyScheme.AES256_GCM)
            .build()
        EncryptedSharedPreferences.create(
            context,
            "vijdon_secure_prefs",
            masterKey,
            EncryptedSharedPreferences.PrefKeyEncryptionScheme.AES256_SIV,
            EncryptedSharedPreferences.PrefValueEncryptionScheme.AES256_GCM,
        )
    }

    private val _tokenFlow = MutableStateFlow<String?>(null)
    val tokenFlow: Flow<String?> = _tokenFlow.asStateFlow()

    suspend fun currentToken(): String? = withContext(Dispatchers.IO) {
        val stored = runCatching { prefs.getString(KEY_TOKEN, null) }.getOrNull()
        if (_tokenFlow.value != stored) _tokenFlow.value = stored
        stored
    }

    suspend fun save(token: String) = withContext(Dispatchers.IO) {
        prefs.edit().putString(KEY_TOKEN, token).apply()
        _tokenFlow.value = token
    }

    suspend fun clear() = withContext(Dispatchers.IO) {
        prefs.edit().remove(KEY_TOKEN).apply()
        _tokenFlow.value = null
    }

    private companion object {
        const val KEY_TOKEN = "auth_token"
    }
}
