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

@Serializable
data class OrderHistoryResponse(
    val orders: List<OrderDto>,
    val total_earned: Double,
    val completed: Int,
)

@Serializable
data class RatingRowDto(
    val rank: Int,
    val full_name: String,
    val completed: Int,
    val earned: Int,
    val is_me: Boolean,
)

@Serializable
data class RatingResponse(
    val rows: List<RatingRowDto>,
    val my_row: RatingRowDto? = null,
    val gap_to_next: Int? = null,
)

@Serializable
data class PhotoResponse(val photo_url: String)

@Serializable
data class BalanceEntryDto(val is_income: Boolean, val amount: String, val note: String, val created_at: String)

@Serializable
data class BalanceHistoryResponse(val entries: List<BalanceEntryDto>, val balance: String)

@Serializable
data class ContractDto(val title: String, val content: String, val version: Int, val signed: Boolean)

@Serializable
data class AddressDto(
    val id: Int,
    val name: String,
    val address: String,
    val lat: Double,
    val lng: Double,
    val today_orders: Int,
    val queue_count: Int,
)

@Serializable
data class QueuePositionResponse(val position: Int? = null, val total: Int = 0)

@Serializable
data class QueueDriverDto(
    val position: Int,
    val full_name: String,
    val car_model: String,
    val car_number: String,
    val joined_at: String,
    val is_me: Boolean,
)

@Serializable
data class DestinationRequest(
    val lat: Double? = null,
    val lng: Double? = null,
    val address: String? = null,
    val clear: Boolean? = null,
)

@Serializable
data class DestinationResponse(val active: Boolean)

@Serializable
data class SosResponse(val id: Int)

@Serializable
data class SurgeResponse(val multiplier: Double, val reason: String)

@Serializable
data class NearbyDriverDto(
    val id: Int,
    val full_name: String,
    val car_type: String,
    val car_model: String,
    val car_number: String,
    val photo_url: String,
    val latitude: Double,
    val longitude: Double,
    val trips_count: Int,
    val rating: Double,
    val level: String,
)

/** Veb paneldagi `PanelSound` bilan bir xil — operator sozlagan (yoki
 * standart) ovoz fayli. `url` to'liq (absolute) manzil, `null` bo'lsa
 * o'sha hodisa uchun ovoz yo'q (chalinmaydi). */
@Serializable
data class DriverSoundDto(val enabled: Boolean, val url: String? = null)
