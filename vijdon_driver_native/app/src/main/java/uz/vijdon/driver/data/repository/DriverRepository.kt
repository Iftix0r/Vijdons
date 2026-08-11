package uz.vijdon.driver.data.repository

import kotlinx.coroutines.delay
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
import uz.vijdon.driver.data.api.ChatUnreadResponse
import uz.vijdon.driver.data.api.DriverSoundDto
import uz.vijdon.driver.data.api.GroupMessageDto
import uz.vijdon.driver.data.api.NearbyDriverDto
import uz.vijdon.driver.data.api.OrderDto
import uz.vijdon.driver.data.api.OrderHistoryResponse
import uz.vijdon.driver.data.api.PhotoResponse
import uz.vijdon.driver.data.api.QueueDriverDto
import uz.vijdon.driver.data.api.QueuePositionResponse
import uz.vijdon.driver.data.api.RatingResponse
import uz.vijdon.driver.data.api.RegionDto
import uz.vijdon.driver.data.api.SosResponse
import uz.vijdon.driver.data.api.SurgeResponse
import uz.vijdon.driver.util.DeviceInfo
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
    // Signal vaqtincha uzilib qolishi (metro, tunnel, tog' hududi, liftda
    // qolib ketish) — haydovchi uchun eng xavfli payt aynan shu, chunki
    // "Qabul qilish" kabi vaqtga bog'liq amal bajarilsa, operator sozlamasidagi
    // dispatch_timeout atigi 10s bo'lgani uchun buyurtma boshqa haydovchiga
    // o'tib ketishi mumkin. Shu sabab SOF tarmoq xatosida (IOException —
    // so'rov serverga umuman yetib bormagan holat) darhol xato ko'rsatish
    // o'rniga, qisqa kutish bilan bir necha marta avtomatik qayta uriniladi.
    // Server javob qaytargan holatlarda (HttpException — masalan 400/403)
    // qayta urinish ma'nosiz, chunki natija o'zgarmaydi.
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
                // Server JSON o'rniga kutilmagan javob qaytarsa (masalan Cloudflare
                // HTML tekshiruv sahifasi — 0.1-band hali bajarilmagan bo'lsa),
                // kotlinx.serialization SerializationException tashlaydi — bu
                // HttpException/IOException EMAS, shu sabab alohida tutiladi.
                // Aks holda tutilmagan xato butun ilovani (yoki hech bo'lmasa joriy
                // ekranni) buzib qo'yardi.
                return ApiResult.Error("Kutilmagan javob. Server sozlamalarini tekshiring.")
            }
        }
        return ApiResult.Error("Internet aloqasi yo'q. Qayta urinib ko'ring.")
    }

    private companion object {
        const val NETWORK_RETRY_ATTEMPTS = 3
        const val NETWORK_RETRY_BACKOFF_MS = 400L
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
        // Qaysi qurilmadan kirganini serverga bildirib qo'yamiz — operator
        // paneli haydovchi tafsilotida shuni ko'rsatadi.
        val result = safeCall {
            api.login(mapOf("phone_number" to phone, "password" to password, "device_model" to DeviceInfo.model))
        }
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

    // `battery` — real qurilma batareya foizi (server real vaqtda kuzatib
    // borishi uchun); joylashuv bilan bir qatorda, alohida so'rovsiz yuboriladi.
    suspend fun sendLocation(lat: Double, lng: Double, battery: Int? = null) = safeCall {
        api.sendLocation(
            buildMap {
                put("lat", lat)
                put("lng", lng)
                battery?.let { put("battery", it.toDouble()) }
            },
        )
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
        savedAddressId: Int? = null,
    ) = safeCall {
        val body = mutableMapOf(
            "phone_number" to phone, "customer_name" to customerName, "to_address" to toAddress,
            "from_address" to fromAddress, "assign_to" to assignTo,
        )
        // Saqlangan manzil tanlangan bo'lsa — uning ID'si ham yuboriladi,
        // shunda server aniq koordinata (lat/lng)ni ishlatadi va "Boshqa
        // haydovchilar" tanlanganda avtomatik taqsimlashni ham ishga
        // tushiradi (taxi/driverapp_views.py: order_create). ID'siz faqat
        // manzil NOMI boradi, server esa koordinata sifatida buyurtma
        // yaratayotgan haydovchining joriy joylashuvini oladi — bu
        // "Boshqa haydovchilar" holatida noto'g'ri (buyurtma manzili u
        // yerda emas, haydovchi turgan joyda bo'lib qolardi).
        if (savedAddressId != null) body["saved_address_id"] = savedAddressId.toString()
        api.createOrder(body)
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

    suspend fun addresses(region: Int? = null, district: Int? = null, q: String? = null): ApiResult<List<AddressDto>> =
        safeCall { api.addresses(region, district, q) }

    suspend fun regions(): ApiResult<List<RegionDto>> = safeCall { api.regions() }

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

    suspend fun driverSounds(): ApiResult<Map<String, DriverSoundDto>> = safeCall { api.driverSounds() }

    suspend fun chatGroupList(sinceId: Int): ApiResult<List<GroupMessageDto>> = safeCall { api.chatGroupList(sinceId) }

    suspend fun chatGroupSend(text: String): ApiResult<GroupMessageDto> = safeCall {
        api.chatGroupSend(mapOf("text" to text))
    }

    suspend fun chatGroupUnread(): ApiResult<ChatUnreadResponse> = safeCall { api.chatGroupUnread() }
}
