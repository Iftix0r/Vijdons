package uz.vijdon.driver.data.repository

import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import okhttp3.MediaType.Companion.toMediaType
import okhttp3.MultipartBody
import okhttp3.RequestBody.Companion.asRequestBody
import okhttp3.RequestBody.Companion.toRequestBody
import retrofit2.HttpException
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.AvailableOrdersResponse
import uz.vijdon.driver.data.api.BalanceHistoryResponse
import uz.vijdon.driver.data.api.ConfigDto
import uz.vijdon.driver.data.api.ContractDto
import uz.vijdon.driver.data.api.DestinationRequest
import uz.vijdon.driver.data.api.DestinationResponse
import uz.vijdon.driver.data.api.DriverApiService
import uz.vijdon.driver.data.api.DriverDto
import uz.vijdon.driver.data.api.DutyToggleResponse
import uz.vijdon.driver.data.api.NearbyDriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.api.OrderHistoryResponse
import uz.vijdon.driver.data.api.PhotoResponse
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.data.api.QueuePositionResponse
import uz.vijdon.driver.data.api.RatingResponse
import uz.vijdon.driver.data.api.SosResponse
import uz.vijdon.driver.data.api.SurgeResponse
import java.io.File
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

    suspend fun createOrder(
        phone: String, customerName: String, toAddress: String, fromAddress: String, assignTo: String,
    ) = safeCall {
        api.createOrder(
            mapOf(
                "phone_number" to phone, "customer_name" to customerName, "to_address" to toAddress,
                "from_address" to fromAddress, "assign_to" to assignTo,
            ),
        )
    }

    suspend fun history(period: String): ApiResult<OrderHistoryResponse> = safeCall { api.history(period) }

    suspend fun rating(): ApiResult<RatingResponse> = safeCall { api.rating() }

    suspend fun uploadPhoto(file: File): ApiResult<PhotoResponse> = safeCall {
        val body = file.asRequestBody("image/*".toMediaType())
        api.uploadPhoto(MultipartBody.Part.createFormData("photo", file.name, body))
    }

    suspend fun changePassword(oldPassword: String, newPassword: String) = safeCall {
        api.changePassword(mapOf("old_password" to oldPassword, "new_password" to newPassword))
    }

    suspend fun balanceHistory(): ApiResult<BalanceHistoryResponse> = safeCall { api.balanceHistory() }

    suspend fun requestTopup(receiptFile: File, amount: String) = safeCall {
        val receiptBody = receiptFile.asRequestBody("image/*".toMediaType())
        val amountBody = amount.toRequestBody("text/plain".toMediaType())
        api.requestTopup(MultipartBody.Part.createFormData("receipt", receiptFile.name, receiptBody), amountBody)
    }

    suspend fun contract(): ApiResult<ContractDto> = safeCall { api.contract() }

    suspend fun signContract(signatureFile: File) = safeCall {
        val signatureBody = signatureFile.asRequestBody("image/png".toMediaType())
        val agreeBody = "1".toRequestBody("text/plain".toMediaType())
        api.signContract(MultipartBody.Part.createFormData("signature", signatureFile.name, signatureBody), agreeBody)
    }

    suspend fun addresses(): ApiResult<List<AddressDto>> = safeCall { api.addresses() }

    suspend fun addressQueuePosition(id: Int, lat: Double?, lng: Double?): ApiResult<QueuePositionResponse> = safeCall {
        api.addressQueuePosition(id, lat, lng)
    }

    suspend fun addressQueueDrivers(id: Int): ApiResult<List<QueueDriverDto>> = safeCall { api.addressQueueDrivers(id) }

    suspend fun setDestination(lat: Double, lng: Double, address: String): ApiResult<DestinationResponse> = safeCall {
        api.setDestination(DestinationRequest(lat = lat, lng = lng, address = address))
    }

    suspend fun clearDestination(): ApiResult<DestinationResponse> = safeCall {
        api.setDestination(DestinationRequest(clear = true))
    }

    suspend fun sendSos(lat: Double?, lng: Double?, note: String): ApiResult<SosResponse> = safeCall {
        api.sendSos(
            buildMap {
                lat?.let { put("lat", it.toString()) }
                lng?.let { put("lng", it.toString()) }
                put("note", note)
            },
        )
    }

    suspend fun surge(): ApiResult<SurgeResponse> = safeCall { api.surge() }

    suspend fun nearbyDrivers(): ApiResult<List<NearbyDriverDto>> = safeCall { api.nearbyDrivers() }
}
