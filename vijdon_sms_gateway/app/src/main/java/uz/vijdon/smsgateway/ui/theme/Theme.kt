package uz.vijdon.smsgateway.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

object VijdonColors {
    val Background: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF0E1621) else Color(0xFFF2F2F7)
    val Surface: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFFFFFFF)
    val Border: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.09f) else Color(0xFF3C3C43).copy(alpha = 0.29f)

    val Green = Color(0xFF12B76A)
    val Red = Color(0xFFFF3B30)
    val Yellow = Color(0xFFFFCC00)
    val TextOnGreen = Color(0xFFFFFFFF)

    val TextPrimary: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFFFFFFFF) else Color(0xFF000000)
    val TextSecondary: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.65f) else Color(0xFF3C3C43)
    val BadgeNeutral: Color @Composable get() = if (isSystemInDarkTheme()) Color.White.copy(alpha = 0.08f) else Color(0xFF787880).copy(alpha = 0.2f)
}

val CardRadius = 18.dp

@Composable
fun VijdonSmsGatewayTheme(content: @Composable () -> Unit) {
    val dark = isSystemInDarkTheme()
    val colorScheme = if (dark) {
        darkColorScheme(
            primary = VijdonColors.Green, onPrimary = VijdonColors.TextOnGreen,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            outline = VijdonColors.Border,
        )
    } else {
        lightColorScheme(
            primary = VijdonColors.Green, onPrimary = VijdonColors.TextOnGreen,
            secondary = VijdonColors.Green, error = VijdonColors.Red,
            background = VijdonColors.Background, onBackground = VijdonColors.TextPrimary,
            surface = VijdonColors.Surface, onSurface = VijdonColors.TextPrimary,
            outline = VijdonColors.Border,
        )
    }
    MaterialTheme(colorScheme = colorScheme, content = content)
}
