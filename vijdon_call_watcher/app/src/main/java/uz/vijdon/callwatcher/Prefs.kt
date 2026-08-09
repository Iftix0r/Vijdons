package uz.vijdon.callwatcher

import android.content.Context
import android.content.SharedPreferences

/** Sayt manzili, kirish holati va xizmat holatini saqlaydi.
 * Diqqat: token endi saqlanmaydi — sessiya WebView'ning o'z cookie
 * ombori (CookieManager, diskka saqlanadi) orqali ushlab turiladi;
 * shu klass faqat "kirilganmi" bayrog'ini saqlaydi. */
class Prefs(context: Context) {
    private val sp: SharedPreferences =
        context.getSharedPreferences("vijdon_call_watcher", Context.MODE_PRIVATE)

    var siteUrl: String
        get() = sp.getString(KEY_SITE_URL, DEFAULT_SITE_URL) ?: DEFAULT_SITE_URL
        set(value) = sp.edit().putString(KEY_SITE_URL, value).apply()

    var loggedIn: Boolean
        get() = sp.getBoolean(KEY_LOGGED_IN, false)
        set(value) = sp.edit().putBoolean(KEY_LOGGED_IN, value).apply()

    var username: String?
        get() = sp.getString(KEY_USERNAME, null)
        set(value) = sp.edit().putString(KEY_USERNAME, value).apply()

    var serviceEnabled: Boolean
        get() = sp.getBoolean(KEY_SERVICE_ENABLED, false)
        set(value) = sp.edit().putBoolean(KEY_SERVICE_ENABLED, value).apply()

    /** Qaysi audio manbadan (CallRecorder.AUDIO_SOURCES indeksi) boshlash kerakligi —
     * bir manba jim chiqsa, keyingi qo'ng'iroqda ro'yxatdagi keyingisidan boshlanadi. */
    var audioSourceIndex: Int
        get() = sp.getInt(KEY_AUDIO_SOURCE_INDEX, 0)
        set(value) = sp.edit().putInt(KEY_AUDIO_SOURCE_INDEX, value).apply()

    fun clearSession() {
        sp.edit()
            .putBoolean(KEY_LOGGED_IN, false)
            .remove(KEY_USERNAME)
            .putBoolean(KEY_SERVICE_ENABLED, false)
            .apply()
    }

    companion object {
        private const val KEY_SITE_URL = "site_url"
        private const val KEY_LOGGED_IN = "logged_in"
        private const val KEY_USERNAME = "username"
        private const val KEY_SERVICE_ENABLED = "service_enabled"
        private const val KEY_AUDIO_SOURCE_INDEX = "audio_source_index"
        const val DEFAULT_SITE_URL = "https://vijdontaxi.uz"
    }
}
