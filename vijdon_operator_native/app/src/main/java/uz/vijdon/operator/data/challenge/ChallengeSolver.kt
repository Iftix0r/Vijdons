package uz.vijdon.operator.data.challenge

import android.content.Context
import android.webkit.CookieManager
import android.webkit.WebView
import android.webkit.WebViewClient
import dagger.hilt.android.qualifiers.ApplicationContext
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.sync.Mutex
import kotlinx.coroutines.sync.withLock
import kotlinx.coroutines.withContext
import kotlinx.coroutines.withTimeoutOrNull
import uz.vijdon.operator.BuildConfig
import javax.inject.Inject
import javax.inject.Singleton

data class ChallengeSession(val cookie: String, val userAgent: String)

/**
 * Ishlab chiqarish serveridagi hosting-darajasidagi bot-himoya (Imunify360
 * WAF) faqat JavaScript ishlata oladigan mijozlarni (brauzer/WebView)
 * "haqiqiy" deb hisoblaydi — oddiy HTTP klient (Retrofit/OkHttp) esa har
 * doim "One moment, please..." tekshiruv sahifasiga tushib qoladi.
 *
 * Bu klass ko'rinmas WebView orqali shu JS tekshiruvni (haqiqiy brauzerdek)
 * "yechadi" va undan chiqqan cookie'ni keshlab, keyin oddiy tarmoq
 * so'rovlarida qayta ishlatish uchun beradi — haydovchi ilovasi
 * (vijdon_driver_native) bilan bir xil mexanizm.
 */
@Singleton
class ChallengeSolver @Inject constructor(@ApplicationContext private val context: Context) {

    private val mutex = Mutex()
    private var cached: ChallengeSession? = null

    suspend fun getSession(forceRefresh: Boolean = false): ChallengeSession? = mutex.withLock {
        val current = cached
        if (!forceRefresh && current != null) return@withLock current
        val solved = solve()
        cached = solved
        solved
    }

    private suspend fun solve(): ChallengeSession? = withTimeoutOrNull(25_000) {
        withContext(Dispatchers.Main) {
            solveOnMainThread()
        }
    }

    private suspend fun solveOnMainThread(): ChallengeSession? {
        val origin = BuildConfig.CHALLENGE_ORIGIN
        val cookieManager = CookieManager.getInstance()
        cookieManager.setAcceptCookie(true)

        val webView = WebView(context)
        webView.settings.javaScriptEnabled = true
        webView.settings.domStorageEnabled = true
        val userAgent = webView.settings.userAgentString
        cookieManager.setAcceptThirdPartyCookies(webView, true)

        // Android WebView'da window.outerWidth/outerHeight doim 0 qaytadi
        // (haqiqiy brauzer oynasi "chrome"i yo'qligi sababli) — server
        // WAF'ining bot-tekshiruvi buni aynan shu asosda "bot" deb belgilab,
        // so'rovni doim rad etardi. Shu sabab WebView'ga haqiqiy o'lcham
        // beramiz VA sahifaning o'ziga xos tekshiruv skripti ishga
        // tushishidan oldin (har bir navigatsiya boshida) ushbu ikki
        // xususiyatni haqiqiy qiymat qaytaradigan qilib "yamaymiz".
        webView.measure(
            android.view.View.MeasureSpec.makeMeasureSpec(1080, android.view.View.MeasureSpec.EXACTLY),
            android.view.View.MeasureSpec.makeMeasureSpec(2280, android.view.View.MeasureSpec.EXACTLY),
        )
        webView.layout(0, 0, 1080, 2280)

        return try {
            var attempts = 0
            webView.webViewClient = object : WebViewClient() {
                override fun onPageStarted(view: WebView, url: String?, favicon: android.graphics.Bitmap?) {
                    view.evaluateJavascript(
                        "Object.defineProperty(window,'outerWidth',{get:function(){return 1080;},configurable:true});" +
                            "Object.defineProperty(window,'outerHeight',{get:function(){return 2280;},configurable:true});",
                        null,
                    )
                }
            }
            webView.loadUrl(origin)

            // WAF sahifasi o'zi 5s'da qayta yuklanadi va JS tekshiruvi
            // muvaffaqiyatli bo'lsa haqiqiy sahifaga o'tkazadi — shu sabab
            // muntazam ravishda "hali ham tekshiruv sahifasimi" deb so'rab
            // turamiz, muvaffaqiyatga erishguncha yoki taymout tugaguncha.
            while (attempts < 12) {
                delay(2_000)
                val isChallenge = evalIsChallengePage(webView)
                if (!isChallenge) break
                attempts++
            }

            val cookie = cookieManager.getCookie(origin)
            webView.destroy()
            if (cookie.isNullOrBlank()) null else ChallengeSession(cookie, userAgent)
        } catch (e: Exception) {
            webView.destroy()
            null
        }
    }

    private suspend fun evalIsChallengePage(webView: WebView): Boolean =
        kotlin.coroutines.suspendCoroutine { cont ->
            webView.evaluateJavascript("document.title") { title ->
                cont.resumeWith(Result.success(title?.contains("moment", ignoreCase = true) == true))
            }
        }
}
