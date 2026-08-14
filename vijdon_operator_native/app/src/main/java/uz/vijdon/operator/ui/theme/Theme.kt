package uz.vijdon.operator.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// Vijdon Taxi operator paneli (veb, taxi/templates/taxi/base.html) bilan
// bir xil g'oyadagi rang tokenlari — haydovchi ilovasidan (vijdon_driver_native,
// sariq aksent) farqlash uchun aksent rang KO'K (iOS tizim ko'k rangi).
object VijdonColors {
    val Background: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF0E1621) else Color(0xFFF2F2F7)
    val Surface: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFFFFFFF)
    val SurfaceRaised: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF1C2733) else Color(0xFFF2F2F7)
    val BottomBar: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFFFFFFF)
    val Border: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.09f) else Color(0xFF3C3C43).copy(alpha = 0.29f)

    val Blue = Color(0xFF0A84FF)
    val BlueDark = Color(0xFF0060C0)
    val Green = Color(0xFF34C759)
    val Red = Color(0xFFFF3B30)
    val Yellow = Color(0xFFFFCC00)
    val GreenBadge: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF34D399) else Green
    val Cyan: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF64D2FF) else Blue

    val TextPrimary: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFFFFFFFF) else Color(0xFF000000)
    val TextSecondary: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.65f) else Color(0xFF3C3C43)
    val TextOnBlue = Color(0xFFFFFFFF)

    val BadgeNeutral: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.08f) else Color(0xFF787880).copy(alpha = 0.2f)

    val Glass: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF141416).copy(alpha = 0.85f) else Color.White.copy(alpha = 0.9f)
}

val CardRadius = 18.dp
val ChipRadius = 12.dp

@Composable
fun VijdonOperatorTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = if (dark) {
        darkColorScheme(
            primary = VijdonColors.Blue, onPrimary = VijdonColors.TextOnBlue,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            surfaceVariant = VijdonColors.SurfaceRaised, onSurfaceVariant = VijdonColors.TextSecondary,
            outline = VijdonColors.Border,
        )
    } else {
        lightColorScheme(
            primary = VijdonColors.Blue, onPrimary = VijdonColors.TextOnBlue,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            surfaceVariant = VijdonColors.SurfaceRaised, onSurfaceVariant = VijdonColors.TextSecondary,
            outline = VijdonColors.Border,
        )
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
