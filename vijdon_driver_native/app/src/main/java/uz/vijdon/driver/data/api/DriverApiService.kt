package uz.vijdon.driver.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path

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
}
