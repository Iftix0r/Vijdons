package uz.vijdon.callwatcher

import android.content.Context
import android.os.Handler
import android.os.Looper
import android.util.Log
import android.webkit.CookieManager
import android.webkit.JavascriptInterface
import android.webkit.WebView
import android.webkit.WebViewClient
import org.json.JSONObject

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
    private var pendingCallResult: ((Boolean) -> Unit)? = null

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

    /** Sessiya (cookie) allaqachon mavjud deb hisoblab, qo'ng'iroq raqamini saytga yuboradi. */
    fun reportIncomingCall(baseUrl: String, phone: String, onResult: (Boolean) -> Unit) {
        val currentUrl = webView.url
        if (currentUrl.isNullOrEmpty() || !currentUrl.startsWith(baseUrl)) {
            webView.webViewClient = object : WebViewClient() {
                override fun onPageFinished(view: WebView, url: String) {
                    if (url.contains("/panel/login")) {
                        Log.w(TAG, "Sessiya tugagan ko'rinadi — ilovada qayta login qiling")
                        onResult(false)
                    } else {
                        doFetch(baseUrl, phone, onResult)
                    }
                }

                override fun onReceivedError(view: WebView, errorCode: Int, description: String?, failingUrl: String?) {
                    Log.e(TAG, "WebView xatosi (call report): $description")
                    onResult(false)
                }
            }
            webView.loadUrl(baseUrl + "panel/")
        } else {
            doFetch(baseUrl, phone, onResult)
        }
    }

    private fun doFetch(baseUrl: String, phone: String, onResult: (Boolean) -> Unit) {
        pendingCallResult = onResult
        webView.evaluateJavascript(buildFetchJs(baseUrl, phone), null)
    }

    private inner class JsBridge {
        @JavascriptInterface
        fun onCallResult(success: Boolean) {
            mainHandler.post {
                pendingCallResult?.invoke(success)
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
                    if (window.AndroidCall) window.AndroidCall.onCallResult(r.ok);
                }).catch(function(){
                    if (window.AndroidCall) window.AndroidCall.onCallResult(false);
                });
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
