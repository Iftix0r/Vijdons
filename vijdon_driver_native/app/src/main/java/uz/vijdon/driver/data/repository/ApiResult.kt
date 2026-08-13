package uz.vijdon.driver.data.repository

sealed class ApiResult<out T> {
    data class Success<T>(val data: T) : ApiResult<T>()
    data class Error(
        val message: String,
        val code: String? = null,
        val httpCode: Int? = null,
        // So'rov serverga umuman yetib bormagan (sof tarmoq/ulanish xatosi,
        // safeCall ichida allaqachon bir necha marta qayta urinilgan)
        // holatda true — bunga qarab chaqiruvchi qayta urinish strategiyasini
        // moslashtira oladi (masalan SessionViewModel.refresh()).
        val isConnectivity: Boolean = false,
    ) : ApiResult<Nothing>()
}

/** Backend `code` maydoni orqali qaysi holat ekranini ko'rsatish kerakligini bildiradi. */
object ApiErrorCode {
    const val PENDING = "pending"
    const val FROZEN = "frozen"
    const val REJECTED = "rejected"
    const val NO_PROFILE = "no_profile"
}
