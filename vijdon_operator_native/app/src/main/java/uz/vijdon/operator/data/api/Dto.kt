package uz.vijdon.operator.data.api

import kotlinx.serialization.Serializable

@Serializable
data class OperatorDto(
    val id: Int,
    val username: String,
    val full_name: String,
    val is_superuser: Boolean,
)

@Serializable
data class LoginResponse(val token: String, val operator: OperatorDto)

@Serializable
data class DetailResponse(val detail: String? = null, val status: String? = null)

@Serializable
data class DashboardDto(
    val today_orders: Int,
    val today_revenue: String,
    val pending_orders: Int,
    val aging_orders: Int,
    val on_duty_drivers: Int,
    val online_drivers: Int,
    val pending_driver_approvals: Int,
    val low_balance_drivers: Int,
    val pending_topups: Int,
    val aging_topups: Int,
)

@Serializable
data class RejectedByDto(val id: Int, val full_name: String)

@Serializable
data class DispatchAttemptDto(
    val driver_id: Int,
    val driver_name: String,
    val distance_km: Double? = null,
    val attempt_number: Int,
    val result: String,
    val result_label: String,
    val created_at: String,
    val resolved_at: String? = null,
)

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
    val on_way_address: String = "",
    val arrived_address: String = "",
    val client_id: Int,
    val client_name: String,
    val client_phone: String,
    val client_is_blocked: Boolean,
    val driver_id: Int? = null,
    val driver_name: String? = null,
    val driver_phone: String? = null,
    val dispatched_to_id: Int? = null,
    val dispatched_to_name: String? = null,
    val dispatched_at: String? = null,
    val price: String? = null,
    val commission: String,
    val distance_km: Double? = null,
    val payment_type: String,
    val payment_type_display: String,
    val car_type: String,
    val car_type_display: String,
    val is_delivery: Boolean,
    val note: String = "",
    val cancel_reason: String = "",
    val rejected_by: List<RejectedByDto> = emptyList(),
    val dispatch_attempts: List<DispatchAttemptDto> = emptyList(),
    val created_at: String,
    val updated_at: String,
) {
    val isPending: Boolean get() = status == "pending"
    val isActive: Boolean get() = status in listOf("accepted", "on_way", "arrived")
}

@Serializable
data class OrderListResponse(val orders: List<OrderDto>, val page: Int, val has_next: Boolean, val total_count: Int)

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
    val is_qarzdor: Boolean,
    val qarz_note: String = "",
    val approval_status: String,
    val approval_status_display: String,
    val registered_at: String,
    val balance: String,
    val rating: String,
    val trips_count: Int,
    val photo_url: String? = null,
    val last_seen: String? = null,
    val is_online: Boolean,
    val completed_count: Int? = null,
    val cancelled_count: Int? = null,
) {
    val isApproved: Boolean get() = approval_status == "approved"
    val isPending: Boolean get() = approval_status == "pending"
}

@Serializable
data class DriverListResponse(
    val drivers: List<DriverDto>,
    val page: Int,
    val has_next: Boolean,
    val total_count: Int,
    val pending_count: Int,
    val approved_count: Int,
    val rejected_count: Int,
)

@Serializable
data class DriverDetailResponse(val driver: DriverDto, val recent_orders: List<OrderDto>)

@Serializable
data class LiveDriverDto(
    val id: Int,
    val full_name: String,
    val phone_number: String,
    val car_model: String,
    val car_number: String,
    val latitude: Double,
    val longitude: Double,
    val balance: String,
    val today_orders_count: Int,
    val last_address: String = "",
    val is_online: Boolean,
    val is_on_duty: Boolean,
)

@Serializable
data class DriverLiveResponse(val drivers: List<LiveDriverDto>)

@Serializable
data class ChatMessageDto(
    val id: Int,
    val sender: String,
    val text: String,
    val is_read: Boolean,
    val created_at: String,
) {
    val isFromDriver: Boolean get() = sender == "driver"
}

@Serializable
data class ChatDriverSummaryDto(
    val driver_id: Int,
    val full_name: String,
    val car_number: String,
    val last_message: ChatMessageDto? = null,
    val unread: Int,
)

@Serializable
data class ChatUnreadResponse(val count: Int)

@Serializable
data class GroupMessageDto(
    val id: Int,
    val sender_name: String,
    val text: String,
    val is_driver: Boolean,
    val created_at: String,
)

@Serializable
data class TopupDto(
    val id: Int,
    val driver_id: Int,
    val driver_name: String,
    val driver_phone: String,
    val amount: String,
    val receipt_url: String? = null,
    val status: String,
    val reject_reason: String = "",
    val created_at: String,
    val resolved_at: String? = null,
)

@Serializable
data class TopupListResponse(val requests: List<TopupDto>, val pending_count: Int)

@Serializable
data class BalanceLogEntryDto(
    val id: Int,
    val driver_id: Int,
    val driver_name: String,
    val action: String,
    val amount: String,
    val balance_after: String,
    val note: String = "",
    val created_at: String,
) {
    val isIncome: Boolean get() = action == "add"
}

@Serializable
data class BalanceLogResponse(val entries: List<BalanceLogEntryDto>, val page: Int, val has_next: Boolean, val total_count: Int)
