package uz.vijdon.driver.data.api

import okhttp3.MultipartBody
import okhttp3.RequestBody
import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.Multipart
import retrofit2.http.POST
import retrofit2.http.Part
import retrofit2.http.Path
import retrofit2.http.Query

interface DriverApiService {

    @POST("auth/register/")
    suspend fun register(@Body body: Map<String, String>): RegisterResponse

    @POST("auth/login/")
    suspend fun login(@Body body: Map<String, String>): LoginResponse

    @GET("me/")
    suspend fun me(): DriverDto

    @GET("config/")
    suspend fun config(): ConfigDto

    @POST("duty/toggle/")
    suspend fun toggleDuty(): DutyToggleResponse

    @POST("location/")
    suspend fun sendLocation(@Body body: Map<String, Double>): LocationResponse

    @POST("fcm/")
    suspend fun syncFcmToken(@Body body: Map<String, String>): DetailResponse

    @GET("orders/available/")
    suspend fun availableOrders(): AvailableOrdersResponse

    @GET("orders/my/")
    suspend fun myOrders(): List<OrderDto>

    @POST("orders/start_taximeter/")
    suspend fun startTaximeterOrder(@Body body: Map<String, String>): OrderDto

    @POST("orders/{id}/accept/")
    suspend fun acceptOrder(@Path("id") id: Int): OrderDto

    @POST("orders/{id}/reject/")
    suspend fun rejectOrder(@Path("id") id: Int): DetailResponse

    @POST("orders/{id}/on_way/")
    suspend fun orderOnWay(@Path("id") id: Int, @Body body: Map<String, String> = emptyMap()): OrderDto

    @POST("orders/{id}/arrived/")
    suspend fun orderArrived(@Path("id") id: Int, @Body body: Map<String, String> = emptyMap()): OrderDto

    @POST("orders/{id}/complete/")
    suspend fun orderComplete(@Path("id") id: Int, @Body body: Map<String, String> = emptyMap()): OrderDto

    @POST("orders/{id}/meter/")
    suspend fun updateMeter(@Path("id") id: Int, @Body body: Map<String, String>): MeterResponse

    @GET("history/")
    suspend fun history(@Query("period") period: String): OrderHistoryResponse

    @GET("rating/")
    suspend fun rating(): RatingResponse

    @Multipart
    @POST("profile/photo/")
    suspend fun uploadPhoto(@Part photo: MultipartBody.Part): PhotoResponse

    @POST("profile/password/")
    suspend fun changePassword(@Body body: Map<String, String>): DetailResponse

    @GET("balance/history/")
    suspend fun balanceHistory(): BalanceHistoryResponse

    @Multipart
    @POST("balance/topup/")
    suspend fun requestTopup(@Part receipt: MultipartBody.Part, @Part("amount") amount: RequestBody): DetailResponse

    @GET("contract/")
    suspend fun contract(): ContractDto

    @Multipart
    @POST("contract/sign/")
    suspend fun signContract(
        @Part signature: MultipartBody.Part,
        @Part("agree") agree: RequestBody,
    ): DetailResponse

    @GET("addresses/")
    suspend fun addresses(
        @Query("region") region: Int? = null,
        @Query("district") district: Int? = null,
        @Query("q") q: String? = null,
    ): List<AddressDto>

    @GET("regions/")
    suspend fun regions(): List<RegionDto>

    @GET("addresses/current-area/")
    suspend fun currentArea(@Query("lat") lat: Double, @Query("lng") lng: Double): CurrentAreaResponse

    @GET("addresses/{id}/queue/")
    suspend fun addressQueuePosition(
        @Path("id") id: Int,
        @Query("lat") lat: Double?,
        @Query("lng") lng: Double?,
    ): QueuePositionResponse

    @GET("addresses/{id}/queue/drivers/")
    suspend fun addressQueueDrivers(@Path("id") id: Int): List<QueueDriverDto>

    @POST("destination/")
    suspend fun setDestination(@Body body: DestinationRequest): DestinationResponse

    @POST("sos/")
    suspend fun sendSos(@Body body: Map<String, String>): SosResponse

    @GET("surge/")
    suspend fun surge(): SurgeResponse

    @GET("nearby-drivers/")
    suspend fun nearbyDrivers(): List<NearbyDriverDto>

    @GET("sounds/")
    suspend fun driverSounds(): Map<String, DriverSoundDto>

    @GET("chat/")
    suspend fun chatList(): List<ChatMessageDto>

    @POST("chat/send/")
    suspend fun chatSend(@Body body: Map<String, String>): ChatMessageDto

    @GET("chat/unread/")
    suspend fun chatUnread(): ChatUnreadResponse

    @GET("chat/typing/")
    suspend fun chatTypingStatus(): ChatTypingResponse
}
