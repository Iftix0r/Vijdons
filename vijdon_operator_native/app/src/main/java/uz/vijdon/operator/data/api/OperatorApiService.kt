package uz.vijdon.operator.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Query

interface OperatorApiService {

    @POST("auth/login/")
    suspend fun login(@Body body: Map<String, String>): LoginResponse

    @GET("me/")
    suspend fun me(): OperatorDto

    @POST("fcm/")
    suspend fun syncFcmToken(@Body body: Map<String, String>): DetailResponse

    @GET("dashboard/")
    suspend fun dashboard(): DashboardDto

    @GET("orders/")
    suspend fun orders(
        @Query("q") q: String? = null,
        @Query("status") status: String? = null,
        @Query("page") page: Int? = null,
    ): OrderListResponse

    @GET("orders/{id}/")
    suspend fun orderDetail(@Path("id") id: Int): OrderDto

    @POST("orders/create/")
    suspend fun createOrder(@Body body: Map<String, String>): OrderDto

    @POST("orders/{id}/status/")
    suspend fun updateOrderStatus(@Path("id") id: Int, @Body body: Map<String, String>): OrderDto

    @POST("orders/{id}/dispatch/")
    suspend fun dispatchOrder(@Path("id") id: Int): OrderDto

    @POST("orders/{id}/cancel/")
    suspend fun cancelOrder(@Path("id") id: Int): OrderDto

    @POST("orders/{id}/delete/")
    suspend fun deleteOrder(@Path("id") id: Int): DetailResponse

    @GET("drivers/")
    suspend fun drivers(
        @Query("tab") tab: String? = null,
        @Query("q") q: String? = null,
        @Query("sort") sort: String? = null,
        @Query("page") page: Int? = null,
    ): DriverListResponse

    @GET("drivers/live/")
    suspend fun driversLive(): DriverLiveResponse

    @GET("drivers/{id}/")
    suspend fun driverDetail(@Path("id") id: Int): DriverDetailResponse

    @POST("drivers/{id}/approve/")
    suspend fun driverApprove(@Path("id") id: Int, @Body body: Map<String, String>): DriverDto

    @POST("drivers/{id}/toggle_active/")
    suspend fun driverToggleActive(@Path("id") id: Int): DriverDto

    @POST("drivers/{id}/toggle_frozen/")
    suspend fun driverToggleFrozen(@Path("id") id: Int): DriverDto

    @POST("drivers/{id}/recharge/")
    suspend fun driverRecharge(@Path("id") id: Int, @Body body: Map<String, String>): DriverDto

    @GET("chat/drivers/")
    suspend fun chatDriverList(): List<ChatDriverSummaryDto>

    @GET("chat/{driverId}/messages/")
    suspend fun chatMessages(@Path("driverId") driverId: Int): List<ChatMessageDto>

    @POST("chat/{driverId}/send/")
    suspend fun chatSend(@Path("driverId") driverId: Int, @Body body: Map<String, String>): ChatMessageDto

    @GET("chat/unread/")
    suspend fun chatUnread(): ChatUnreadResponse

    @GET("chat/group/")
    suspend fun chatGroupList(): List<GroupMessageDto>

    @POST("chat/group/send/")
    suspend fun chatGroupSend(@Body body: Map<String, String>): GroupMessageDto

    @GET("balance/topups/")
    suspend fun topups(@Query("status") status: String? = null): TopupListResponse

    @POST("balance/topups/{id}/resolve/")
    suspend fun topupResolve(@Path("id") id: Int, @Body body: Map<String, String>): DetailResponse

    @GET("balance/log/")
    suspend fun balanceLog(@Query("q") q: String? = null, @Query("action") action: String? = null, @Query("page") page: Int? = null): BalanceLogResponse
}
