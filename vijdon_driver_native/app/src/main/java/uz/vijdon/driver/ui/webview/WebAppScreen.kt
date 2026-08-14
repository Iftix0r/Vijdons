package uz.vijdon.driver.ui.webview

import android.annotation.SuppressLint
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.viewinterop.AndroidView
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Pastki pager'dagi "yon" bo'lim (YouTube) uchun umumiy WebView qobiq —
 * haydovchi navbatda kutayotganda tashqi saytdan foydalanishi uchun.
 * `url` parametri orqali boshqa saytlar uchun ham qayta ishlatilishi
 * mumkin (`ApprovedScaffold.kt`).
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun WebAppScreen(url: String) {
    val context = LocalContext.current
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var progress by remember { mutableFloatStateOf(0f) }
    var loading by remember { mutableStateOf(true) }

    // Tizim "Orqaga" tugmasi — agar sayt ichida (masalan video/post
    // sahifasidan ro'yxatga) sahifa tarixi bo'lsa, avval o'sha ichki
    // tarixga qaytadi, aks holda odatdagidek ilova navigatsiyasiga beriladi.
    BackHandler(enabled = webViewRef?.canGoBack() == true) {
        webViewRef?.goBack()
    }

    Box(modifier = Modifier.fillMaxSize()) {
        AndroidView(
            modifier = Modifier.fillMaxSize(),
            factory = {
                WebView(context).apply {
                    layoutParams = ViewGroup.LayoutParams(ViewGroup.LayoutParams.MATCH_PARENT, ViewGroup.LayoutParams.MATCH_PARENT)
                    settings.javaScriptEnabled = true
                    settings.domStorageEnabled = true
                    settings.mediaPlaybackRequiresUserGesture = false
                    settings.loadWithOverviewMode = true
                    settings.useWideViewPort = true
                    // GPU kompozitsiyasi — video/tez skroll (Shorts) silliq
                    // ishlashi uchun. Sukut bo'yicha yoqilgan bo'lishi kerak,
                    // lekin ba'zi qurilma/ilova holatlarida WebView dasturiy
                    // (software) qatlamga tushib qolib, sekinlashishi mumkin.
                    setLayerType(android.view.View.LAYER_TYPE_HARDWARE, null)
                    // Bu ekran HorizontalPager'ning BITTA sahifasi — pager
                    // har bir teginish harakatini "sahifa gorizontal
                    // almashtirilyaptimi" deb tekshiradi, bu esa Shorts'dagi
                    // TEZ VERTIKAL svayplarni "yeb qo'yib", WebView'ga
                    // kechikib/qisman yetkazib berishi mumkin edi (sekin,
                    // "yopishqoq" harakat sifatida sezilardi). Teginish
                    // boshlanishi bilan ota-ona (pager)ga uni to'xtatishni
                    // taqiqlab qo'yamiz — shu orqali butun svayp to'g'ridan-
                    // to'g'ri, hech qanday kechikishsiz WebView'ning o'ziga
                    // boradi (standart Android "ichki scroll tashqi
                    // svayp bilan to'qnashmasin" yechimi).
                    setOnTouchListener { v, _ ->
                        v.parent?.requestDisallowInterceptTouchEvent(true)
                        false
                    }
                    webViewClient = object : WebViewClient() {
                        // YouTube mobil saytining o'z tepa panelidagi
                        // "hamburger" (asosiy menyu) tugmasi ilova ichida
                        // keraksiz — bosilsa YouTube'ning o'z navigatsiya
                        // panelini ochib, kichik ekranda joy band qiladi.
                        // Sof CSS/JS bilan yashiriladi (server tomonidan
                        // emas, chunki bu YouTube'ning o'z sahifasi) —
                        // DIQQAT: YouTube o'z HTML tuzilishini istalgan
                        // vaqt o'zgartirishi mumkin, shu sabab bu "eng
                        // ehtimolli" selektorlar bilan yozilgan va vaqti
                        // bilan ishlamay qolishi mumkin.
                        override fun onPageFinished(view: WebView, loadedUrl: String) {
                            super.onPageFinished(view, loadedUrl)
                            if (loadedUrl.contains("youtube.com")) {
                                view.evaluateJavascript(
                                    """
                                    (function() {
                                        var css = 'ytm-topbar-menu-button-renderer:first-of-type,'
                                            + 'button[aria-label="Guide"],'
                                            + 'tp-yt-iron-icon[icon="yt-icons:menu"],'
                                            + '.topbar-menu-button-guide {'
                                            + 'display: none !important; }';
                                        var style = document.createElement('style');
                                        style.appendChild(document.createTextNode(css));
                                        document.head.appendChild(style);
                                    })();
                                    """.trimIndent(),
                                    null,
                                )
                            }
                        }
                    }
                    webChromeClient = object : WebChromeClient() {
                        override fun onProgressChanged(view: WebView, newProgress: Int) {
                            progress = newProgress / 100f
                            loading = newProgress < 100
                        }
                    }
                    loadUrl(url)
                    webViewRef = this
                }
            },
        )
        if (loading) {
            LinearProgressIndicator(
                progress = { progress },
                color = VijdonColors.Yellow,
                modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter),
            )
        }
    }

    DisposableEffect(Unit) {
        onDispose {
            webViewRef?.apply {
                stopLoading()
                destroy()
            }
            webViewRef = null
        }
    }
}
