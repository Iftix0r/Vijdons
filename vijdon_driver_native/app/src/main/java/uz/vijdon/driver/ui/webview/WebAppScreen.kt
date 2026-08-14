package uz.vijdon.driver.ui.webview

import android.annotation.SuppressLint
import android.view.ViewGroup
import android.webkit.WebChromeClient
import android.webkit.WebView
import android.webkit.WebViewClient
import androidx.activity.compose.BackHandler
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.statusBarsPadding
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.rounded.ArrowBack
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableFloatStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import uz.vijdon.driver.ui.theme.VijdonColors

/**
 * Pastki pager'dagi "yon" bo'lim (YouTube) uchun umumiy WebView qobiq —
 * haydovchi navbatda kutayotganda tashqi saytdan foydalanishi uchun.
 * `url` parametri orqali boshqa saytlar uchun ham qayta ishlatilishi
 * mumkin (`ApprovedScaffold.kt`).
 *
 * `onBackToHome` berilsa (ya'ni pastki tugmalar qatori shu sahifada
 * yashirilgan bo'lsa — `ApprovedScaffold.kt`dagi YouTube holati) — suzuvchi
 * "Ortga" tugmasi chiziladi. MUHIM: teginish-ushlab-qolish tuzatishi
 * (pastga qarang, Shorts tez svaypi uchun) sabab bu sahifadan endi
 * GORIZONTAL svayp bilan chiqib bo'lmaydi — shu tugma bo'lmasa, pastki
 * panel ham yashirilgan holda haydovchi bu yerda "qamalib" qolardi.
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun WebAppScreen(url: String, onBackToHome: (() -> Unit)? = null) {
    val context = LocalContext.current
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var progress by remember { mutableFloatStateOf(0f) }
    var loading by remember { mutableStateOf(true) }

    // Tizim "Orqaga" tugmasi — agar sayt ichida (masalan video/post
    // sahifasidan ro'yxatga) sahifa tarixi bo'lsa, avval o'sha ichki
    // tarixga qaytadi. Aks holda — agar pastki panel shu sahifada
    // yashirilgan bo'lsa (`onBackToHome` berilgan) — Asosiy sahifaga
    // qaytaradi, aks holda odatdagidek ilova navigatsiyasiga beriladi.
    BackHandler(enabled = webViewRef?.canGoBack() == true) {
        webViewRef?.goBack()
    }
    if (onBackToHome != null) {
        BackHandler(enabled = webViewRef?.canGoBack() != true) {
            onBackToHome()
        }
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
                    // "yopishqoq" harakat sifatida sezilardi).
                    //
                    // Diqqat: avval BU YERDA har doim (yo'nalishidan qat'i
                    // nazar) `requestDisallowInterceptTouchEvent(true)`
                    // chaqirilardi — Shorts tezlashdi, LEKIN shu bilan birga
                    // pager UMUMAN hech qanday teginishni ololmay qoldi,
                    // gorizontal svayp bilan Asosiy sahifaga qaytish ham
                    // ishlamay qoldi. Endi harakat YO'NALISHI aniqlanadi:
                    // vertikal bo'lsa (Shorts) — pager batamom chetlatiladi
                    // (tezkorlik uchun), gorizontal bo'lsa — pager'ga
                    // ruxsat qaytariladi, u navbatdagi kadrda odatdagidek
                    // sahifani almashtira oladi.
                    val touchSlopPx = android.view.ViewConfiguration.get(context).scaledTouchSlop
                    var downX = 0f
                    var downY = 0f
                    var directionDecided = false
                    setOnTouchListener { v, event ->
                        when (event.actionMasked) {
                            android.view.MotionEvent.ACTION_DOWN -> {
                                downX = event.x
                                downY = event.y
                                directionDecided = false
                                // Boshida ehtiyot chorasi sifatida vertikal
                                // (Shorts) deb faraz qilinadi — aksariyat
                                // teginishlar aynan shu, video-ro'yxat
                                // ichida bo'ladi.
                                v.parent?.requestDisallowInterceptTouchEvent(true)
                            }
                            android.view.MotionEvent.ACTION_MOVE -> {
                                if (!directionDecided) {
                                    val dx = kotlin.math.abs(event.x - downX)
                                    val dy = kotlin.math.abs(event.y - downY)
                                    if (dx > touchSlopPx || dy > touchSlopPx) {
                                        directionDecided = true
                                        if (dx > dy) {
                                            // Gorizontal niyat — pager'ga
                                            // qaytadan ruxsat, u sahifani
                                            // almashtirishi mumkin bo'lsin.
                                            v.parent?.requestDisallowInterceptTouchEvent(false)
                                        }
                                    }
                                }
                            }
                        }
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
            // Diqqat: avval WebView pastdagi alohida `DisposableEffect`
            // ichida to'g'ridan-to'g'ri `destroy()` qilinardi — lekin bu
            // View HALI o'z ota-onasidan (Compose'ning ichki interop
            // ViewGroup'i) OLIB TASHLANMAGAN paytda chaqirilishi mumkin
            // edi (ikkalasi mustaqil, tartib kafolatlanmagan). Android'ning
            // o'zi buni tavsiya qilmaydi — biriktirilgan holda destroy()
            // chaqirish vaqti-vaqti bilan chizish/xotira xatoliklariga (va
            // shu bilan bog'liq "qotib qolish"ga) olib kelishi mumkin edi.
            // `onRelease` — Compose'ning O'ZI, View allaqachon ierarxiyadan
            // OLIB TASHLANGANDAN keyin chaqiradigan, shu ish uchun maxsus
            // mo'ljallangan joy.
            onRelease = { view ->
                view.stopLoading()
                view.destroy()
            },
        )
        if (loading) {
            LinearProgressIndicator(
                progress = { progress },
                color = VijdonColors.Yellow,
                modifier = Modifier.fillMaxWidth().align(Alignment.TopCenter),
            )
        }
        if (onBackToHome != null) {
            Box(
                modifier = Modifier
                    .align(Alignment.TopStart)
                    .statusBarsPadding()
                    .padding(12.dp)
                    .size(40.dp)
                    .background(VijdonColors.Surface.copy(alpha = 0.92f), CircleShape)
                    .clickable(onClick = onBackToHome),
                contentAlignment = Alignment.Center,
            ) {
                Icon(Icons.AutoMirrored.Rounded.ArrowBack, contentDescription = "Ortga", tint = VijdonColors.TextPrimary)
            }
        }
    }
}
