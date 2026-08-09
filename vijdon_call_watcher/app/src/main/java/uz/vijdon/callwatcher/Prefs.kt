package uz.vijdon.callwatcher

import android.content.Context
import android.content.SharedPreferences

/** Sayt manzili, operator tokeni va xizmat holatini saqlaydi. */
class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.getSharedPreferences("vijdon_call_watcher", Context.MODE_PRIVATE)

    var siteUrl: String
        get() = sp.getString(KEY_SITE_URL, DEFAULT_SITE_URL) ?: DEFAULT_SITE_URL
        set(value) = sp.edit().putString(KEY_SITE_URL, value).apply()

    var token: String?
        get() = sp.getString(KEY_TOKEN, null)
        set(value) = sp.edit().putString(KEY_TOKEN, value).apply()

    var username: String?
        get() = sp.getString(KEY_USERNAME, null)
        set(value) = sp.edit().putString(KEY_USERNAME, value).apply()

    var serviceEnabled: Boolean
        get() = sp.getBoolean(KEY_SERVICE_ENABLED, false)
        set(value) = sp.edit().putBoolean(KEY_SERVICE_ENABLED, value).apply()

    fun clearSession() {
        sp.edit()
            .remove(KEY_TOKEN)
            .remove(KEY_USERNAME)
            .putBoolean(KEY_SERVICE_ENABLED, false)
            .apply()
    }

    companion object {
        private const val KEY_SITE_URL = "site_url"
        private const val KEY_TOKEN = "token"
        private const val KEY_USERNAME = "username"
        private const val KEY_SERVICE_ENABLED = "service_enabled"
        const val DEFAULT_SITE_URL = "https://vijdontaxi.uz"
    }
}
