package uz.vijdon.driver.data.repository

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import uz.vijdon.driver.data.api.AvailableOrdersResponse
import uz.vijdon.driver.data.api.ConfigDto
import uz.vijdon.driver.data.api.DriverApiService
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.DutyToggleResponse
import uz.vijdon.driver.data.api.OrderDto
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
private data class ErrorBody(val detail: String? = null, val code: String? = null)

@Singleton
class DriverRepository @Inject constructor(
    private val api: DriverApiService,
    private val tokenStore: TokenStore,
    private val json: Json,
) {
    private suspend fun <T> safeCall(block: suspend () -> T): ApiResult<T> = try {
        ApiResult.Success(block())
    } catch (e: HttpException) {
        val bodyString = e.response()?.errorBody()?.string()
        val parsed = bodyString?.let { runCatching { json.decodeFromString<ErrorBody>(it) }.getOrNull() }
        ApiResult.Error(
            message = parsed?.detail ?: bodyString ?: e.message() ?: "Xatolik yuz berdi",
            code = parsed?.code,
            httpCode = e.code(),
        )
    } catch (e: IOException) {
        ApiResult.Error("Internet aloqasi yo'q. Qayta urinib ko'ring.")
    }

    suspend fun register(
        fullName: String, phone: String, carModel: String, carNumber: String, carType: String, password: String,
    ) = safeCall {
        api.register(
            mapOf(
                "full_name" to fullName, "phone_number" to phone, "car_model" to carModel,
                "car_number" to carNumber, "car_type" to carType, "password" to password,
            ),
        )
    }

    suspend fun login(phone: String, password: String): ApiResult<DriverDto> {
        val result = safeCall { api.login(mapOf("phone_number" to phone, "password" to password)) }
        return when (result) {
            is ApiResult.Success -> {
                tokenStore.save(result.data.token)
                ApiResult.Success(result.data.driver)
            }
            is ApiResult.Error -> result
        }
    }

    suspend fun logout() = tokenStore.clear()

    suspend fun me(): ApiResult<DriverDto> = safeCall { api.me() }

    suspend fun config(): ApiResult<ConfigDto> = safeCall { api.config() }

    suspend fun toggleDuty(): ApiResult<DutyToggleResponse> = safeCall { api.toggleDuty() }

    suspend fun sendLocation(lat: Double, lng: Double) = safeCall {
        api.sendLocation(mapOf("lat" to lat, "lng" to lng))
    }

    suspend fun syncFcmToken(token: String) = safeCall { api.syncFcmToken(mapOf("fcm_token" to token)) }

    suspend fun availableOrders(): ApiResult<AvailableOrdersResponse> = safeCall { api.availableOrders() }

    suspend fun acceptOrder(id: Int): ApiResult<OrderDto> = safeCall { api.acceptOrder(id) }

    suspend fun rejectOrder(id: Int) = safeCall { api.rejectOrder(id) }

    suspend fun orderOnWay(id: Int): ApiResult<OrderDto> = safeCall { api.orderOnWay(id) }

    suspend fun orderArrived(id: Int): ApiResult<OrderDto> = safeCall { api.orderArrived(id) }

    suspend fun orderComplete(id: Int, distKm: Double?, price: Double?): ApiResult<OrderDto> = safeCall {
        val body = buildMap {
            distKm?.let { put("tmx_dist_km", it.toString()) }
            price?.let { put("tmx_price", it.toString()) }
        }
        api.orderComplete(id, body)
    }

    suspend fun updateMeter(id: Int, distKm: Double, price: Double, waiting: Boolean, waitMs: Long) = safeCall {
        api.updateMeter(
            id,
            mapOf(
                "dist_km" to distKm.toString(), "price" to price.toString(),
                "waiting" to if (waiting) "1" else "0", "wait_ms" to waitMs.toString(),
            ),
        )
    }
}
