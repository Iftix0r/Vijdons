package uz.vijdon.smsgateway.data.api

import retrofit2.http.Body
import retrofit2.http.GET
import retrofit2.http.POST
import retrofit2.http.Path
import retrofit2.http.Url

interface SmsGatewayApiService {

    // To'liq (nisbiy bo'lmagan) yo'l — bu login mavjud `/panel/api/operator/`
    // ostida, `/api/smsgatewayapp/` prefiksidan FARQLI (taxi/api_views.py:
    // operator_login, qo'ng'iroq-kuzatuvchi ilova ham shundan foydalanadi).
    @POST
    suspend fun login(@Url url: String, @Body body: Map<String, String>): LoginResponse

    @POST("api/smsgatewayapp/fcm/")
    suspend fun syncFcmToken(@Body body: Map<String, String>): DetailResponse

    @GET("api/smsgatewayapp/pending/")
    suspend fun pending(): List<PendingSmsDto>

    @POST("api/smsgatewayapp/{id}/result/")
    suspend fun reportResult(@Path("id") id: Int, @Body body: Map<String, String>): DetailResponse

    @POST("api/smsgatewayapp/incoming/")
    suspend fun reportIncoming(@Body body: Map<String, String>): DetailResponse
}
