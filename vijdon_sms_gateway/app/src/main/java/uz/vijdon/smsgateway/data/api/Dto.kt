package uz.vijdon.smsgateway.data.api

import kotlinx.serialization.Serializable

@Serializable
data class LoginResponse(val token: String, val username: String)

@Serializable
data class DetailResponse(val detail: String? = null)

@Serializable
data class PendingSmsDto(
    val id: Int,
    val phone_number: String,
    val text: String,
    val created_at: String,
)
