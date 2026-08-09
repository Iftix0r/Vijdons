package uz.vijdon.driver.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color

val BrandYellow = Color(0xFFF5B400)
val BrandYellowDark = Color(0xFFC68F00)
val StatusOk = Color(0xFF1E8E3E)
val StatusError = Color(0xFFD93025)

private val LightColors = lightColorScheme(
    primary = BrandYellowDark,
    secondary = BrandYellow,
    error = StatusError,
)

private val DarkColors = darkColorScheme(
    primary = BrandYellow,
    secondary = BrandYellowDark,
    error = StatusError,
)

@Composable
fun VijdonDriverTheme(content: @Composable () -> Unit) {
    val colors = if (isSystemInDarkTheme()) DarkColors else LightColors
    MaterialTheme(colorScheme = colors, content = content)
}
