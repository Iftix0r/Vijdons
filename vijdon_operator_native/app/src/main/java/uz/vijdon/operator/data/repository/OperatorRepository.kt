package uz.vijdon.operator.data.repository

import kotlinx.coroutines.delay
import kotlinx.serialization.Serializable
import kotlinx.serialization.json.Json
import retrofit2.HttpException
import uz.vijdon.operator.data.api.BalanceLogResponse
import uz.vijdon.operator.data.api.ChatDriverSummaryDto
import uz.vijdon.operator.data.api.ChatMessageDto
import uz.vijdon.operator.data.api.ChatUnreadResponse
import uz.vijdon.operator.data.api.DashboardDto
import uz.vijdon.operator.data.api.DetailResponse
import uz.vijdon.operator.data.api.DriverDetailResponse
import uz.vijdon.operator.data.api.DriverDto
import uz.vijdon.operator.data.api.DriverListResponse
import uz.vijdon.operator.data.api.DriverLiveResponse
import uz.vijdon.operator.data.api.GroupMessageDto
import uz.vijdon.operator.data.api.OperatorApiService
import uz.vijdon.operator.data.api.OperatorDto
import uz.vijdon.operator.data.api.OrderDto
import uz.vijdon.operator.data.api.OrderListResponse
import uz.vijdon.operator.data.api.TopupListResponse
import java.io.IOException
import javax.inject.Inject
import javax.inject.Singleton

@Serializable
private data class ErrorBody(val detail: String? = null, val code: String? = null)

@Singleton
class OperatorRepository @Inject constructor(
    private val api: OperatorApiService,
    private val tokenStore: TokenStore,
    private val json: Json,
) {
    // driverapp'dagi (vijdon_driver_native) bilan bir xil chidamlilik
    // strategiyasi: sof tarmoq xatosida (IOException) bir necha marta qayta
    // uriniladi, server javob qaytargan xatoda (HttpException) qayta
    // urinish ma'nosiz.
    private suspend fun <T> safeCall(block: suspend () -> T): ApiResult<T> {
        repeat(NETWORK_RETRY_ATTEMPTS) { attempt ->
            try {
                return ApiResult.Success(block())
            } catch (e: HttpException) {
                val bodyString = e.response()?.errorBody()?.string()
                val parsed = bodyString?.let { runCatching { json.decodeFromString<ErrorBody>(it) }.getOrNull() }
                return ApiResult.Error(
                    message = parsed?.detail ?: bodyString ?: e.message() ?: "Xatolik yuz berdi",
                    code = parsed?.code,
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

    suspend fun login(username: String, password: String): ApiResult<OperatorDto> {
        val result = safeCall { api.login(mapOf("username" to username, "password" to password)) }
        return when (result) {
            is ApiResult.Success -> {
                tokenStore.save(result.data.token)
                ApiResult.Success(result.data.operator)
            }
            is ApiResult.Error -> result
        }
    }

    suspend fun logout() = tokenStore.clear()

    suspend fun me(): ApiResult<OperatorDto> = safeCall { api.me() }

    suspend fun syncFcmToken(token: String) = safeCall { api.syncFcmToken(mapOf("fcm_token" to token)) }

    suspend fun dashboard(): ApiResult<DashboardDto> = safeCall { api.dashboard() }

    suspend fun orders(q: String? = null, status: String? = null, page: Int? = null): ApiResult<OrderListResponse> =
        safeCall { api.orders(q, status, page) }

    suspend fun orderDetail(id: Int): ApiResult<OrderDto> = safeCall { api.orderDetail(id) }

    suspend fun createOrder(
        phone: String, customerName: String, fromAddress: String, toAddress: String,
        fromLat: Double?, fromLng: Double?, toLat: Double?, toLng: Double?,
        driverId: Int?, paymentType: String, carType: String, isDelivery: Boolean, note: String,
    ): ApiResult<OrderDto> = safeCall {
        val body = buildMap {
            put("phone_number", phone)
            put("customer_name", customerName)
            put("from_address", fromAddress)
            put("to_address", toAddress)
            fromLat?.let { put("from_lat", it.toString()) }
            fromLng?.let { put("from_lng", it.toString()) }
            toLat?.let { put("to_lat", it.toString()) }
            toLng?.let { put("to_lng", it.toString()) }
            driverId?.let { put("driver_id", it.toString()) }
            put("payment_type", paymentType)
            put("car_type", carType)
            put("is_delivery", if (isDelivery) "1" else "")
            put("note", note)
        }
        api.createOrder(body)
    }

    suspend fun updateOrderStatus(id: Int, status: String? = null, driverId: Int? = null): ApiResult<OrderDto> = safeCall {
        val body = buildMap {
            status?.let { put("status", it) }
            driverId?.let { put("driver_id", it.toString()) }
        }
        api.updateOrderStatus(id, body)
    }

    suspend fun dispatchOrder(id: Int): ApiResult<OrderDto> = safeCall { api.dispatchOrder(id) }

    suspend fun cancelOrder(id: Int): ApiResult<OrderDto> = safeCall { api.cancelOrder(id) }

    suspend fun deleteOrder(id: Int) = safeCall { api.deleteOrder(id) }

    suspend fun drivers(tab: String = "approved", q: String? = null, sort: String? = null, page: Int? = null): ApiResult<DriverListResponse> =
        safeCall { api.drivers(tab, q, sort, page) }

    suspend fun driversLive(): ApiResult<DriverLiveResponse> = safeCall { api.driversLive() }

    suspend fun driverDetail(id: Int): ApiResult<DriverDetailResponse> = safeCall { api.driverDetail(id) }

    suspend fun driverApprove(id: Int, approve: Boolean): ApiResult<DriverDto> = safeCall {
        api.driverApprove(id, mapOf("action" to if (approve) "approve" else "reject"))
    }

    suspend fun driverToggleActive(id: Int): ApiResult<DriverDto> = safeCall { api.driverToggleActive(id) }

    suspend fun driverToggleFrozen(id: Int): ApiResult<DriverDto> = safeCall { api.driverToggleFrozen(id) }

    suspend fun driverRecharge(id: Int, amount: String, deduct: Boolean, note: String = ""): ApiResult<DriverDto> = safeCall {
        api.driverRecharge(id, mapOf("amount" to amount, "action" to if (deduct) "deduct" else "add", "note" to note))
    }

    suspend fun chatDriverList(): ApiResult<List<ChatDriverSummaryDto>> = safeCall { api.chatDriverList() }

    suspend fun chatMessages(driverId: Int): ApiResult<List<ChatMessageDto>> = safeCall { api.chatMessages(driverId) }

    suspend fun chatSend(driverId: Int, text: String): ApiResult<ChatMessageDto> = safeCall {
        api.chatSend(driverId, mapOf("text" to text))
    }

    suspend fun chatUnread(): ApiResult<ChatUnreadResponse> = safeCall { api.chatUnread() }

    suspend fun chatGroupList(): ApiResult<List<GroupMessageDto>> = safeCall { api.chatGroupList() }

    suspend fun chatGroupSend(text: String): ApiResult<GroupMessageDto> = safeCall {
        api.chatGroupSend(mapOf("text" to text))
    }

    suspend fun topups(status: String? = null): ApiResult<TopupListResponse> = safeCall { api.topups(status) }

    suspend fun topupResolve(id: Int, approve: Boolean, reason: String = ""): ApiResult<DetailResponse> = safeCall {
        val body = if (approve) mapOf("action" to "approve") else mapOf("action" to "reject", "reason" to reason)
        api.topupResolve(id, body)
    }

    suspend fun balanceLog(q: String? = null, action: String? = null, page: Int? = null): ApiResult<BalanceLogResponse> =
        safeCall { api.balanceLog(q, action, page) }
}
