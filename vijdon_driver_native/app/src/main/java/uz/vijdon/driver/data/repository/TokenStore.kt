package uz.vijdon.driver.data.repository

import android.content.Context
import androidx.datastore.preferences.core.edit
import androidx.datastore.preferences.core.stringPreferencesKey
import androidx.datastore.preferences.preferencesDataStore
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.flow.Flow
import kotlinx.coroutines.flow.catch
import kotlinx.coroutines.flow.first
import kotlinx.coroutines.flow.map
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

private val Context.dataStore by preferencesDataStore(name = "vijdon_driver_prefs")

@Singleton
class TokenStore @Inject constructor(@ApplicationContext private val context: Context) {
    private val tokenKey = stringPreferencesKey("auth_token")

    // DataStore diskdan o'qishda IOException tashlasa, buni avtomatik
    // tutmaydi — shu sabab qo'lda tutib, "token yo'q" deb hisoblaymiz
    // (aks holda ilova ishga tushishida cheksiz "Loading" holatida qolib
    // ketishi mumkin edi).
    val tokenFlow: Flow<String?> = context.dataStore.data
        .catch { e -> if (e is IOException) emit(androidx.datastore.preferences.core.emptyPreferences()) else throw e }
        .map { it[tokenKey] }

    suspend fun currentToken(): String? = tokenFlow.first()

    suspend fun save(token: String) {
        context.dataStore.edit { it[tokenKey] = token }
    }

    suspend fun clear() {
        context.dataStore.edit { it.remove(tokenKey) }
    }
}
