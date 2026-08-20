package uz.vijdon.driver.data.repository

import android.content.Context
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.serialization.encodeToString
import kotlinx.serialization.json.Json
import uz.vijdon.driver.data.api.AddressDto
import uz.vijdon.driver.data.api.AvailableOrdersResponse
import javax.inject.Inject
import javax.inject.Singleton

/**
 * Oxirgi muvaffaqiyatli server javobini SharedPreferences da saqlaydi.
 * Internet uzilganda HomeViewModel shu keshdan foydalanadi — haydovchi
 * bo'sh ekran o'rniga oxirgi ma'lumotni ko'radi.
 */
@Singleton
class OfflineCache @Inject constructor(
    @ApplicationContext private val context: Context,
    private val json: Json,
) {
    private val prefs by lazy { context.getSharedPreferences("vijdon_offline_cache", Context.MODE_PRIVATE) }

    fun saveOrders(response: AvailableOrdersResponse) {
        prefs.edit().putString(KEY_ORDERS, json.encodeToString(response)).apply()
    }

    fun loadOrders(): AvailableOrdersResponse? = prefs.getString(KEY_ORDERS, null)?.let {
        runCatching { json.decodeFromString<AvailableOrdersResponse>(it) }.getOrNull()
    }

    fun saveAddresses(addresses: List<AddressDto>) {
        prefs.edit().putString(KEY_ADDRESSES, json.encodeToString(addresses)).apply()
    }

    fun loadAddresses(): List<AddressDto>? = prefs.getString(KEY_ADDRESSES, null)?.let {
        runCatching { json.decodeFromString<List<AddressDto>>(it) }.getOrNull()
    }

    fun clear() = prefs.edit().clear().apply()

    private companion object {
        const val KEY_ORDERS = "orders"
        const val KEY_ADDRESSES = "addresses"
    }
}
