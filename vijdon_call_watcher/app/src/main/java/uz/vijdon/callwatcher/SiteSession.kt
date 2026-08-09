package uz.vijdon.callwatcher

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Base64
import android.util.Log
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject
import java.io.File

/**
 * Saytga haqiqiy brauzer dvigateli (WebView) orqali ulanadi — shunday qilib
 * server oldidagi bot-tekshiruv (JavaScript challenge) sahifasi muammosiz
 * o'tiladi, xuddi haydovchi/mijoz ilovalari (WebView shell) qanday ishlasa
 * xuddi shunday. Oddiy HTTP so'rov (OkHttp/curl) JavaScript bajara olmagani
 * uchun bu tekshiruvdan hech qachon o'ta olmaydi.
 */
class SiteSession(context: Context, private val webView: WebView) {

    private val appContext = context.applicationContext
    private val mainHandler = Handler(Looper.getMainLooper())
    private var pendingCallResult: ((Boolean, String) -> Unit)? = null

    init {
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        webView.settings.userAgentString = webView.settings.userAgentString + " VijdonCallWatcher/1.0"
        CookieManager.getInstance().setAcceptCookie(true)
        CookieManager.getInstance().setAcceptThirdPartyCookies(webView, true)
        webView.addJavascriptInterface(JsBridge(), "AndroidCall")
    }

    /** Operator login/parolini haqiqiy brauzer sifatida saytning /panel/login/ shakliga yuboradi. */
    fun login(baseUrl: String, username: String, password: String, onResult: (Boolean, String?) -> Unit) {
        val loginUrl = baseUrl + "panel/login/"
        var attempts = 0
        var submitted = false
        var finished = false

        fun finish(success: Boolean, message: String?) {
            if (finished) return
            finished = true
            if (success) {
                CookieManager.getInstance().flush()
            }
            onResult(success, message)
        }

        webView.webViewClient = object : WebViewClient() {
            override fun onPageFinished(view: WebView, url: String) {
                if (finished) return
                attempts++
                if (!submitted) {
                    view.evaluateJavascript(FORM_CHECK_JS) { result ->
                        if (finished) return@evaluateJavascript
                        if (result?.trim('"') == "true") {
                            submitted = true
                            view.evaluateJavascript(buildSubmitJs(username, password), null)
                        } else if (attempts >= MAX_CHALLENGE_ATTEMPTS) {
                            finish(false, appContext.getString(R.string.error_login_failed))
                        }
                        // aks holda: hali tekshiruv sahifasi — o'zi qayta yuklanishini kutamiz
                    }
                } else {
                    if (!url.contains("/panel/login")) {
                        finish(true, null)
                    } else {
                        view.evaluateJavascript(ERROR_CHECK_JS) { result ->
                            if (finished) return@evaluateJavascript
                            if (result?.trim('"') == "true") {
                                finish(false, appContext.getString(R.string.error_login_failed))
                            } else if (attempts >= MAX_CHALLENGE_ATTEMPTS + MAX_SUBMIT_ATTEMPTS) {
                                finish(false, appContext.getString(R.string.error_login_failed))
                            }
                        }
                    }
                }
            }

            override fun onReceivedError(view: WebView, errorCode: Int, description: String?, failingUrl: String?) {
                Log.e(TAG, "WebView xatosi: $description ($failingUrl)")
                finish(false, "Tarmoq xatosi")
            }
        }
        webView.loadUrl(loginUrl)
    }

    /** Sessiya (cookie) allaqachon mavjud deb hisoblab, qo'ng'iroq raqamini saytga yuboradi.
     * onResult(success, detail) — detail diagnostika uchun (masalan "HTTP 401"). */
    fun reportIncomingCall(baseUrl: String, phone: String, onResult: (Boolean, String) -> Unit) {
        ensureSessionThen(baseUrl, onResult) {
            pendingCallResult = onResult
            webView.evaluateJavascript(buildFetchJs(baseUrl, phone), null)
        }
    }

    /** Yozilgan qo'ng'iroq audio faylini saytga yuklaydi (base64 orqali WebView'ning
     * o'z fetch()'iga uzatiladi — shu bilan WAF challenge muammosidan qochiladi). */
    fun uploadCallRecording(baseUrl: String, phone: String, file: File, durationSec: Int, onResult: (Boolean, String) -> Unit) {
        ensureSessionThen(baseUrl, onResult) {
            val base64 = try {
                Base64.encodeToString(file.readBytes(), Base64.NO_WRAP)
            } catch (e: Exception) {
                Log.e(TAG, "Fayl o'qishda xato", e)
                onResult(false, "fayl o'qib bo'lmadi")
                return@ensureSessionThen
            }
            pendingCallResult = onResult
            webView.evaluateJavascript(buildUploadJs(baseUrl, phone, durationSec, base64), null)
        }
    }

    /** Sessiya sahifasi (bir marta) yuklanganini ta'minlab, so'ng berilgan amalni bajaradi. */
    private fun ensureSessionThen(baseUrl: String, onFail: (Boolean, String) -> Unit, action: () -> Unit) {
        val currentUrl = webView.url
        if (currentUrl.isNullOrEmpty() || !currentUrl.startsWith(baseUrl)) {
            webView.webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    if (url.contains("/panel/login")) {
                        Log.w(TAG, "Sessiya tugagan ko'rinadi — ilovada qayta login qiling")
                        onFail(false, "sessiya tugagan")
                    } else {
                        action()
                    }
                }

                override fun onReceivedError(view: WebView, errorCode: Int, description: String?, failingUrl: String?) {
                    Log.e(TAG, "WebView xatosi: $description")
                    onFail(false, description ?: "tarmoq xatosi")
                }
            }
            webView.loadUrl(baseUrl + "panel/")
        } else {
            action()
        }
    }

    private inner class JsBridge {
        @JavascriptInterface
        fun onCallResult(success: Boolean, detail: String) {
            mainHandler.post {
                pendingCallResult?.invoke(success, detail)
                pendingCallResult = null
            }
        }
    }

    private fun buildSubmitJs(username: String, password: String): String {
        val u = JSONObject.quote(username)
        val p = JSONObject.quote(password)
        return """
            (function(){
                var f = document.querySelector('form');
                var u = document.querySelector('input[name=username]');
                var p = document.querySelector('input[name=password]');
                if(!f || !u || !p) return false;
                u.value = $u;
                p.value = $p;
                f.submit();
                return true;
            })();
        """.trimIndent()
    }

    private fun buildFetchJs(baseUrl: String, phone: String): String {
        val url = JSONObject.quote(baseUrl + "panel/api/operator/incoming-call/")
        val phoneJson = JSONObject.quote(phone)
        return """
            (function(){
                function getCookie(name) {
                    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
                    return m ? m.pop() : '';
                }
                fetch($url, {
                    method: 'POST',
                    credentials: 'same-origin',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCookie('csrftoken')
                    },
                    body: JSON.stringify({phone_number: $phoneJson})
                }).then(function(r){
                    if (window.AndroidCall) window.AndroidCall.onCallResult(r.ok, 'HTTP ' + r.status);
                }).catch(function(e){
                    if (window.AndroidCall) window.AndroidCall.onCallResult(false, String(e));
                });
            })();
        """.trimIndent()
    }

    private fun buildUploadJs(baseUrl: String, phone: String, durationSec: Int, base64Audio: String): String {
        val url = JSONObject.quote(baseUrl + "panel/api/operator/call-recording/")
        val phoneJson = JSONObject.quote(phone)
        val b64Json = JSONObject.quote(base64Audio)
        return """
            (function(){
                function getCookie(name) {
                    var m = document.cookie.match('(^|;)\\s*' + name + '\\s*=\\s*([^;]+)');
                    return m ? m.pop() : '';
                }
                try {
                    var byteChars = atob($b64Json);
                    var byteNumbers = new Array(byteChars.length);
                    for (var i = 0; i < byteChars.length; i++) { byteNumbers[i] = byteChars.charCodeAt(i); }
                    var blob = new Blob([new Uint8Array(byteNumbers)], { type: 'audio/mp4' });
                    var fd = new FormData();
                    fd.append('audio', blob, 'call.m4a');
                    fd.append('phone_number', $phoneJson);
                    fd.append('duration_sec', '$durationSec');
                    fetch($url, {
                        method: 'POST',
                        credentials: 'same-origin',
                        headers: { 'X-CSRFToken': getCookie('csrftoken') },
                        body: fd
                    }).then(function(r){
                        if (window.AndroidCall) window.AndroidCall.onCallResult(r.ok, 'HTTP ' + r.status);
                    }).catch(function(e){
                        if (window.AndroidCall) window.AndroidCall.onCallResult(false, String(e));
                    });
                } catch (e) {
                    if (window.AndroidCall) window.AndroidCall.onCallResult(false, 'JS xato: ' + String(e));
                }
            })();
        """.trimIndent()
    }

    companion object {
        fun normalizeBaseUrl(raw: String): String {
            var url = raw.trim()
            if (!url.startsWith("http://") && !url.startsWith("https://")) url = "https://$url"
            if (!url.endsWith("/")) url += "/"
            return url
        }

        private const val TAG = "VijdonSiteSession"
        private const val MAX_CHALLENGE_ATTEMPTS = 10
        private const val MAX_SUBMIT_ATTEMPTS = 4
        private const val FORM_CHECK_JS = "(!!document.querySelector('input[name=username]')).toString();"

        // views.py'dagi xato xabari — "Login yoki parol noto'g'ri!" — shu matn
        // sahifada bor-yo'qligini tekshiradi (apostrof — oddiy ASCII belgisi).
        private val ERROR_CHECK_JS = """
            (document.body && document.body.innerText.indexOf("noto'g'ri") !== -1).toString();
        """.trimIndent()
    }
}
