package uz.vijdon.driver.data.api

import kotlinx.serialization.Serializable

@Serializable
data class DriverDto(
    val id: Int,
    val full_name: String,
    val phone_number: String,
    val car_model: String,
    val car_number: String,
    val car_type: String,
    val car_type_display: String,
    val is_active: Boolean,
    val is_on_duty: Boolean,
    val is_frozen: Boolean,
    val approval_status: String,
    val approval_status_display: String,
    val registered_at: String,
    val balance: String,
    val rating: String,
    val trips_count: Int,
    val level: String,
    val photo_url: String? = null,
    val destination_mode: Boolean = false,
    val destination_lat: Double? = null,
    val destination_lng: Double? = null,
    val destination_address: String = "",
) {
    val isApproved: Boolean get() = approval_status == "approved"
    val isPending: Boolean get() = approval_status == "pending"
    val isRejected: Boolean get() = approval_status == "rejected"
}

@Serializable
data class LoginResponse(val token: String, val driver: DriverDto)

@Serializable
data class RegisterResponse(val detail: String, val driver_id: Int)

@Serializable
data class ConfigDto(
    val base_price: Double,
    val price_per_km: Double,
    val waiting_price_per_minute: Double,
    val commission: Double,
    val operator_phone: String,
    val yandex_api_key: String,
)

@Serializable
data class DutyToggleResponse(val is_on_duty: Boolean)

@Serializable
data class LocationResponse(val latitude: Double, val longitude: Double)

@Serializable
data class DetailResponse(val detail: String)

@Serializable
data class AvailableOrdersResponse(
    val orders: List<OrderDto>,
    val low_balance: Boolean,
)

@Serializable
data class MeterResponse(val dist_km: Double, val price: Double)

@Serializable
data class OrderDto(
    val id: Int,
    val status: String,
    val status_label: String,
    val from_address: String,
    val from_lat: Double? = null,
    val from_lng: Double? = null,
    val to_address: String,
    val to_lat: Double? = null,
    val to_lng: Double? = null,
    val client_name: String,
    val client_phone: String,
    val client_rating: Double? = null,
    val client_trips_count: Int? = null,
    val price: String? = null,
    val commission: String? = null,
    val distance_km: Double? = null,
    val payment_type: String,
    val payment_type_display: String,
    val car_type: String,
    val car_type_display: String,
    val note: String,
    val is_dispatched: Boolean,
    val timer_sec: Int? = null,
    val tmx_dist_km: Double = 0.0,
    val tmx_paused: Boolean = false,
    val tmx_paused_ms: Long = 0,
    val tmx_start_time: String? = null,
    val created_at: String,
    val updated_at: String,
) {
    val isPending: Boolean get() = status == "pending"
    val isAccepted: Boolean get() = status == "accepted"
    val isOnWay: Boolean get() = status == "on_way"
    val isArrived: Boolean get() = status == "arrived"
    val isActive: Boolean get() = status in setOf("accepted", "on_way", "arrived")
}
