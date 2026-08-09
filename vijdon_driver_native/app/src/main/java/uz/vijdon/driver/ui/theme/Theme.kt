package uz.vijdon.driver.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.unit.dp

// Vijdon Taxi haydovchi paneli (veb)dagi kabi — ilova qurilmaning tizim
// sozlamasiga (yorug'/qorong'i) qarab avtomatik moslashadi. Aksent ranglar
// (Yellow/Green/Red/Blue) ikkala rejimda ham bir xil qoladi — faqat fon,
// karta va matn ranglari almashadi.
object VijdonColors {
    // Qorong'i rejim — Telegram tungi mavzusidagi kabi yumshoq to'q ko'k-kulrang
    // fon (pure black emas) — ko'zga yumshoqroq va "chuqurlik" hissi beradi.
    val Background: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF17212B) else Color(0xFFF2F2F7)
    val Surface: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF1C2733) else Color(0xFFFFFFFF)
    val SurfaceRaised: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF232E3C) else Color(0xFFF7F7FA)
    val BottomBar: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF0E1621) else Color(0xFFFFFFFF)
    val Border: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF2B3946) else Color(0xFFD1D1D6)

    val Yellow = Color(0xFFF5B400)
    val YellowDark = Color(0xFFC68F00)
    val Green = Color(0xFF34D399)
    val Red = Color(0xFFEF4444)
    val Blue = Color(0xFF60A5FA)

    val TextPrimary: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFFF5F6FA) else Color(0xFF1C1C1E)
    val TextSecondary: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF8E99A3) else Color(0xFF6B7280)
    val TextOnYellow = Color(0xFF1A1300)

    val BadgeNeutral: Color @Composable get() = if (isSystemInDarkTheme()) Color(0xFF232E3C) else Color(0xFFE5E5EA)
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
