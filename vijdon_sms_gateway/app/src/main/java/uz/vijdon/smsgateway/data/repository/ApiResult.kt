package uz.vijdon.smsgateway.data.repository

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(
        val message: String,
        val httpCode: Int? = null,
        val isConnectivity: Boolean = false,
    ) : ApiResult<Nothing>()
}
