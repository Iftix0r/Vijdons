package uz.vijdon.driver.ui.youtube

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
 * Asosiy'dan o'ngga surilganda ochiladigan "YouTube" bo'limi — haydovchi
 * navbatda kutayotganda qo'shiq/video eshitib turishi uchun, to'liq
 * YouTube mobil saytini o'z ichiga oladi (alohida native pleylist emas,
 * foydalanuvchi so'rovi bo'yicha oddiygina YouTube ochiladi).
 */
@SuppressLint("SetJavaScriptEnabled")
@Composable
fun YouTubeScreen() {
    val context = LocalContext.current
    var webViewRef by remember { mutableStateOf<WebView?>(null) }
    var progress by remember { mutableFloatStateOf(0f) }
    var loading by remember { mutableStateOf(true) }

    // Tizim "Orqaga" tugmasi — agar YouTube ichida (masalan video sahifasidan
    // qidiruvga) sahifa tarixi bo'lsa, avval o'sha ichki tarixga qaytadi,
    // aks holda odatdagidek ilova navigatsiyasiga beriladi.
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
                    webViewClient = WebViewClient()
                    webChromeClient = object : WebChromeClient() {
                        override fun onProgressChanged(view: WebView, newProgress: Int) {
                            progress = newProgress / 100f
                            loading = newProgress < 100
                        }
                    }
                    loadUrl("https://m.youtube.com")
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
