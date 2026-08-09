package uz.vijdon.callwatcher

import android.util.Log
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.OkHttpClient
import okhttp3.Request
import okhttp3.RequestBody.Companion.toRequestBody
import org.json.JSONObject
import java.io.IOException
import java.util.concurrent.TimeUnit

/** Django backend (taxi/api_views.py: operator_login, incoming_call_report) bilan gaplashadi. */
object ApiClient {
    private const val TAG = "VijdonApiClient"
    private val JSON = "application/json; charset=utf-8".toMediaType()

    private val client = OkHttpClient.Builder()
        .connectTimeout(10, TimeUnit.SECONDS)
        .readTimeout(10, TimeUnit.SECONDS)
        .writeTimeout(10, TimeUnit.SECONDS)
        .build()

    sealed class LoginResult {
        data class Success(val token: String) : LoginResult()
        data class Failure(val message: String) : LoginResult()
    }

    fun login(baseUrl: String, username: String, password: String): LoginResult {
        return try {
            val body = JSONObject()
                .put("username", username)
                .put("password", password)
                .toString()
                .toRequestBody(JSON)
            val request = Request.Builder()
                .url(normalizeBaseUrl(baseUrl) + "panel/api/operator/login/")
                .post(body)
                .build()
            client.newCall(request).execute().use { resp ->
                val text = resp.body?.string().orEmpty()
                if (resp.isSuccessful) {
                    val token = runCatching { JSONObject(text).optString("token") }.getOrDefault("")
                    if (token.isNotEmpty()) LoginResult.Success(token)
                    else LoginResult.Failure("Token topilmadi")
                } else {
                    val detail = runCatching { JSONObject(text).optString("detail") }.getOrDefault("")
                    LoginResult.Failure(detail.ifEmpty { "Xato: ${resp.code}" })
                }
            }
        } catch (e: Exception) {
            Log.e(TAG, "login xatosi", e)
            LoginResult.Failure("Sayt bilan aloqa yo'q")
        }
    }

    /** Kiruvchi qo'ng'iroq raqamini serverga yuboradi; tarmoq xatosida bir necha marta qayta urinadi.
     * Bloklaydigan chaqiruv — background thread'dan chaqirilishi shart, hech qachon UI thread'dan emas. */
    fun reportIncomingCall(baseUrl: String, token: String, phoneNumber: String) {
        val body = JSONObject()
            .put("phone_number", phoneNumber)
            .toString()
            .toRequestBody(JSON)
        val request = Request.Builder()
            .url(normalizeBaseUrl(baseUrl) + "panel/api/operator/incoming-call/")
            .addHeader("Authorization", "Token $token")
            .post(body)
            .build()

        var lastError: Exception? = null
        for (attempt in 1..3) {
            try {
                client.newCall(request).execute().use { resp ->
                    if (resp.isSuccessful) {
                        Log.i(TAG, "Qo'ng'iroq yuborildi: $phoneNumber")
                        return
                    }
                    Log.w(TAG, "Server javobi ${resp.code}, urinish $attempt/3")
                }
            } catch (e: IOException) {
                lastError = e
                Log.w(TAG, "Tarmoq xatosi, urinish $attempt/3: ${e.message}")
            }
            try {
                Thread.sleep(1500L * attempt)
            } catch (_: InterruptedException) {
                Thread.currentThread().interrupt()
                return
            }
        }
        Log.e(TAG, "Qo'ng'iroqni yuborib bo'lmadi: $phoneNumber", lastError)
    }

    fun normalizeBaseUrl(raw: String): String {
        var url = raw.trim()
        if (!url.startsWith("http://") && !url.startsWith("https://")) url = "https://$url"
        if (!url.endsWith("/")) url += "/"
        return url
    }
}
