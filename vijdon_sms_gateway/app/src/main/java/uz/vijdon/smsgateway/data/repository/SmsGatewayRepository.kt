package uz.vijdon.smsgateway.data.repository

import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import uz.vijdon.smsgateway.BuildConfig
import uz.vijdon.smsgateway.data.api.PendingSmsDto
import uz.vijdon.smsgateway.data.api.SmsGatewayApiService
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
private data class ErrorBody(val detail: String? = null)

@Singleton
class SmsGatewayRepository @Inject constructor(
    private val api: SmsGatewayApiService,
    private val tokenStore: TokenStore,
    private val json: Json,
) {
    // driverapp/operatorapp'dagi bilan bir xil chidamlilik strategiyasi:
    // sof tarmoq xatosida (IOException) bir necha marta qayta uriniladi,
    // server javob qaytargan xatoda (HttpException) qayta urinish ma'nosiz.
    private suspend fun <T> safeCall(block: suspend () -> T): ApiResult<T> {
        repeat(NETWORK_RETRY_ATTEMPTS) { attempt ->
            try {
                return ApiResult.Success(block())
            } catch (e: HttpException) {
                val bodyString = e.response()?.errorBody()?.string()
                val parsed = bodyString?.let { runCatching { json.decodeFromString<ErrorBody>(it) }.getOrNull() }
                return ApiResult.Error(
                    message = parsed?.detail ?: bodyString ?: e.message() ?: "Xatolik yuz berdi",
                    httpCode = e.code(),
                )
            } catch (e: IOException) {
                if (attempt < NETWORK_RETRY_ATTEMPTS - 1) delay(NETWORK_RETRY_BACKOFF_MS * (attempt + 1))
            } catch (e: kotlinx.coroutines.CancellationException) {
                throw e
            } catch (e: Exception) {
                return ApiResult.Error("Kutilmagan javob. Server sozlamalarini tekshiring.")
            }
        }
        return ApiResult.Error("Internet aloqasi yo'q. Qayta urinib ko'ring.", isConnectivity = true)
    }

    private companion object {
        const val NETWORK_RETRY_ATTEMPTS = 3
        const val NETWORK_RETRY_BACKOFF_MS = 400L
    }

    suspend fun login(username: String, password: String): ApiResult<String> {
        // Diqqat: mavjud `/panel/api/operator/login/` (taxi/api_views.py:
        // operator_login) ishlatiladi — SMS-shlyuz ilovasi uchun alohida
        // login yozilmagan, qo'ng'iroq-kuzatuvchi ilova ham xuddi shu
        // endpoint'dan foydalanadi.
        val loginUrl = BuildConfig.BASE_URL.trimEnd('/') + "/panel/api/operator/login/"
        val result = safeCall { api.login(loginUrl, mapOf("username" to username, "password" to password)) }
        return when (result) {
            is ApiResult.Success -> {
                tokenStore.save(result.data.token, result.data.username)
                ApiResult.Success(result.data.username)
            }
            is ApiResult.Error -> result
        }
    }

    suspend fun logout() = tokenStore.clear()

    suspend fun syncFcmToken(token: String) = safeCall { api.syncFcmToken(mapOf("fcm_token" to token)) }

    suspend fun pending(): ApiResult<List<PendingSmsDto>> = safeCall { api.pending() }

    suspend fun reportSent(id: Int) = safeCall { api.reportResult(id, mapOf("status" to "sent")) }

    suspend fun reportFailed(id: Int, error: String) = safeCall {
        api.reportResult(id, mapOf("status" to "failed", "error" to error.take(255)))
    }

    suspend fun reportIncoming(phoneNumber: String, text: String, receivedAtIso: String) = safeCall {
        api.reportIncoming(mapOf("phone_number" to phoneNumber, "text" to text, "received_at" to receivedAtIso))
    }
}
