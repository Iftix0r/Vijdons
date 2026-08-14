package uz.vijdon.operator.data.challenge

import kotlinx.coroutines.runBlocking
import okhttp3.Interceptor
import okhttp3.Response
import uz.vijdon.operator.BuildConfig
import javax.inject.Inject

/**
 * Har bir so'rovga WAF tekshiruvidan "o'tgan" cookie va User-Agent'ni
 * qo'shadi. Agar javob baribir HTML (JSON emas) bo'lib chiqsa — demak
 * cookie eskirgan yoki umuman ishlamagan — WebView'ni qayta ishga tushirib,
 * so'rovni bir marta qayta yuboradi.
 */
class ChallengeInterceptor @Inject constructor(private val solver: ChallengeSolver) : Interceptor {
    override fun intercept(chain: Interceptor.Chain): Response {
        // Faqat ishlab chiqarish domeniga (BASE_URL) yuborilgan so'rovlarga
        // tegishli — lokal test serveriga (127.0.0.1) WAF yo'q, urinish shart emas.
        if (!chain.request().url.toString().startsWith(BuildConfig.BASE_URL)) {
            return chain.proceed(chain.request())
        }

        val session = runBlocking { solver.getSession() }
        val response = proceedWithSession(chain, session)
        if (session == null || isJsonResponse(response)) return response

        response.close()
        val freshSession = runBlocking { solver.getSession(forceRefresh = true) }
        return proceedWithSession(chain, freshSession)
    }

    private fun proceedWithSession(chain: Interceptor.Chain, session: ChallengeSession?): Response {
        var builder = chain.request().newBuilder()
        if (session != null) {
            builder = builder.header("Cookie", session.cookie).header("User-Agent", session.userAgent)
        }
        return chain.proceed(builder.build())
    }

    private fun isJsonResponse(response: Response): Boolean {
        val contentType = response.header("Content-Type") ?: return false
        return contentType.contains("json", ignoreCase = true)
    }
}
