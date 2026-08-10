package uz.vijdon.driver.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// Vijdon Taxi haydovchi paneli (veb, taxi/templates/driver/base.html dagi
// --ios-* CSS o'zgaruvchilari) bilan AYNAN bir xil rang tokenlari — ilova
// qurilmaning tizim sozlamasiga (yorug'/qorong'i) qarab avtomatik moslashadi.
object VijdonColors {
    // --ios-bg / --ios-card
    val Background: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF0E1621) else Color(0xFFF2F2F7)
    val Surface: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFFFFFFF)
    // --ios-card2
    val SurfaceRaised: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF1C2733) else Color(0xFFF2F2F7)
    // Web'dagi suzuvchi panel — o'zi fondan bir bosqich ochiqroq karta rangida (.ios-glass taxminiy ekvivalenti)
    val BottomBar: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFFFFFFF)
    // --ios-sep
    val Border: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.09f) else Color(0xFF3C3C43).copy(alpha = 0.29f)

    // --ios-yellow / --ios-green / --ios-red / --ios-blue
    val Yellow = Color(0xFFFFD600)
    val YellowDark = Color(0xFFB8860B)
    val Green = Color(0xFF34C759)
    val Red = Color(0xFFFF3B30)
    val Blue = Color(0xFF007AFF)

    // --ios-label
    val TextPrimary: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFFFFFFFF) else Color(0xFF000000)
    // --ios-label2
    val TextSecondary: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.65f) else Color(0xFF3C3C43)
    // .ios-btn-primary { color:#000 }
    val TextOnYellow = Color(0xFF000000)

    // --ios-fill
    val BadgeNeutral: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.08f) else Color(0xFF787880).copy(alpha = 0.2f)

    // .ios-glass — suzuvchi shaffof "shisha" panel (tepadagi reyting/balans
    // chiplari, pastki navigatsiya paneli) uchun. Compose'da haqiqiy
    // backdrop-blur yo'q, shu sabab web'dagidan sal yuqoriroq xiralik bilan
    // taxminiy natija beriladi.
    val Glass: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF141416).copy(alpha = 0.85f) else Color.White.copy(alpha = 0.9f)
}

val CardRadius = 18.dp
val ChipRadius = 12.dp

@Composable
fun VijdonDriverTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = if (dark) {
        darkColorScheme(
            primary = VijdonColors.Yellow, onPrimary = VijdonColors.TextOnYellow,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            surfaceVariant = VijdonColors.SurfaceRaised, onSurfaceVariant = VijdonColors.TextSecondary,
            outline = VijdonColors.Border,
        )
    } else {
        lightColorScheme(
            primary = VijdonColors.Yellow, onPrimary = VijdonColors.TextOnYellow,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            surfaceVariant = VijdonColors.SurfaceRaised, onSurfaceVariant = VijdonColors.TextSecondary,
            outline = VijdonColors.Border,
        )
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
